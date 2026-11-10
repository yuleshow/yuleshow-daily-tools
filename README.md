# yuleshow-daily-tools

A collection of small command-line tools used daily by 梅璽閣主 for photo/video
management, file renaming, and system maintenance. The command-line tools
support **macOS**, **Linux**, and **Windows**.

## Install

```bash
git clone <this-repo>
cd yuleshow-daily-tools
./install.sh
```

On Windows, run PowerShell from the repository directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The installer will:

1. Install system dependencies (Homebrew on macOS; `apt` / `dnf` / `pacman` on Linux; `winget` on Windows when available).
2. Create a Python virtualenv at `~/.local/share/yuleshow-daily-tools/venv` (Windows: `%USERPROFILE%\.local\share\yuleshow-daily-tools\venv`).
3. Install Python libraries from `requirements.txt` (including Pillow, pyexiv2, lunarcalendar, pdf2image, exifread, and timezone data).
4. Install command wrappers for every tool in `scripts/` (`~/.local/bin/` on macOS/Linux; `%USERPROFILE%\.local\bin\` on Windows).

All commands use Python entry points, so Windows runs them natively without
Bash, WSL, or Git Bash. Windows system packages are installed with `winget`
when possible; install ffmpeg, GPSBabel, ExifTool, Poppler, and ImageMagick
manually if `winget` is unavailable or a package installation fails. The
digiKam backup tool also requires a MySQL/MariaDB client providing `mysqldump`.

### Options

```bash
./install.sh --no-system   # skip system package install (venv + wrappers only)
./install.sh --uninstall   # remove wrappers and the venv
PREFIX=/opt/yuleshow ./install.sh
```

PowerShell equivalents:

```powershell
.\install.ps1 -NoSystem
.\install.ps1 -NoPath
.\install.ps1 -Uninstall
.\install.ps1 -Prefix C:\Tools\yuleshow
```

### PATH

On macOS/Linux, ensure `~/.local/bin` is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

The Windows installer adds `%USERPROFILE%\.local\bin` to the user PATH.
Open a new terminal after installation.

## Tools

### File / folder rename

| Command | Description |
| --- | --- |
| `yuleshow-rename` | Rename JPGs in CWD by EXIF date+camera (Pillow). |
| `yuleshow-rename-folder` | Same as above, but also move into `YYYYMMDD/` folders. |
| `yuleshow-rename-original` | Flatten subdirs, rename JPGs, remove `.AAE`, tidy CWD. |
| `yuleshow-rename-lunar-folder` | Append lunar/festival/solar-term/US-holiday info to `YYYYMMDD*` folders. |
| `yuleshow-hyphen2underscore` | Rename files in CWD: `-` -> `_`. |
| `yuleshow-space2underscore` | Rename files in CWD: space -> `_`. |

### Image / PDF conversion

| Command | Description |
| --- | --- |
| `yuleshow-avif2jpg <file.avif>` | Convert a single AVIF to JPG. |
| `yuleshow-avif2png [options] <file-or-dir...>` | Convert AVIF files to PNG; supports recursive and output-directory options. |
| `yuleshow-jpeg2png [-d] <file-or-dir>` | Convert JPEG files to PNG, optionally deleting originals after success. |
| `yuleshow-heif2jpg [dir]` | Convert HEIC/HEIF in a dir to JPG (cross-platform). |
| `yuleshow-pdf2jpg <file.pdf>` | Render PDF pages to 300 DPI JPGs. |
| `yuleshow-mahjong` | Crop 2560×1080 screenshots to center 1440×1080 (for mahjong). |

### Audio / video

| Command | Description |
| --- | --- |
| `yuleshow-2echoshow` | Recursively create smaller H.265 MP4 copies for compatible devices (ffmpeg). |
| `yuleshow-stereo2mono` | Convert stereo `*.mp3` in CWD to mono (ffmpeg). |
| `yuleshow-batch-convert <old> <new>` | Batch-convert by extension via ffmpeg, e.g. `wav mp3`. |

### Tags / metadata

| Command | Description |
| --- | --- |
| `yuleshow-readtags [dir]` | Print IPTC Keywords and XMP Subject for images. |
| `yuleshow-get-tags` | Collect unique IPTC keywords under CWD -> `unique_iptc_keywords_output.txt`. |
| `yuleshow-tags-c2t` | Convert IPTC keywords Simplified -> Traditional Chinese (in-place). |

### GPS conversion

| Command | Description |
| --- | --- |
| `yuleshow-csv2gpx <file.csv>` | Convert GPS CSV (Unix time,lat,lon,alt) to GPX 1.1 (America/Los_Angeles). |
| `yuleshow-igc2gpx` | Convert all IGC files in CWD to same-name GPX files via GPSBabel, skipping existing GPX files. |
| `yuleshow-fixgpx [--dry-run]` | Recursively repair GPX files, back up home-only or empty logs to `.bak`, and rename trips by Los Angeles time. |

Run `yuleshow-igc2gpx` from the folder containing your flight logs. It scans only
that folder (including hidden files), accepts extensions case-insensitively,
and keeps the original IGC files. For example, `flight.IGC` becomes `flight.gpx`,
unless `flight.gpx` (or `flight.GPX`, etc.) already exists. Failed conversions
are reported, do not leave partial GPX files, and cause a nonzero exit status;
the remaining files are still processed.
Completed output is moved into place without overwriting existing files; no
hard-link support is required, so FAT/exFAT flight-recorder volumes are supported.

GPSBabel is installed by the installers when possible; for manual installation,
use `brew install gpsbabel` on macOS, your Linux package manager's `gpsbabel`
package, or `winget install GPSBabel.GPSBabel` on Windows. GPSBabel preserves flight timestamps in UTC and may produce separate
tracks for pressure and GNSS altitudes when both are recorded.

#### `yuleshow-fixgpx`

Run from the folder containing your recordings:

```bash
yuleshow-fixgpx --dry-run   # preview repairs and renames
yuleshow-fixgpx             # apply them in this folder and all subfolders
```

Requires Python 3.9+ and timezone data (included in the virtual environment).
On macOS/Linux, it also uses the system `mv` command to avoid overwriting a
destination during a concurrent rename. On Windows, it uses the native
no-overwrite rename operation. The installer automatically includes this
script; before installation, run `python3 /path/to/scripts/yuleshow-fixgpx`
or `python C:\path\to\scripts\yuleshow-fixgpx`.
GPX extensions are matched case-insensitively, hidden files are included, and
symbolic links to files or directories are not followed.

Missing final `</trkseg>`, `</trk>`, `</rte>`, and `</gpx>` tags are appended only
when they close otherwise intact XML. Premature `</trkseg></trk></gpx>` sequences
followed by more track points or duplicate closing sequences are removed, then
the entire document is parsed again before checking whether it is empty or
home-only. All points are preserved, and valid complete files are not rewritten.
Other broken XML, incomplete points, and unsupported encodings are reported and left alone;
processing continues, with a nonzero exit status if any file fails.

Empty GPX recordings with no track points, route points, or waypoints are also
renamed to `.bak`, after repairing missing closing tags if needed. A zero-byte
file is not valid GPX and is reported rather than renamed. Points with missing
or invalid coordinates do not count as an empty recording.

The home reference is **34.1539223, -118.1082890**, based on the confirmed stationary
window recording. A nonempty recording is considered home-only when every track,
route, and waypoint coordinate is within **75 metres** of this reference. This
tolerance covers the supplied home-drift samples, which reach about 70 metres
from the reference even after startup.
For track-only recordings, initial fixes may be up to **100 metres** away during
the first **60 seconds**, provided all later fixes are within 75 metres and those
later fixes span at least another 60 seconds. This exception requires valid,
strictly increasing, timezone-aware timestamps. Missing or invalid coordinates
prevent home-only classification. Elevation is ignored because of GPS noise.

These are distance heuristics, not proof of being stationary: a short walk near
home can also qualify. Preview first; adjust the constants at the top of the
script if needed. `recording.gpx` becomes `recording.bak` (not `.gpx.bak`), keeping
all recorded points and any repaired ending. Existing backups, including dangling
symlinks, are never overwritten. Other recordings retain their `.gpx` extension.

Retained recordings are renamed to `YYYYMMDD_HHMM-LA.gpx`, using
`America/Los_Angeles` time with daylight saving handled automatically. For example,
`2026-10-22T01:20:45Z` becomes `20261021_1820-LA.gpx`. The first usable
timezone-aware timestamp is selected from track points, then route points, then
waypoints, with GPX metadata time (or GPX 1.0 root time) as a fallback. Timestamps
inside the GPX are unchanged. Files without a usable timestamp keep their names.
Existing destinations, including dangling symlinks, are never overwritten;
recordings that map to an occupied name are reported and keep their original names.
Already correctly named files are left in place. Home-only and empty recordings
keep the original filename stem when renamed to `.bak`.

Tests: `python3 tests/test-fixgpx.py -v` and
`python3 tests/test_portability.py -v`.

### System / backup

| Command | Description |
| --- | --- |
| `yuleshow-clean` | User-cache maintenance plus optional mounted-volume cleanup for OS metadata. |
| `yuleshow-digikam-backup` | Dump digiKam MySQL DB, keep `KEEP_DAYS` history. See config below. |

#### `yuleshow-clean` examples

```bash
yuleshow-clean                            # normal user-cache maintenance
yuleshow-clean /Volumes/SD4T              # clean an external macOS volume
yuleshow-clean --dry-run /media/user/SD4T # preview a mounted Linux volume
```

On Windows, pass a drive root from PowerShell, for example
`yuleshow-clean --system E:\`.

The volume-clean command accepts mounted volume roots only. It removes macOS
metadata (and macOS service folders on macOS), plus `Thumbs.db` on Windows.
System maintenance clears user caches: macOS caches while protecting Homebrew,
Linux `~/.cache`, and Windows `%LOCALAPPDATA%\Temp`; macOS also retains its
existing Homebrew cleanup and system maintenance actions. Use `--dry-run` to
preview file removals.

#### `yuleshow-digikam-backup` config

Create `~/.yuleshow/digikam.conf`:

```sh
MYSQL_USER=digikamuser
MYSQL_PASS=your_password
DB_NAME=digikam
BACKUP_DIR=$HOME/Backups/digikam
KEEP_DAYS=14
```

Or use `~/.my.cnf` for credentials.

## Style conventions

All command scripts share:

- Python shebangs: `#!/usr/bin/env python3`.
- `main()` returns an exit code, invoked through `sys.exit(main())`.
- Output emojis: 🚀 start · ✅ success · ⚠️ warn · ❌ error · 🔍 scan · 📷 photo.

## Platform notes

- All scripts are Python-based and launch natively on macOS, Linux, and Windows.
- Some system integrations are OS-specific; `yuleshow-clean` uses macOS maintenance commands only on macOS.
- `yuleshow-rename-lunar-folder` uses ` - ` as its Windows folder-name separator because `|` is not valid in Windows names.
- `yuleshow-digikam-backup` needs the `mysqldump` client installed.
- `yuleshow-csv2gpx` and `yuleshow-fixgpx` use the `America/Los_Angeles` timezone.

## Uninstall

```bash
./install.sh --uninstall
# Windows:
.\install.ps1 -Uninstall
```

This removes wrappers and the virtual environment from their platform-specific
install locations. Your original scripts in the repo remain untouched.
