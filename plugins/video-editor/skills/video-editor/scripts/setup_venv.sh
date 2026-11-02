#!/bin/bash
# Create the kit's Python venv (numpy, OpenCV, librosa, Pillow, SciPy) on Mac or Windows (Git Bash). Idempotent.
# Usage: scripts/setup_venv.sh   [EXTRAS=ai for the optional local AI tools: audio_tags, stems, footage_search, reframe_916, shot_check]
#        (venv lives at ~/.editing-kit/venv so plugin updates don't wipe it; override with EDITKIT_VENV)
set -e
V="${EDITKIT_VENV:-$HOME/.editing-kit/venv}"; mkdir -p "$(dirname "$V")"
# Skip Windows' Microsoft Store placeholders (WindowsApps\python*.exe), which exist but don't run.
PY=""; for c in python3 python py; do p=$(command -v $c) && "$p" -c "" 2>/dev/null && { PY=$p; break; }; done
[ -n "$PY" ] || { echo "install Python 3 first" >&2; exit 1; }
[ -x "$V/bin/python" ] || [ -x "$V/Scripts/python.exe" ] || "$PY" -m venv "$V"
VP="$V/bin/python"; [ -x "$VP" ] || VP="$V/Scripts/python.exe"
"$VP" -m pip -q install --upgrade pip numpy opencv-python-headless librosa pillow scipy soundfile openpyxl
if [ "$EXTRAS" = ai ]; then
  # ~2-3 GB. Model weights download on first use (HuggingFace cache, ~/.cache/torch); PANNs and MediaPipe need one manual file each (see the script headers).
  "$VP" -m pip -q install torch torchaudio transformers panns-inference demucs mediapipe
fi
"$VP" -c "import cv2, numpy; print('venv ready:', cv2.__version__, numpy.__version__)"
