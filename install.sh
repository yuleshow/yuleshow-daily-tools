#!/usr/bin/env bash
# yuleshow-daily-tools installer
# Supports macOS (Homebrew) and Linux (apt / dnf / pacman).
#
# Usage:
#   ./install.sh              # install everything
#   ./install.sh --no-system  # skip system package installation
#   ./install.sh --no-path    # skip updating shell rc PATH
#   ./install.sh --uninstall  # remove installed wrappers and venv
#
# Environment overrides:
#   PREFIX=/custom/prefix     # default: $HOME/.local

set -euo pipefail

# ---------- Paths ----------
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$REPO_DIR/scripts"
PREFIX="${PREFIX:-$HOME/.local}"
BIN_DIR="$PREFIX/bin"
APP_DIR="$PREFIX/share/yuleshow-daily-tools"
VENV_DIR="$APP_DIR/venv"

SKIP_SYSTEM=0
UNINSTALL=0
SKIP_PATH=0

for arg in "$@"; do
    case "$arg" in
        --no-system) SKIP_SYSTEM=1 ;;
        --no-path)   SKIP_PATH=1 ;;
        --uninstall) UNINSTALL=1 ;;
        -h|--help)
            sed -n '2,13p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

# ---------- Helpers ----------
log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m  %s\n' "$*" >&2; }
die()  { printf '\033[1;31mXX\033[0m  %s\n' "$*" >&2; exit 1; }

detect_os() {
    case "$(uname -s)" in
        Darwin) OS=macos ;;
        Linux)  OS=linux ;;
        *) die "Unsupported OS: $(uname -s)" ;;
    esac
}

