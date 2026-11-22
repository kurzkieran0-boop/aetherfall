# THE MIDNIGHT COURIER — procedural video series

A zero-API-key, fully procedural 9:16 animated story engine: Vite + Canvas 2D
(painterly paper-cut layers) + WebGL2 (post: motion blur, grain, vignette) +
GSAP (seeked camera timelines) + Web Audio (procedural score & SFX) +
Kokoro TTS. Exported deterministically with Playwright + ffmpeg.

## Commands

```bash
npm install                 # vite, gsap
pip install kokoro-onnx soundfile   # Kokoro-82M (ONNX); weights in .cache/kokoro
npm run export              # voice -> fit -> build -> frames -> mux  => out/midnight-part1.mp4
npm run export -- part2     # any part folder under series/
npm run shots               # QA frames for every shot -> out/qa/<part>/
npm run dev                 # live preview with score + voice (after voice/fit)
```

Kokoro weights (`kokoro-v1.0.onnx`, `voices-v1.0.bin`) come from the
kokoro-onnx GitHub release and go in `.cache/kokoro/`. TTS fallback order:
Kokoro → Piper (`.cache/piper/*.onnx`) → edge-tts.

## Making a new part

Copy `series/part1/timeline.json` to `series/part2/timeline.json`, edit the
beats, and run `npm run export -- part2`. Nothing else changes.

* `beats[]`: `palette` (dusk / violet / midnight / predawn), `music` flags,
  `narration` (one WAV per line; `*key*` words turn gold; per-line `speed`,
  `gain`, `pause`), `tease` (end-of-beat question), `shots[]`, `cutaways[]`.
* shots: `scene` (skyline, rooftops, market, letter, library, door),
  `camera` {from, to, ease, whipIn, whipOut, shake}, `fx`, `sound`,
  `overlay`, optional `fromLine` (shot starts on that narration line).
* `duration: "auto"`: `scripts/fit.mjs` fits shots to the measured voice on
  the BPM grid (6–9 beats each, so 3.3–4.9 s and every cut on a beat), adds holds and
  cutaways until `minDuration` is reached, and **fails** outside
  `[minDuration, maxDuration]`. The export fails again on the final MP4 duration.

## Architecture

* `src/core/buildings.js`: procedural building generator (crooked
  tenements with fire escapes and laundry, canal houses, pagodas, greenhouses,
  copper domes, clock tower, Spire Library with exterior spiral stair, market
  stalls, iron bridges, terraces, canals).
* `src/core/citygen.js`: bakes depth layers sized to the camera range;
  rim light, paper grain and cut-paper shadows in `paint.js`.
* `src/core/stage.js`: dolly-camera parallax projection, sky, fog, light shafts.
* `src/core/juno.js`: procedural run / jump / climb / knock cycles + verlet scarf.
* `src/core/audio.js`: 110 BPM score, riser and drop, whooshes, rustles,
  bells, tram bell, hum, knocks; score ducked 8 dB under the voice.
* `src/core/engine.js`: `render(t)` is a pure function of time, so 4
  workers can render frame ranges in parallel.
