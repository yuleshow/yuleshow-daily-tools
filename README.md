# yuleshow-daily-tools

A collection of small command-line tools used daily by 梅璽閣主 for photo/video
management, file renaming, and system maintenance. Works on **macOS** and
**Linux**.

## Install

```bash
git clone <this-repo>
cd yuleshow-daily-tools
./install.sh
```

The installer will:

1. Install system dependencies (Homebrew on macOS; `apt` / `dnf` / `pacman` on Linux).
2. Create a Python virtualenv at `~/.local/share/yuleshow-daily-tools/venv`.
3. Install Python libraries (Pillow, pillow-heif, pillow-avif-plugin, pyexiv2, lunarcalendar, pdf2image, exif, opencc-python-reimplemented).
4. Drop thin wrapper scripts into `~/.local/bin/` for every tool in `scripts/`.

### Options

```bash
./install.sh --no-system   # skip system package install (venv + wrappers only)
./install.sh --uninstall   # remove wrappers and the venv
PREFIX=/opt/yuleshow ./install.sh
```

### PATH

Ensure `~/.local/bin` is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

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
| `yuleshow-heif2jpg [dir]` | Convert HEIC/HEIF in a dir to JPG (cross-platform). |
| `yuleshow-pdf2jpg <file.pdf>` | Render PDF pages to 300 DPI JPGs. |
| `yuleshow-mahjong` | Crop 2560×1080 screenshots to center 1440×1080 (for mahjong). |

### Audio / video

| Command | Description |
| --- | --- |
| `yuleshow-stereo2mono` | Convert stereo `*.mp3` in CWD to mono (ffmpeg). |
| `yuleshow-batch-convert <old> <new>` | Batch-convert by extension via ffmpeg, e.g. `wav mp3`. |

### Tags / metadata

| Command | Description |
| --- | --- |
| `yuleshow-readtags [dir]` | Print IPTC Keywords and XMP Subject for images. |
| `yuleshow-get-tags` | Collect unique IPTC keywords under CWD -> `unique_iptc_keywords_output.txt`. |
| `yuleshow-tags-c2t` | Convert IPTC keywords Simplified -> Traditional Chinese (in-place). |

### CSV / GPX

| Command | Description |
| --- | --- |
| `yuleshow-csv2gpx <file.csv>` | Convert GPS CSV (Unix time,lat,lon,alt) to GPX 1.1 (America/Los_Angeles). |

### System / backup

| Command | Description |
| --- | --- |
| `yuleshow-clean` | **macOS-only.** System maintenance: caches, Adobe, `.DS_Store`, AppleDouble. |
| `yuleshow-digikam-backup` | Dump digiKam MySQL DB, keep `KEEP_DAYS` history. See config below. |

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

All scripts share:

- Shebangs: `#!/usr/bin/env bash` or `#!/usr/bin/env python3`.
- Bash: `set -euo pipefail`, unified `log / ok / warn / err` helpers.
- Python: module docstring + usage, `main()` returning exit code, `sys.exit(main())`.
- Output emojis: 🚀 start · ✅ success · ⚠️ warn · ❌ error · 🔍 scan · 📷 photo.

## Platform notes

- `yuleshow-clean` is macOS-only (uses `defaults`, `dot_clean`, `purge`). On Linux it exits with a notice.
- `yuleshow-digikam-backup` needs the `mysqldump` client installed.
- `yuleshow-csv2gpx` hardcodes `America/Los_Angeles` timezone.

## Uninstall

```bash
./install.sh --uninstall
```

This removes the wrappers from `~/.local/bin` and the venv at
`~/.local/share/yuleshow-daily-tools`. Your original scripts in the repo remain
untouched.