# ---------- Uninstall ----------
uninstall() {
    log "Removing wrappers from $BIN_DIR"
    for src in "$SCRIPTS_DIR"/*; do
        name="$(basename "$src")"
        target="$BIN_DIR/${name%.sh}"
        if [ -f "$target" ] && grep -q "yuleshow-daily-tools wrapper" "$target" 2>/dev/null; then
            rm -f "$target"
            echo "  removed $target"
        fi
    done
    if [ -d "$APP_DIR" ]; then
        log "Removing $APP_DIR"
        rm -rf "$APP_DIR"
    fi

    log "Cleaning PATH entries from shell rc files"
    for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
        [ -f "$rc" ] || continue
        if grep -Fq "# added by yuleshow-daily-tools installer" "$rc"; then
            # Remove marker line and the export PATH line that follows it.
            tmp="$(mktemp)"
            awk '
                /# added by yuleshow-daily-tools installer/ { skip=2; next }
                skip>0 { skip--; next }
                { print }
            ' "$rc" > "$tmp" && mv "$tmp" "$rc"
            echo "  cleaned $rc"
        fi
    done

    log "Uninstall complete."
}

# ---------- System deps ----------
install_system_macos() {
    if ! command -v brew >/dev/null 2>&1; then
        die "Homebrew not found. Install from https://brew.sh and re-run."
    fi
    log "Installing system packages via Homebrew"
    brew install --quiet \
        python@3.13 \
        ffmpeg \
        exiftool \
        poppler \
        exiv2 || warn "Some brew packages may already be installed."
}

install_system_linux() {
    SUDO=""
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo >/dev/null 2>&1; then
            SUDO=sudo
        else
            warn "Not root and sudo not available; skipping system package install."
            return 0
        fi
    fi

    if command -v apt-get >/dev/null 2>&1; then
        log "Installing system packages via apt-get"
        $SUDO apt-get update
        $SUDO apt-get install -y \
            python3 python3-venv python3-pip python3-dev \
            build-essential \
            ffmpeg \
            libimage-exiftool-perl \
            poppler-utils \
            libexiv2-dev libboost-python-dev \
            libheif-examples imagemagick
    elif command -v dnf >/dev/null 2>&1; then
        log "Installing system packages via dnf"
        $SUDO dnf install -y \
            python3 python3-virtualenv python3-pip python3-devel \
            gcc gcc-c++ make \
            ffmpeg \
            perl-Image-ExifTool \
            poppler-utils \
            exiv2-devel boost-python3-devel \
            libheif ImageMagick
    elif command -v pacman >/dev/null 2>&1; then
        log "Installing system packages via pacman"
        $SUDO pacman -S --needed --noconfirm \
            python python-pip \
            base-devel \
            ffmpeg \
            perl-image-exiftool \
            poppler \
            exiv2 boost \
            libheif imagemagick
    else
        warn "Unsupported Linux distro. Install manually: ffmpeg exiftool poppler exiv2 python3 libheif imagemagick"
    fi
}

# ---------- Python venv ----------
setup_venv() {
    log "Creating Python virtualenv at $VENV_DIR"
    mkdir -p "$APP_DIR"
    if [ ! -x "$VENV_DIR/bin/python3" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools >/dev/null

    log "Installing Python packages"
    "$VENV_DIR/bin/pip" install \
        Pillow \
        pillow-avif-plugin \
        pillow-heif \
        pyexiv2 \
        lunarcalendar \
        pdf2image \
        exif \
        exifread \
        opencc-python-reimplemented
}

# ---------- Wrappers ----------
install_wrappers() {
    log "Installing command wrappers into $BIN_DIR"
    mkdir -p "$BIN_DIR"

    for src in "$SCRIPTS_DIR"/*; do
        [ -f "$src" ] || continue
        name="$(basename "$src")"
        target_name="${name%.sh}"
        target="$BIN_DIR/$target_name"

        first_line="$(head -n1 "$src" || true)"
        if [[ "$first_line" == *python* ]]; then
            cat > "$target" <<EOF
#!/usr/bin/env bash
# yuleshow-daily-tools wrapper (python)
exec "$VENV_DIR/bin/python3" "$src" "\$@"
EOF
        else
            cat > "$target" <<EOF
#!/usr/bin/env bash
# yuleshow-daily-tools wrapper (shell)
exec bash "$src" "\$@"
EOF
        fi
        chmod +x "$target"
        chmod +x "$src" 2>/dev/null || true
        echo "  installed $target_name"
    done
}

# ---------- PATH setup ----------
add_path_to_rc() {
    local rc="$1"
    local marker="# added by yuleshow-daily-tools installer"
    local line="export PATH=\"$BIN_DIR:\$PATH\""

    [ -f "$rc" ] || touch "$rc"

    if grep -Fq "$marker" "$rc" 2>/dev/null; then
        echo "  $rc already configured"
        return 0
    fi
    if grep -Fq "$BIN_DIR" "$rc" 2>/dev/null; then
        echo "  $rc already references $BIN_DIR"
        return 0
    fi

    {
        printf '\n%s\n' "$marker"
        printf '%s\n' "$line"
    } >> "$rc"
    echo "  updated $rc"
}

setup_path() {
    case ":$PATH:" in
        *":$BIN_DIR:"*) return 0 ;;
    esac

    if [ "$SKIP_PATH" -eq 1 ]; then
        echo
        warn "$BIN_DIR is not in your PATH (--no-path given)."
        echo "    Add this line to ~/.zshrc or ~/.bashrc:"
        echo "        export PATH=\"$BIN_DIR:\$PATH\""
        return 0
    fi

    log "Adding $BIN_DIR to PATH in shell rc files"

    local current_shell rc_candidates=()
    current_shell="$(basename "${SHELL:-}")"
    case "$current_shell" in
        zsh)  rc_candidates+=("$HOME/.zshrc") ;;
        bash)
            if [ "$OS" = "macos" ]; then
                rc_candidates+=("$HOME/.bash_profile")
            else
                rc_candidates+=("$HOME/.bashrc")
            fi
            ;;
        *)
            [ -f "$HOME/.zshrc" ]        && rc_candidates+=("$HOME/.zshrc")
            [ -f "$HOME/.bashrc" ]       && rc_candidates+=("$HOME/.bashrc")
            [ -f "$HOME/.bash_profile" ] && rc_candidates+=("$HOME/.bash_profile")
            [ ${#rc_candidates[@]} -eq 0 ] && rc_candidates+=("$HOME/.profile")
            ;;
    esac

    for rc in "${rc_candidates[@]}"; do
        add_path_to_rc "$rc"
    done

    echo
    warn "Restart your shell or run: source ${rc_candidates[0]}"
}

# ---------- Post-install hints ----------
post_install_notes() {
    echo
    log "Installation complete."
    echo "    Wrappers : $BIN_DIR"
    echo "    venv     : $VENV_DIR"
    echo "    sources  : $SCRIPTS_DIR"

    setup_path

    if [ "$OS" = "linux" ]; then
        echo
        warn "macOS-only commands will no-op on Linux:"
        echo "    - yuleshow-clean  (uses macOS 'dot_clean', 'defaults', 'purge')"
    fi
}

# ---------- Main ----------
main() {
    detect_os
    log "Detected OS: $OS"
    log "Install prefix: $PREFIX"

    if [ "$UNINSTALL" -eq 1 ]; then
        uninstall
        exit 0
    fi

    [ -d "$SCRIPTS_DIR" ] || die "Scripts dir not found: $SCRIPTS_DIR"

    if [ "$SKIP_SYSTEM" -eq 0 ]; then
        if [ "$OS" = "macos" ]; then
            install_system_macos
        else
            install_system_linux
        fi
    else
        log "Skipping system package installation (--no-system)"
    fi

    setup_venv
    install_wrappers
    post_install_notes
}

main
