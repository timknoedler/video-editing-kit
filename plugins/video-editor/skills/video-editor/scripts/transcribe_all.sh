#!/bin/bash
# Transcribe every clip in probe.json with whisper.cpp (word-level JSON + SRT + TXT), skipping ones already done.
# Usage: transcribe_all.sh "<FOOTAGE_ROOT>" [model.bin]   (model: arg, else $WHISPER_MODEL, else the Mac default
#   ~/Library/Application Support/whisper.cpp/models/ggml-large-v3-turbo.bin, else ~/whisper.cpp/models/ggml-large-v3-turbo.bin on Windows)
# ~55 s per 6 min of audio on an M1. Put interviews first by running once with their names via ONLY="C0021 C0022".
set -e
ROOT="${1%/}"; M="${2:-$WHISPER_MODEL}"
for C in "$HOME/Library/Application Support/whisper.cpp/models/ggml-large-v3-turbo.bin" "$HOME/whisper.cpp/models/ggml-large-v3-turbo.bin"; do [ -n "$M" ] || { [ -f "$C" ] && M="$C"; }; done
[ -f "$M" ] || { echo "whisper model not found; set WHISPER_MODEL" >&2; exit 1; }
PY=$(command -v python3 || command -v python || command -v py)
E="${EDIT_DIR:-$ROOT/_edit}"; T="$E/transcripts"; W="$E/work"; mkdir -p "$T" "$W"
"$PY" -c "import json,sys;[print(r['file']) for r in json.load(open(sys.argv[1]))]" "$W/probe.json" | while IFS= read -r f; do
  n=$(basename "$f"); n="${n%.*}"
  [ -n "$ONLY" ] && [[ " $ONLY " != *" $n "* ]] && continue
  [ -f "$T/$n.json" ] && continue
  ffmpeg -v quiet -y -i "$ROOT/$f" -vn -ac 1 -ar 16000 "$W/$n.wav" </dev/null
  whisper-cli -m "$M" -f "$W/$n.wav" -l en -ojf -otxt -osrt -ml 1 -sow -of "$T/$n" >/dev/null 2>&1 </dev/null
  rm -f "$W/$n.wav"; echo "$n"
done
echo ALLDONE
