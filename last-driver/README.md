# LAST DRIVER — procedural 3D vertical video series

Three.js (WebGL2) cyberpunk thriller rendered deterministically in headless
Chromium: instanced skyscrapers with procedural lit-window shaders, rain-wet
streets with mirror reflections, market tunnel, skyway, drawbridge, Tower Nine,
PBR clearcoat hero car, traffic, drones, holo billboards, bloom, motion blur.
Same pipeline as `../midnight-courier` (Kokoro voice, beat-grid fitter,
procedural Web Audio score, Playwright + ffmpeg export).

```bash
npm install
npm run export            # -> out/last-driver-part1.mp4
npm run shots             # QA frame per shot -> out/qa/part1/
```

New part: write `series/part2/build_timeline.py` (or `timeline.json`) using
scenes `city` / `core`, camera modes `chase` / `orbit` / `track` / `world`,
and `car: {s: [from, to]}` positions along the route (see `src/world/city.js`).
