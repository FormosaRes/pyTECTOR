#!/bin/sh
# pyTECTOR launcher for macOS and Linux, the counterpart of pyTECTOR.bat.
#
# On macOS a .command file is double-clickable from Finder. If it is not,
# it has lost its execute bit; restore it with
#
#     chmod +x pyTECTOR.command
#
# Picks the first interpreter that can actually import PyQt5, so a machine
# with both a system python and a conda python does not fail on whichever
# one happens to be first on PATH.
set -e
cd "$(dirname "$0")"

for py in "$PYTECTOR_PYTHON" python3 python; do
    [ -n "$py" ] || continue
    command -v "$py" >/dev/null 2>&1 || continue
    if "$py" -c 'import PyQt5' >/dev/null 2>&1; then
        exec "$py" pyTECTOR.py "$@"
    fi
done

echo "No Python with PyQt5 was found."
echo
echo "Install the dependencies first:"
echo "    python3 -m pip install numpy scipy matplotlib PyQt5"
echo
echo "On an Apple Silicon Mac, PyQt5 needs a build with an arm64 wheel"
echo "(5.15.10 or newer). If pip tries to compile it from source, use"
echo "conda instead:"
echo "    conda install -c conda-forge pyqt"
echo
echo "To point this launcher at a specific interpreter, set PYTECTOR_PYTHON."
exit 1
