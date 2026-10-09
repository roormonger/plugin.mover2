**<span style="color:#56adda">0.1.2</span>**
- Fork: add "Prune empty directories left in the destination". A *arr import moves the file out of the Mover's destination and leaves the release directory behind empty, so those now get cleared on the next run once they have stood empty for the configured number of minutes. Runs independently of the source-file settings, and never touches the destination root or the category directories beneath it.

**<span style="color:#56adda">0.1.1</span>**
- Fork: treat common release sidecar files (.nfo, .sfv, .md5, .txt, .diz, .url and images) as non-content, so a source directory holding only those is still removed. Anything else in the directory still blocks removal, so season packs and seeding payloads stay safe. Configurable via the "File extensions that do not count as content" setting.

**<span style="color:#56adda">0.1.0</span>**
- Fork: add the "Remove the source directory if it is left empty" option - clear away the source directory after the source file is removed, when it is genuinely empty
- Fork: rename the plugin id to `mover2_cleanup` so it installs alongside the official mover2
- Fork: remove the workflow job that opened a PR against the official Unmanic plugin repo

**<span style="color:#56adda">0.0.9</span>**
- Add support for using the File Metadata helper for storing details on moved files (Requires Unmanic v0.3.0)

**<span style="color:#56adda">0.0.8</span>**
- Always prevent Unmanic's default move process (Requires Unmanic v0.2.0)

**<span style="color:#56adda">0.0.7</span>**
- Fixed bug where library path was not being correctly fetched on newer versions of Unmanic

**<span style="color:#56adda">0.0.6</span>**
- Always exclude the '.unmanic' file from file movements
- Disable the default file copy of Unmnaic's post-processor when Remove source files is unselected (Requires Unmanic v0.2.0)

**<span style="color:#56adda">0.0.5</span>**
- Ignore files on all future scans if "Remove source files" is not selected
- Add ability to force tasks to be created for all files tested regardless of other plugin processing requirements

**<span style="color:#56adda">0.0.4</span>**
- Enabled support for v2 plugin executor

**<span style="color:#56adda">0.0.3</span>**
- Ensure the file copy flag is set for the file moments. Even tho the current default is to do so it may change in the future.

**<span style="color:#56adda">0.0.2</span>**
- Update available options with the ability to recreate directory structure relative to the library path

**<span style="color:#56adda">0.0.1</span>**
- initial version based on the original mover plugin by R3dC4p and 
  updated for compatibility with latest Unmanic release
