# Mover v2 + Directory Cleanup

Plugin for [Unmanic](https://github.com/Unmanic) - a fork of
[Unmanic/plugin.mover2](https://github.com/Unmanic/plugin.mover2).

---

### What this fork adds

Upstream `mover2` moves the completed encode to the destination directory and, when
*Remove source files* is enabled, deletes the original source file - but it leaves the
**directory that file sat in** behind. In a download-client staging layout
(`.../complete/sonarr/<release>/...`) that leaves one empty directory per release, forever.

This fork adds one option, **Remove the source directory if it is left empty** (enabled by
default): after the source file is removed, its parent directory is deleted **only if
nothing else remains in it**. A directory still holding subtitles, nfo files, sidecar art,
or a seeding torrent's payload is left alone - so it is safe to enable on torrent libraries
too.

Everything else is upstream behaviour, unchanged.

---

### Information:

- [Description](description.md)
- [Changelog](changelog.md)

---

### Installing

Unmanic -> **Settings -> Plugins -> Install plugin -> from a GitHub repository**, using this
repo's URL.

The plugin installs under the id `mover2_cleanup`, so it sits alongside the official
`mover2` instead of replacing it - updates to the official plugin cannot clobber it.

Per-library settings do **not** carry across from `mover2`: configure `mover2_cleanup` on
each library and swap it into the plugin flow where `mover2` used to be, then disable the
official `mover2`.

---

### Licence

GPL-3.0, inherited from the upstream project. Original plugin by Josh.5 and
[R3dC4p](https://github.com/R3dC4p).
