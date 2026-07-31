#!/bin/sh
# ---------------------------------------------------------------------------
# pyTECTOR one-click setup for macOS and Linux, the counterpart of install.bat.
#
# On macOS a .command file is double-clickable from Finder. If it is not, it has
# lost its execute bit; restore it with
#
#     chmod +x install.command
#
# What it does:
#
#   1. finds a Python 3.8 or newer, conda installations first
#   2. if there is none, offers to download Miniconda from repo.anaconda.com
#      and install it into ~/miniconda3, for this user only
#   3. installs numpy, scipy, matplotlib and PyQt5, falling back to conda-forge
#      for anything pip cannot supply
#   4. checks that all four actually import
#   5. records the interpreter in python-path.txt so pyTECTOR.command starts
#      that same one
#   6. compile-checks the program and makes the launcher executable
#
# Safe to run twice. Needs no root.
# ---------------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1

PYEXE=""
CONDA=""
MISSING=""

echo
echo "  pyTECTOR setup"
echo "  =============="
echo

# --- 1. find an interpreter -------------------------------------------------
try_python() {
    [ -z "$PYEXE" ] || return 0
    [ -n "$1" ] || return 0
    command -v "$1" >/dev/null 2>&1 || return 0
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1 || return 0
    PYEXE=$("$1" -c 'import sys; print(sys.executable)' 2>/dev/null) || PYEXE="$1"
    return 0
}

echo "[1/5] Looking for a Python interpreter ..."

try_python "$PYTECTOR_PYTHON"
[ -f python-path.txt ] && try_python "$(cat python-path.txt)"

# conda first, for the same reason as on Windows: it ships scipy and Qt as
# binaries, so nothing has to be compiled.
for d in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" \
         /opt/miniconda3 /opt/anaconda3 /opt/homebrew/Caskroom/miniconda/base \
         /usr/local/miniconda3 /usr/local/anaconda3; do
    try_python "$d/bin/python3"
done

try_python python3
try_python python

if [ -z "$PYEXE" ]; then
    case "$(uname -s)" in
        Darwin) case "$(uname -m)" in
                    arm64) SH=Miniconda3-latest-MacOSX-arm64.sh ;;
                    *)     SH=Miniconda3-latest-MacOSX-x86_64.sh ;;
                esac ;;
        *)      case "$(uname -m)" in
                    aarch64|arm64) SH=Miniconda3-latest-Linux-aarch64.sh ;;
                    *)             SH=Miniconda3-latest-Linux-x86_64.sh ;;
                esac ;;
    esac
    URL="https://repo.anaconda.com/miniconda/$SH"

    echo
    echo "  No Python 3.8 or newer was found."
    echo
    echo "  pyTECTOR needs one. The recommended choice is Miniconda: a small"
    echo "  Python distribution that installs into your home folder, needs no"
    echo "  root, and brings the conda package manager, which supplies scipy"
    echo "  and Qt as prebuilt binaries instead of compiling them."
    echo
    echo "  This script can fetch and install it for you, from the official"
    echo "  site:"
    echo "    $URL"
    echo "  About 100 MB, into $HOME/miniconda3. Nothing outside your home"
    echo "  folder is changed."
    echo
    printf "  Download and install Miniconda now? [Y/n] "
    read -r ans
    case "$ans" in
        n|N|no|NO|No)
            echo
            echo "  Setup stopped: pyTECTOR has no Python to run on."
            echo "  Install Miniconda from https://www.anaconda.com/download/success"
            echo "  and run install.command again."
            exit 1 ;;
    esac

    echo
    echo "  Downloading Miniconda ..."
    if command -v curl >/dev/null 2>&1; then
        curl -fL --progress-bar -o "/tmp/$SH" "$URL" || { echo "  Download failed."; exit 1; }
    elif command -v wget >/dev/null 2>&1; then
        wget -O "/tmp/$SH" "$URL" || { echo "  Download failed."; exit 1; }
    else
        echo "  Neither curl nor wget is available. Install Miniconda by hand from"
        echo "  https://www.anaconda.com/download/success"
        exit 1
    fi

    echo "  Installing Miniconda into $HOME/miniconda3 ..."
    sh "/tmp/$SH" -b -p "$HOME/miniconda3" || { echo "  Install failed."; exit 1; }
    rm -f "/tmp/$SH"
    try_python "$HOME/miniconda3/bin/python3"
    [ -n "$PYEXE" ] || { echo "  Miniconda did not appear where expected."; exit 1; }
    echo "  Miniconda installed."
fi

echo "      Using: $PYEXE"
PYDIR=$(dirname "$PYEXE")
for c in "$PYDIR/conda" "$PYDIR/../condabin/conda"; do
    [ -z "$CONDA" ] && [ -x "$c" ] && CONDA="$c"
done
[ -n "$CONDA" ] && echo "      conda: $CONDA"

# --- 2. dependencies --------------------------------------------------------
echo
echo "[2/5] Installing numpy, scipy, matplotlib and PyQt5 ..."
echo
"$PYEXE" -m pip install --upgrade pip >/dev/null 2>&1
# A distribution-managed python refuses to install into itself (PEP 668); the
# per-user location is the polite answer there, and is harmless elsewhere.
"$PYEXE" -m pip install -r requirements.txt \
    || "$PYEXE" -m pip install --user -r requirements.txt \
    || true

# --- 3. verify --------------------------------------------------------------
need() {
    "$PYEXE" -c "import $1" >/dev/null 2>&1 || MISSING="$MISSING $2"
}
collect_missing() {
    MISSING=""
    need numpy numpy
    need scipy scipy
    need matplotlib matplotlib
    need PyQt5.QtWidgets pyqt
}

echo
echo "[3/5] Checking that all four import ..."
collect_missing

if [ -n "$MISSING" ] && [ -n "$CONDA" ]; then
    echo "      pip did not supply:$MISSING"
    echo "      Trying conda-forge instead ..."
    echo
    # shellcheck disable=SC2086
    "$CONDA" install -y -c conda-forge $MISSING
    echo
    collect_missing
fi

if [ -n "$MISSING" ]; then
    echo
    echo "  Setup could not install:$MISSING"
    echo
    echo "  Install them by hand and run install.command again:"
    echo "      \"$PYEXE\" -m pip install numpy scipy matplotlib PyQt5"
    echo
    if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
        echo "  On Apple Silicon, PyQt5 needs a release with an arm64 wheel"
        echo "  (5.15.10 or newer). If pip started compiling Qt from source,"
        echo "  install it through conda instead:"
        echo "      conda install -c conda-forge pyqt"
        echo
    fi
    exit 1
fi
echo "      numpy, scipy, matplotlib and PyQt5 all import."

# --- 4. record the interpreter and compile-check -----------------------------
printf '%s\n' "$PYEXE" > python-path.txt

echo
echo "[4/5] Checking that the program compiles ..."
if ! "$PYEXE" -m py_compile pyTECTOR.py; then
    echo "      Compile check failed. The download may be incomplete: fetch the"
    echo "      repository again rather than patching this copy."
    exit 1
fi
echo "      pyTECTOR.py compiles."

# --- 5. make the launcher double-clickable -----------------------------------
echo
echo "[5/5] Making the launcher executable ..."
chmod +x pyTECTOR.command 2>/dev/null && echo "      Done." \
    || echo "      Could not chmod pyTECTOR.command; run it as: sh pyTECTOR.command"

echo
echo "  pyTECTOR is installed. Start it with ./pyTECTOR.command, or by"
echo "  double-clicking pyTECTOR.command in Finder."
echo
