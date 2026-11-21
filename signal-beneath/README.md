# THE SIGNAL BENEATH — vertical neon-sonar story series

Free, zero-API-key animated story pipeline. **Vite + HTML Canvas 2D + GLSL fragment shader + GSAP.** No 3D.
Output: `out/signal-partN.mp4`, H.264/AAC, **1080x1920 (9:16), 30 fps, 120–170 s, < 50 MB**.

## Look
Near-black navy `#02060d`, electric cyan `#19f0ff` line art, magenta `#ff2e88` only for *the voice* and danger.
Neon bloom, CRT scanlines, faint chromatic aberration, marine snow, far-background bioluminescent jellyfish.
The world is cross-sections, sonar PPI, waveforms, spectrograms and bathymetric contours. Captions are typed
word-by-word (letter by letter, blinking cursor) in VT323, inside the safe area (nothing in the top 10% / bottom 20%).
Scene changes are sonar-ping wipes from the center (no hard cuts); the end card follows a cut-to-black + one glitch frame.

## Run
```bash
npm install
pip install -r requirements.txt        # Kokoro (ONNX); falls back to piper -> edge-tts
npm run voice                          # Kokoro TTS -> one radio-processed WAV per narration line
npm run timeline                       # durations from voice length + 0.8 s breath; auto-lengthen to >= 120 s
npm run dev                            # live preview with the Web Audio score (click PLAY)
npm run shots                          # screenshots of every scene + safe-area text audit -> out/shots/
npm run export                         # deterministic Playwright capture + ffmpeg mux -> out/signal-part1.mp4
```
`export` fails (exit 1) if the MP4 is < 120 s or > 170 s, not 1080x1920, > 50 MB after the crf-24 re-encode,
or if the 1.5 s "total silence" before the final line is not actually silent.

## How a part is built
* `public/series.json` — series title, palette, safe area, timing rules (min/max/target, 0.8 s breathing pause),
  voice (Kokoro `af_sarah`, whisper delivery for the cliffhanger, 300–3400 Hz radio band-pass + static), template cards.
* `public/episodes/partN/timeline.json` — **the only per-part file**: scenes with `palette`, `visuals`, `visual`
  (renderer type + params), `sound` (mood, drone/static levels, ping interval, heartbeat/tone), `narration`.
  `npm run timeline` writes the measured `start`, `duration` and `voice` (sentence + word timings) back into it.
* Template pieces, automatic for every part: title card (series title + `PART X`) after the cold open, sonar sting,
  sonar-ping wipes, glitch cut, `PART X+1` end card (`endCard.text`).

### Scene renderer types (`src/scenes.js`)
`coldOpen`, `station`, `spectrum`, `countdown`, `triangulation`, `slowdown`, `glitchWords`, `terminalLog`,
`logZoom`, `cliffhanger` (+ template `titleCard`, `endCard`). Text, numbers, log lines, word marks and labels are
params, so new parts can reuse them; add a new type by adding an entry to `SCENES`.

### Audio (`src/audio.js`, rendered offline so picture and sound are sample-exact)
Sub-bass pressure drone + brown-noise rumble, sonar pings on a shared schedule that speeds up toward the cliffhanger,
radio static/crackle, heartbeat (synced to the ECG trace), per-scene sound design. Score ducked **-10 dB** under every
voice sentence; **fully silent for 1.5 s** before the final line.

### New part
```bash
npm run new-part -- 2      # scaffolds public/episodes/part2/timeline.json
# edit narration / visuals, then
npm run export -- part2    # -> out/signal-part2.mp4
```
