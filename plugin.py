#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     22 Aug 2021, (9:55 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import hashlib
import json
import logging
import os
import time
from configparser import NoSectionError, NoOptionError

from unmanic.libs.directoryinfo import UnmanicDirectoryInfo
from unmanic.libs.unplugins.settings import PluginSettings

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.mover2_cleanup")


class Settings(PluginSettings):
    settings = {
        "force_processing_all_files":   False,
        "destination_directory":        "/library",
        "recreate_directory_structure": True,
        "include_library_structure":    True,
        "remove_source_file":           False,
        "remove_empty_source_directory": True,
        "source_directory_junk_extensions": "nfo,sfv,md5,txt,diz,url,jpg,jpeg,png,gif",
        "prune_empty_destination_directories": True,
        "prune_destination_min_age_minutes":   10,
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "force_processing_all_files":   {
                "label": "Force processing of all files",
            },
            "destination_directory":        {
                "label":      "Destination directory",
                "input_type": "browse_directory",
            },
            "recreate_directory_structure": {
                "label": "Recreate directory structure",
            },
            "include_library_structure":    self.__set_include_library_structure(),
            "remove_source_file":           {
                "label": "Remove source files",
            },
            "remove_empty_source_directory": {
                "label":       "Remove the source directory if it is left empty",
                "description": "Once the source file has been removed, also delete the directory it sat in when nothing else is left in it. Directories still holding other files (subtitles, nfo, sidecar art, or a seeding torrent's payload) are left alone.",
                "input_type":  "checkbox",
            },
            "source_directory_junk_extensions": {
                "label":       "File extensions that do not count as content",
                "description": "Comma separated. When the source directory holds nothing but these files, it is removed along with them - so a release that keeps an .nfo or .sfv beside the video still gets tidied away. Anything else in the directory (other episodes of a season pack, subtitles) leaves it in place.",
                "input_type":  "text",
            },
            "prune_empty_destination_directories": {
                "label":       "Prune empty directories left in the destination",
                "description": "An *arr import MOVES the file out of the destination directory, leaving the release folder behind empty. Enable this and each run will clear away empty directories under the destination directory.",
                "input_type":  "checkbox",
            },
            "prune_destination_min_age_minutes": {
                "label":       "Only prune destination directories empty for at least (minutes)",
                "description": "Keeps a directory that is momentarily empty from being yanked mid-use by a copy or a move in progress.",
                "input_type":  "text",
            },
        }

    def __set_include_library_structure(self):
        values = {
            "label":      "Also include library path when re-creating the directory structure",
            "input_type": "checkbox",
        }
        if not self.get_setting('recreate_directory_structure'):
            values["display"] = 'hidden'
        return values


def all_parent_directories(head):
    dirs = []
    while True:
        head, tail = os.path.split(head)
        if tail != "":
            dirs[0:0] = [tail]
        else:
            # Dont bother appending the root to this path...
            break
    return dirs


def get_file_out(settings, original_source_path, file_out, library_id=None):
    # Get the destination directory
    destination_directory = settings.get_setting('destination_directory')

    # Is the plugin configured to recreate the directory structure?
    if settings.get_setting('recreate_directory_structure'):
        # Recreate the FULL directory path
        # Get the parent directory of the original file
        # Eg. /library/path/to/my/file.ext    =   /library/path/to/my
        original_source_dirname = os.path.dirname(original_source_path)

        if not settings.get_setting('include_library_structure'):
            # Remove the library path from the original_source_dirname
            if library_id:
                from unmanic.libs.library import Library
                library = Library(library_id)
                library_path = library.get_path()
            else:
                from unmanic import config
                unmanic_settings = config.Config()
                library_path = unmanic_settings.get_library_path()
            original_source_dirname = os.path.relpath(original_source_dirname, library_path)

        # Fetch a list of all directories in the original directory path
        # Eg. directories = ['library', 'path', 'to', 'my']
        directories = all_parent_directories(original_source_dirname)

        # Append the directory structure to the destination directory
        destination_directory = os.path.join(destination_directory, *directories)

        # Ensure the destination directory structure exists. Create it if it does not
        if not os.path.exists(destination_directory):
            os.makedirs(destination_directory)

    # Get just the file name from of the output file
    file_out_basename = os.path.basename(file_out)

    # Return the output file
    return os.path.join(destination_directory, file_out_basename)


def file_marked_as_moved(path, file_metadata=None):
    if file_metadata:
        try:
            metadata = file_metadata.get()
            if metadata.get('status') == 'Ignoring' or metadata.get('ignore') is True:
                return True
        except Exception as e:
            logger.debug("Unable to read UnmanicFileMetadata for '{}': {}".format(path, e))

    directory_info = UnmanicDirectoryInfo(os.path.dirname(path))
    try:
        has_been_moved = directory_info.get('mover2', os.path.basename(path))
    except NoSectionError as e:
        has_been_moved = ''
    except NoOptionError as e:
        has_been_moved = ''
    except Exception as e:
        logger.debug("Unknown exception {}.".format(e))
        has_been_moved = ''

    if has_been_moved == 'Ignoring':
        # This file movement already has been attempted and failed
        return True

    # Default to...
    return False


