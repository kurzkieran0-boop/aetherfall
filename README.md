# THE VILLAGE THAT REPEATS — animated story series template

A free, offline, zero-API-key pipeline that turns one JSON script into a narrated, captioned,
scored 3D animated short. Part 1 renders as a **150 s** video in **9:16 (1080×1920)** and
**16:9 (1920×1080)**.

Stack: Vite + Three.js + GSAP (render), Kokoro TTS (voice), Web Audio (score), Playwright + ffmpeg (export).
It needs no paid services and no connectors.

## Quick start

```bash
npm install                      # three, gsap, vite, playwright, fonts (bundled locally via @fontsource)
pip install -r requirements.txt  # kokoro-onnx + soundfile (Kokoro-82M, offline once weights are cached)

npm run export                   # voice -> timeline -> deterministic frame capture -> 2 MP4s (+ duration check)
npm run dev                      # live preview at http://127.0.0.1:5173/?ep=part1   (click / space to play)
npm run shots                    # QA stills of every scene, both aspects -> out/shots/
```

Outputs:

| file | what |
|---|---|
| `out/part1_9x16.mp4` | 1080×1920, H.264 + AAC, 30 fps |
| `out/part1_16x9.mp4` | 1920×1080, H.264 + AAC, 30 fps |
| `out/part1_mix.wav` | final score + SFX + voice mix (48 kHz stereo) |
| `out/part1_export.json` | measured durations / pass-fail report |

`npm run export` exits non-zero if any MP4 is shorter than 120 s (`series.json → timing.minTotal`).

Useful flags: `npm run export -- part1 --only=9x16`, `--seconds=10` (quick preview cut, skips the
duration check), `--rs=1` (render the 3D at full resolution instead of 0.75× + FXAA), `--skip-prepare`.
Preview URL params: `?ep=part1&aspect=16:9`, `?w=1080&h=1920`.

## How it fits together

```
public/series.json                 series template: title/end cards, palettes, timing rules (min 120 s, target 135–150 s)
public/episodes/part1/script.json  the authored episode: scenes, narration, camera keys, actors, events, sound mood
        │  scripts/tts.py          Kokoro voice per sentence (cached by hash), word timings, whisper FX for scene 10
        ▼
public/episodes/part1/audio/voice_manifest.json + .cache/*.wav
        │  scripts/build-timeline.mjs
        ▼
public/episodes/part1/timeline.json  durations, absolute word timings, captions, camera spline, palette keys,
                                     actor keys, events; plus audio/line_XX_<scene>.wav (one WAV per narration line)
        │  src/ (engine)           Three.js village + characters + GLSL fog/god-rays/post, GSAP overlays, Web Audio score
        ▼
scripts/export.mjs                 Playwright calls window.__vtr.frame(t) for every frame -> JPEG -> ffmpeg (+ mix.wav)
```

