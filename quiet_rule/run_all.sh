#!/usr/bin/env bash
# One command: ./quiet_rule/run_all.sh   (re-runnable; every step resumes / skips finished work)
#   QR_WORKERS=1        parallel Blender render processes (CPU llvmpipe already uses every core)
#   QR_RENDER_FPS=30    render rate (15 = fast draft; frames get doubled to 30fps)
#   QR_RES=1080x1920    render resolution (540x960 = fast draft, upscaled)
#   QR_REBUILD=1        force rebuilding the Blender town
set -euo pipefail
cd "$(dirname "$0")"
WORKERS=${QR_WORKERS:-1}

python3 -c "import bpy, piper, faster_whisper, PIL, numpy" 2>/dev/null || \
  pip install bpy piper-tts faster-whisper pillow numpy fonttools
[ -f voices/en_US-hfc_female-medium.onnx ] || python3 -m piper.download_voices --download-dir voices en_US-hfc_female-medium
[ -f assets/QRBlack.ttf ] || { echo "missing assets/QRBlack.ttf (Montserrat Black, OFL)"; exit 1; }

echo "== 1. narration (Piper TTS + faster-whisper word timings)"; python3 tts.py
echo "== 2. shot list";                        python3 make_shots.py
echo "== 3. faces + insert cards";             python3 assets.py
if [ ! -f build/town.blend ] || [ "${QR_REBUILD:-0}" = "1" ]; then
  echo "== 4. build town in Blender";          python3 build_town.py 2>&1 | grep -E "saved|Error" || true
fi
echo "== 5. render shots ($WORKERS workers, log: build/render_progress.log)"
pids=()
for ((w=0; w<WORKERS; w++)); do
  python3 render_shots.py "$w" "$WORKERS" > "build/render_w$w.out" 2>&1 & pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
echo "== 6. assemble";                         python3 assemble.py
echo "== 7. verify";                           python3 verify.py