def on_library_management_file_test(data, task_data_store=None, file_metadata=None):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Get the path to the file
    abspath = data.get('path')
    basename = os.path.basename(abspath)

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    if file_marked_as_moved(abspath, file_metadata=file_metadata):
        # Ensure this file is not added to the pending tasks
        data['add_file_to_pending_tasks'] = False
        logger.debug("File '{}' has been previously marked as moved.".format(abspath))
    elif settings.get_setting('force_processing_all_files') and basename != '.unmanic':
        # (Never move the .unmanic file)
        # Ensure this file is added to the pending tasks regardless of status of any subsequent tests
        data['add_file_to_pending_tasks'] = True
        logger.debug("Forcing file '{}' to be added to task list.".format(abspath))

    return data


def on_postprocessor_file_movement(data, task_data_store=None, file_metadata=None):
    """
    Runner function - configures additional postprocessor file movements during the postprocessor stage of a task.

    The 'data' object argument includes:
        library_id              - Integer, the library that the current task is associated with.
        source_data             - Dictionary, data pertaining to the original source file.
        remove_source_file      - Boolean, should Unmanic remove the original source file after all copy operations
                                  are complete. (default: 'True' if file name has changed)
        copy_file               - Boolean, should Unmanic run a copy operation with the returned data variables.
                                  (default: 'False')
        file_in                 - String, the converted cache file to be copied by the postprocessor.
        file_out                - String, the destination file that the file will be copied to.
        run_default_file_copy   - Boolean, should Unmanic run the default post-process file movement. (default: 'True')

    :param data:
    :return:

    """
    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get the original file's absolute path
    original_source_path = data.get('source_data', {}).get('abspath')
    if not original_source_path:
        logger.error("Provided 'source_data' is missing the source file abspath data.")
        return data

    unmanic_destination_file = data.get('file_out')

    # Should the plugin remove the source file?
    # If remove source file is not selected, then prevent the removal of the source file
    data['remove_source_file'] = settings.get_setting('remove_source_file')
    # Always prevent Unmanic from running the default file movement (requires Unmanic v0.2.0)
    data['run_default_file_copy'] = False

    # Set the output file
    file_out = get_file_out(settings, original_source_path, os.path.abspath(data.get('file_out')),
                            library_id=data.get('library_id'))
    data['file_out'] = file_out

    # Set plugin to copy file
    data['copy_file'] = True

    # Store some required data in a JSON file for the on_postprocessor_task_results runner.
    # If the source needs to be removed, then we will handle that with the other plugin runner. Notes below...
    # For now, save the current file_out (which is Unmanic's destination file once all plugins are run) to a file.
    # We also want to store a checksum of the cache file to ensure that the file movement was completed correctly.
    profile_directory = settings.get_profile_directory()
    # Use the basename of the source path to create a unique file for storing the file_out data.
    # This can then be read and used by the on_postprocessor_task_results function below.
    src_file_hash = hashlib.md5(original_source_path.encode('utf8')).hexdigest()
    plugin_data_file = os.path.join(profile_directory, '{}.json'.format(src_file_hash))
    with open(plugin_data_file, 'w') as f:
        required_data = {
            'file_out':                 file_out,
            'unmanic_destination_file': unmanic_destination_file,
        }
        json.dump(required_data, f, indent=4)

    if not settings.get_setting('remove_source_file'):
        # Get the original file's absolute path
        original_source_path = data.get('source_data', {}).get('abspath')
        if not original_source_path:
            logger.error("Provided 'source_data' is missing the source file abspath data.")
            return data
        if not os.path.exists(original_source_path):
            logger.error("Original source path could not be found.")
            return data

        # Mark the source file to be ignored on future scans. Write the plugin's own directory
        #   marker AND the core .unmanicignore lockfile every time, instead of relying on the
        #   file-metadata store alone: that store is keyed to the file's fingerprint, so anything
        #   that touches the file - a torrent client rechecking it, for instance - loses the marker
        #   and the preserved source gets queued again on the next scan.
        if file_metadata:
            file_metadata.set({'status': 'Ignoring'}, use_source_scope=True)
        source_directory = os.path.dirname(original_source_path)
        source_basename = os.path.basename(original_source_path)
        try:
            directory_info = UnmanicDirectoryInfo(source_directory)
            directory_info.set('mover2', source_basename, 'Ignoring')
            directory_info.save()
            ignore_file = os.path.join(source_directory, '.unmanicignore')
            existing_ignores = ''
            if os.path.exists(ignore_file):
                with open(ignore_file) as f:
                    existing_ignores = f.read()
            if source_basename not in existing_ignores:
                with open(ignore_file, 'a') as f:
                    if existing_ignores and not existing_ignores.endswith('
'):
                        f.write('
')
                    f.write(source_basename + '
')
            logger.info("Marked '{}' to be ignored on future scans.".format(original_source_path))
        except OSError as e:
            logger.debug("Could not write ignore marker for '{}': {}".format(original_source_path, e))


def on_postprocessor_task_results(data):
    """
    Runner function - provides a means for additional postprocessor functions based on the task success.

    The 'data' object argument includes:
        task_processing_success         - Boolean, did all task processes complete successfully.
        file_move_processes_success     - Boolean, did all postprocessor movement tasks complete successfully.
        destination_files               - List containing all file paths created by postprocessor file movements.
        source_data                     - Dictionary containing data pertaining to the original source file.

    :param data:
    :return:

    """
    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get the original file's absolute path
    original_source_path = data.get('source_data', {}).get('abspath')
    if not original_source_path:
        logger.error("Provided 'source_data' is missing the source file abspath data.")
        return data

    # Read the data from the on_postprocessor_file_movement runner
    profile_directory = settings.get_profile_directory()
    # Get the file out and store
    src_file_hash = hashlib.md5(original_source_path.encode('utf8')).hexdigest()
    plugin_data_file = os.path.join(profile_directory, '{}.json'.format(src_file_hash))
    if not os.path.exists(plugin_data_file):
        logger.error("Plugin data file is missing (This may be because the file movement post-processor was skipped)")
        raise Exception("Plugin data file is missing.")
    with open(plugin_data_file) as infile:
        file_movement_data = json.load(infile)

    # Ensure the file was correctly moved as required
    if not data.get('file_move_processes_success'):
        # A plugin failed in its file movements. It may not have been this one... Check file
        if not file_movement_data.get('file_out') in data.get('destination_files'):
            # The file that this plugin requested that Unmanic move to does not exist in the 'destination_files' list
            # This means that the file did not successfully copy
            logger.error(
                "Detected that the file movement did not complete correctly. Dont do anything with the source file.")
            return data
    # If the above check was fine, then the file movement that this plugin requested was successful

    # If the source file and destination file are named the exact same thing (including extension), then the file
    #   may already be removed by setting 'remove_source_file' in the on_postprocessor_file_movement function.
    # However, if the file's name had changed at all, then the "source" file will have been replaced by the
    #   newly named file. Unmanic's default process is to replace the file with the processed one. This section
    #   ensures that these replaced files are cleaned up if the plugin is configured to remove the source files.
    if settings.get_setting('remove_source_file'):
        # Plugin configured to remove the source file.
        unmanic_destination_file = os.path.abspath(file_movement_data.get('unmanic_destination_file'))
        if os.path.exists(unmanic_destination_file):
            logger.debug("Plugin is configured to ensure the original file is removed. Removing file '{}'".format(
                unmanic_destination_file))
            os.remove(unmanic_destination_file)
        else:
            logger.debug("Plugin is configured to ensure the original file is removed. File has already been removed.")

        if settings.get_setting('remove_empty_source_directory'):
            # Unmanic deletes the source file but leaves its directory behind, along with whatever
            #   sidecar files the release shipped with. Clear the directory up once nothing but those
            #   throwaway files remain. Anything else - another episode of a season pack, subtitles, a
            #   seeding torrent's payload - means it is still in use and gets left alone.
            junk_extensions = [e.strip().lower().lstrip('.')
                               for e in settings.get_setting('source_directory_junk_extensions').split(',')
                               if e.strip()]
            source_directory = os.path.dirname(unmanic_destination_file)
            try:
                if os.path.isdir(source_directory):
                    remaining = os.listdir(source_directory)
                    keep = [f for f in remaining
                            if os.path.isdir(os.path.join(source_directory, f)) or
                            os.path.splitext(f)[1].lower().lstrip('.') not in junk_extensions]
                    if not keep:
                        for f in remaining:
                            os.remove(os.path.join(source_directory, f))
                        logger.info("Removed source directory '{}' (it held only sidecar files)".format(source_directory))
                        os.rmdir(source_directory)
            except OSError as e:
                logger.debug("Could not remove source directory '{}': {}".format(source_directory, e))

    if settings.get_setting('prune_empty_destination_directories'):
        # The *arr apps move the file OUT of the destination when they import it, leaving the
        #   release directory behind empty. Clear those away, but only ones that have stayed
        #   empty long enough that nothing can be mid-move inside them.
        destination_directory = settings.get_setting('destination_directory')
        try:
            min_age_seconds = int(settings.get_setting('prune_destination_min_age_minutes')) * 60
        except (TypeError, ValueError):
            min_age_seconds = 600
        try:
            if os.path.isdir(destination_directory):
                now = time.time()
                for root, dirs, files in os.walk(destination_directory, topdown=False):
                    rel = os.path.relpath(root, destination_directory)
                    # Never remove the destination root itself, or the category directories directly under it
                    if rel == '.' or os.sep not in rel:
                        continue
                    if not dirs and not files and (now - os.path.getmtime(root)) >= min_age_seconds:
                        os.rmdir(root)
                        logger.info("Removed empty destination directory '{}'".format(root))
        except OSError as e:
            logger.debug("Could not prune destination '{}': {}".format(destination_directory, e))

    # Clean up plugin's data file
    os.remove(plugin_data_file)