### Durations are driven by the voice
Each scene runs `leadIn + voice (sentences + breathing gaps + optional pauseAfter) + 0.8 s breathing pause + hold`.
If the total is under `targetMin` (135 s, never below the hard 120 s), `build-timeline` lengthens the breathing pauses
between lines (up to 0.7 s), then the ambient holds and camera drifts (weighted by each scene's `stretch`). If it is over
`targetMax` (150 s), it tightens holds first, then gaps. Every time anchor (`{ "s": 2, "edge": "start", "o": -0.3 }`)
is relative to the measured voice, so picture, captions and sound stay in sync when the voice changes.

### Voice (free, offline)
`scripts/tts.py` tries, in order: **kokoro** (PyTorch, `pip install kokoro`) → **kokoro-onnx** (same Kokoro-82M model; weights
fetched once from the kokoro-onnx GitHub release into `.models/`) → **piper** → **edge-tts** → **espeak-ng**.
Part 1 uses a hushed young blend (`af_heart` 60% + `af_nicole` 40%, speed 0.9). Scene 10 uses `af_nicole` plus a
phase-randomised "whisperisation" pass. Word timings come from silence detection plus syllable weighting.
(This build used **kokoro-onnx**: the sandbox it was built in blocks Hugging Face, which the PyTorch build needs.)

### Picture
- One continuous camera: every scene's camera keys join one global, monotone cubic Hermite spline, so there are no
  hard cuts. Breaks happen only at `cut` keys, and only inside a reset glitch or a fog pulse.
- Low-poly procedural village: well, bakery with creaking step, windmill, clock tower (stopped at 3:07, bell, lantern,
  forbidden door), a two-room house with kitchen and bedroom, road loop, trees and hills. Characters are rigged from primitives.
- GLSL: animated height fog patched into every material, a sky dome with sun and clouds, quarter-res screen-space god-rays,
  a composite pass (ACES, teal/cream split-tone, chromatic aberration, vignette, per-frame film grain, FXAA), and a reset
  glitch (horizontal tear, rewind smear/roll, scanlines, dawn flash).
- Captions: IM Fell English italic, word-by-word highlight from the same timings as the voice. The handwriting reveal is an
  SVG line-draw (Homemade Apple, letter-by-letter stroke-dash), anchored to the 3D door.
- The palette uses warm dawn amber, deep teal shadows and cream highlights. Red appears only in the chalk marks.

### Audio (procedural, `src/audio.js`)
Detuned drone, pad, a music-box lullaby motif and a ticking clock that gets louder toward the cliffhanger. The bell is
synthesised in code from additive inharmonic partials; the out-of-order bell is a reversed swell into a detuned strike.
SFX are synthesised too: rewind, tray clatter, creaks, rain, cart rumble and carving scratch. The score bus is ducked
**10 dB** under every narration region and cuts to total silence at "Out of order." The same graph runs in
realtime for preview and in an `OfflineAudioContext` for export.

## Making Part 2 (series template)

```bash
npm run new-part -- part2      # scaffolds public/episodes/part2/script.json (title card "PART 2", end card "PART 3 — …")
# edit scenes / narration / camera keys
npm run export -- part2        # voice, timeline, MP4s, duration check
```

The engine renders any `timeline.json`. You author `script.json`, and `build-timeline` compiles it to `timeline.json`
with measured durations. The title card, bell sting and "PART X — Follow so you don't miss it." end card come from
`series.json` and the episode number. You never draw them by hand.

### script.json reference (per scene)
| key | meaning |
|---|---|
| `palette`, `paletteKeys[]` | named palette from `series.json`; keyed changes (`cut: true` snaps, overrides like `fogDensity`) |
| `narration[]` | sentences (string or `{ text, speed, voice, pauseAfter }`); `whisper: true` for whispered scenes |
| `camera[]` | `{ at, pos, look, fov, cut }`. `fov` is measured across the shorter screen side, so framing holds in 9:16 and 16:9 |
| `actors{}` | `wren, mother, baker, oldman, sweeper, bucketman, goat, cart, shadow, bell` → keys `{ at, pos, rot, action }` |
| `events[]` | `bell, bellWrong, reset, clatter, creak, rainStart, rumble, chime, sting, hush, scratch, doorCreak, silence, blackout, glitchFrame` |
| `transitionIn` | `blend` (default), `reset` (glitch + snap to dawn), `fog` (fog pulse hides the move), `fadeFromBlack` |
| `overlays[]` | `{ type: "handwriting", text, anchor:[x,y,z], from, to }` |
| `set{}` | `chalk, candle, rain, millStopped, towerDoorAjar` |
| `sound{}` | `{ drone, pad, box, tick, chord }` (chords: Dm, Bb, Gm, F, A) |

Time values (`at`, `from`, `to`): `0..1` (fraction of the scene), `{ "t": s }`, `{ "s": i, "edge": "start"|"end", "o": s }`,
or `{ "end": s }` (relative to the end of the narration).

Actions: `idle, walk, lean, stiffen, watchWindow, sitUpInBed, sitInBed, carryTray, dropTray, dropLoop, sweep, bucket,
joke, walkJoke, freeze, stir, patHair, smile, loom, graze, roll, swing, swingWrong, still, hidden`. Loop actions restart
on every `reset` event, so the villagers repeat identical moves.
