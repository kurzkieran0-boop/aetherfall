#!/usr/bin/env bash
# One command: ./mailman/run_all.sh   (re-runnable; every step resumes / skips finished work)
#   MM_RENDER_FPS=30     render rate (15 = fast draft; frames get doubled)
#   MM_RES=1080x1920     render resolution (540x960 = fast draft, upscaled)
#   MM_LENGTH_SCALE=0.69 Piper speaking pace (lower = faster; generated fast at the source, no atempo)
#   MM_REBUILD=1         force rebuilding the Blender town
set -euo pipefail
cd "$(dirname "$0")"
python3 -c "import bpy, piper, faster_whisper, PIL, numpy" 2>/dev/null || \
  pip install bpy piper-tts faster-whisper pillow numpy fonttools
[ -f voices/en_US-lessac-high.onnx ] || python3 -m piper.download_voices --download-dir voices en_US-lessac-high
[ -f assets/QRBlack.ttf ] || { echo "missing assets/QRBlack.ttf (Montserrat Black, OFL)"; exit 1; }

echo "== 1. narration (Piper, silence squeeze, whisper word timings)"; python3 tts.py
echo "== 2. shot list";                       python3 make_shots.py
echo "== 3. faces, envelope wallpaper, cards"; python3 assets.py
if [ ! -f build/town.blend ] || [ "${MM_REBUILD:-0}" = "1" ]; then
  echo "== 4. build town + interiors + cast";   python3 build_town.py 2>&1 | grep -E "saved|Error" || true
fi
echo "== 5. render shots (log: build/render_progress.log)"
python3 render_shots.py 0 1 > build/render_w0.out 2>&1
echo "== 6. assemble";                        python3 assemble.py
echo "== 7. verify";                          python3 verify.py
