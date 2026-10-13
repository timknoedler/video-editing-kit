#!/bin/bash
# Create the kit's Python venv (numpy, OpenCV, librosa, Pillow, SciPy) on Mac or Windows (Git Bash). Idempotent.
# Usage: scripts/setup_venv.sh   (venv lives at ~/.editing-kit/venv so plugin updates don't wipe it; override with EDITKIT_VENV)
set -e
V="${EDITKIT_VENV:-$HOME/.editing-kit/venv}"; mkdir -p "$(dirname "$V")"
# Skip Windows' Microsoft Store placeholders (WindowsApps\python*.exe), which exist but don't run.
PY=""; for c in python3 python py; do p=$(command -v $c) && "$p" -c "" 2>/dev/null && { PY=$p; break; }; done
[ -n "$PY" ] || { echo "install Python 3 first" >&2; exit 1; }
[ -x "$V/bin/python" ] || [ -x "$V/Scripts/python.exe" ] || "$PY" -m venv "$V"
VP="$V/bin/python"; [ -x "$VP" ] || VP="$V/Scripts/python.exe"
"$VP" -m pip -q install --upgrade pip numpy opencv-python-headless librosa pillow scipy openpyxl
"$VP" -c "import cv2, numpy; print('venv ready:', cv2.__version__, numpy.__version__)"
