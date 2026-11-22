// Fits a part's timeline.json to the measured voiceover:
//  - every cut lands on the 110 BPM grid; shots are 6–9 beats (3.3–4.9 s)
//  - shots anchored with "fromLine" start on that narration line
//  - if the total is under minDuration, holds are lengthened and cutaway
//    shots added until it passes; the run FAILS if outside [min, max]
// Writes build/<part>/data/timeline.json (consumed by the renderer).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const SCENE_LAYERS = {
  city: ['sky dome (cloud deck, lightning)', 'instanced skyscrapers (procedural lit-window shader, crown neon)', 'wet street + river (mirror reflections, rain ripples)', 'neon signs + holo billboards', 'market tunnel / skyway / drawbridge', 'traffic (instanced), river of headlights', 'drones', 'hero car (PBR clearcoat, light bars, volumetric beams)', 'rain streaks', 'bloom + motion blur + grain'],
  core: ['server hall (reflective floor, LED racks)', 'volumetric ceiling beams', 'wall of light + screen text', 'pedestal + port', 'Kira', 'bloom + grain'],
};

export function fit(part, opts = {}) {
  const dir = path.join(ROOT, 'series', part);
  const src = JSON.parse(fs.readFileSync(path.join(dir, 'timeline.json'), 'utf8'));
  const dataDir = path.join(ROOT, 'build', part, 'data');
  const man = JSON.parse(fs.readFileSync(path.join(dataDir, 'voice', 'manifest.json'), 'utf8'));
  const beat = 60 / src.bpm;
  const MIN = src.shotBeats?.min ?? 6, MAX = src.shotBeats?.max ?? 9;
  const minD = src.minDuration ?? 120, maxD = src.maxDuration ?? 170;
  const voiceLines = man.lines;
  const lineOf = (bi, li) => voiceLines.find((l) => l.beat === src.beats[bi].id && l.line === li);

  // ---- per-beat plan (beats in grid units); padding loop adjusts `extra`
  const plan = src.beats.map((b, bi) => ({
    b, bi, extra: 0, cut: [...(b.cutaways || [])],
    shots: b.shots.map((s) => ({ ...s })),
    anchored: b.shots.some((s) => s.fromLine !== undefined),
    lines: (b.narration || []).map((n, li) => ({ ...(typeof n === 'string' ? { text: n } : n), li, voice: lineOf(bi, li) })),
  }));
  const endBeats = src.endCard?.beats ?? 8;

  function layout() {
    let g = 0; // grid cursor (beats)
    const shots = [], lines = [], beatsOut = [];
    for (const P of plan) {
      const { b, lines: L } = P;
      const lead = b.lead ?? 0.3, gap = b.gap ?? 0.22, tail = b.tail ?? 1.0;
      const beatStartG = g;
      const t0 = g * beat;
      const placed = [];
      if (!P.anchored) {
        const speech = L.reduce((a, l) => a + l.voice.duration, 0) + gap * Math.max(0, L.length - 1);
        let nb = Math.ceil((lead + speech + tail) / beat);
        nb = Math.max(nb, P.shots.length * MIN) + P.extra;
        // keep average shot length <= MAX by adding cutaways
        while (nb > P.shots.length * MAX) {
          const c = P.cut.shift() || { ...P.shots[P.shots.length - 2], id: `${b.id}-x${P.shots.length}` };
          P.shots.splice(P.shots.length - 1, 0, { ...c, cutaway: true });
        }
        const slack = nb * beat - (lead + speech + tail);
        const g2 = gap + Math.min(0.55, Math.max(0, slack * 0.5) / Math.max(1, L.length - 1));
        let t = t0 + lead;
        for (const l of L) { placed.push({ l, start: t }); t += l.voice.duration + g2; }
        // shots: even split of nb into n parts, each within [MIN, MAX]
        const n = P.shots.length;
        const base = Math.floor(nb / n);
        let rem = nb - base * n;
        let gg = g;
        P.shots.forEach((s, i) => {
          const k = base + (rem > 0 && i % 2 === 0 ? 1 : 0) + (rem > 0 && i === n - 1 ? rem - (i % 2 === 0 ? 1 : 0) : 0);
          if (rem > 0 && i % 2 === 0) rem--;
          s._g0 = gg; s._nb = Math.min(MAX, Math.max(MIN, k)); gg += s._nb;
        });
        g = gg;
      } else {
        // anchored: shots start on their lines; lines before an anchor flow
        let lineCursor = t0 + lead;
        let li = 0;
        P.shots.forEach((s, si) => {
          const start = g * beat;
          const next = P.shots.slice(si + 1).find((x) => x.fromLine !== undefined);
          const upto = next ? next.fromLine : L.length;
          let lastEnd = start;
          if (s.fromLine !== undefined || si === 0) {
            for (; li < upto; li++) {
              const l = L[li];
              const st = Math.max(lineCursor, (li === s.fromLine ? start + (si === 0 ? lead : 0.14) : lineCursor) + (l.pause || 0));
              placed.push({ l, start: st });
              lastEnd = st + l.voice.duration;
              lineCursor = lastEnd + gap;
            }
          }
          const need = s.beats ?? Math.ceil((lastEnd - start + (si === P.shots.length - 1 ? tail : 0.3)) / beat);
          let nb = Math.min(MAX, Math.max(MIN, need));
          if (si === P.shots.length - 1) nb = Math.min(MAX, nb + P.extra);
          s._g0 = g; s._nb = nb; g += nb;
        });
      }
      const beatEnd = g * beat;
      for (const pl of placed) {
        const v = pl.l.voice;
        lines.push({
          idx: v.idx, beat: b.id, li: pl.l.li, file: v.file, text: v.text, gain: pl.l.gain ?? 1,
          start: +pl.start.toFixed(3), end: +(pl.start + v.duration).toFixed(3), dur: v.duration,
          words: v.words.map((w, wi) => ({ w: w.w, s: +(pl.start + w.s).toFixed(3), e: +(pl.start + w.e).toFixed(3), key: /\*/.test(((typeof src.beats[P.bi].narration[pl.l.li] === 'string' ? src.beats[P.bi].narration[pl.l.li] : src.beats[P.bi].narration[pl.l.li].text).split(/\s+/)[wi]) || '') })),
        });
      }
      for (const s of P.shots) shots.push({ s, b, bi: P.bi });
      beatsOut.push({ id: b.id, name: b.name, start: beatStartG * beat, end: beatEnd, P });
    }
    const endStart = g;
    g += endBeats;
    return { shots, lines, beatsOut, endStart, total: g * beat };
  }

  let L = layout();
  // ---- pad to the minimum duration: lengthen holds, add cutaways
  let guard = 0;
  while (L.total < minD + 5 && guard++ < 200) {
    const flow = plan.filter((p) => !p.anchored);
    const pool = flow.length ? flow : plan;
    // grow the beat with the lowest beats-per-shot ratio
    let best = null, ratio = 1e9;
    for (const p of pool) {
      const nb = p.shots.reduce((a, s) => a + (s._nb || MIN), 0);
      const r = nb / p.shots.length;
      if (r < ratio) { ratio = r; best = p; }
    }
    best.extra += 1;
    L = layout();
  }
  if (opts.verbose) console.log(`fit: padded ${guard} beat(s)`);

  // ---- resolve shots
  const shots = [];
  const sfx = [];
  const overlays = [];
  const lineIn = (bid, li) => L.lines.find((l) => l.beat === bid && l.li === li);
  L.shots.forEach(({ s, b }, i) => {
    const start = s._g0 * beat, dur = s._nb * beat;
    const shot = {
      id: s.id, beat: b.id, scene: s.scene, palette: s.palette || b.palette, start: +start.toFixed(4), end: +(start + dur).toFixed(4), dur: +dur.toFixed(4), beats: s._nb,
      camera: s.camera, car: s.car, fx: JSON.parse(JSON.stringify(s.fx || {})), sceneOpts: s.sceneOpts, grade: s.grade, flashIn: s.flashIn, seed: s.seed,
      transition: s.transition || (s.camera?.whipIn ? 'whip' : 'cut'), cutaway: !!s.cutaway,
      layers: s.layers || SCENE_LAYERS[s.scene] || [],
    };
    // text reveals synced to narration lines
    for (const tx of shot.fx.text || []) {
      if (tx.line === undefined) continue;
      const l = lineIn(b.id, tx.line);
      if (!l) continue;
      const pr = tx.part || [0, 1];
      tx.at = [(l.start + pr[0] * l.dur - start) / dur, (l.start + pr[1] * l.dur - start) / dur].map((v) => +Math.min(1, Math.max(0, v)).toFixed(4));
    }
    shot.narration = L.lines.filter((l) => l.start < shot.end && l.end > shot.start).map((l) => l.text).join(' ');
    for (const so of s.sound || []) {
      let t = start + (so.at === 'end' ? dur - 0.05 : so.at === 'start' || so.at === undefined ? 0 : so.at * dur);
      if (so.atLine !== undefined) { const l = lineIn(b.id, so.atLine); if (l) t = l.start; }
      t += so.offset || 0;
      const ev = { t: +t.toFixed(3), type: so.sfx, dur: so.dur, gain: so.gain, n: so.n, shot: s.id };
      if (so.sfx === 'riser' && so.endLine !== undefined) {
        const l = lineIn(b.id, so.endLine);
        ev.t = start;
        ev.dur = +(l.start - start).toFixed(3);
      }
      sfx.push(ev);
    }
    if (s.camera?.whipOut) sfx.push({ t: +(start + dur - 0.02).toFixed(3), type: 'whoosh', dir: s.camera.whipOut === 'left' ? -1 : 1, shot: s.id });
    if (s.camera?.whipIn) {
      const prev = shots[shots.length - 1];
      if (!prev || !prev.camera?.whipOut) sfx.push({ t: +start.toFixed(3), type: 'whoosh', dir: s.camera.whipIn === 'left' ? -1 : 1, shot: s.id });
    }
    if (s.overlay) {
      const o = { style: s.overlay.style, text: s.overlay.text };
      if (o.style === 'hook') { o.start = start; o.end = start + dur; }
      else if (o.style === 'title') { o.start = start + 0.15; o.end = start + Math.min(dur, 3.2); }
      else { o.start = start + 0.2; o.end = start + dur; }
      overlays.push(o);
    }
    shots.push(shot);
  });
  // teases at the end of each beat
  for (const bo of L.beatsOut) {
    const b = src.beats.find((x) => x.id === bo.id);
    if (!b.tease) continue;
    const lastEnd = Math.max(bo.start, ...L.lines.filter((l) => l.beat === b.id).map((l) => l.end));
    const st = Math.max(lastEnd + 0.12, bo.end - 1.7);
    if (bo.end - st >= 0.55) overlays.push({ style: 'tease', text: b.tease, start: +st.toFixed(3), end: +(bo.end - 0.03).toFixed(3) });
  }
  // end card
  const ec = src.endCard;
  if (ec) {
    const start = L.endStart * beat, dur = endBeats * beat;
    shots.push({
      id: ec.id, beat: 'END', scene: ec.scene, palette: ec.palette, start: +start.toFixed(4), end: +(start + dur).toFixed(4), dur: +dur.toFixed(4), beats: endBeats,
      camera: ec.camera, car: ec.car, fx: ec.fx || {}, sceneOpts: ec.sceneOpts, flashIn: ec.flashIn, transition: 'smash', layers: SCENE_LAYERS[ec.scene], narration: '',
    });
    if (ec.overlay) overlays.push({ style: ec.overlay.style, text: ec.overlay.text, start: start + 0.15, end: start + dur + 1 });
    for (const so of ec.sound || []) sfx.push({ t: +(start + (so.at || 0) * dur).toFixed(3), type: so.sfx, gain: so.gain });
  }
  // music sections
  const music = [];
  for (const bo of L.beatsOut) {
    const b = src.beats.find((x) => x.id === bo.id);
    if (b.musicDrop && b.dropLine !== undefined) {
      const l = lineIn(b.id, b.dropLine);
      music.push({ start: bo.start, end: l.start, flags: b.music, beat: b.id });
      music.push({ start: l.start, end: bo.end, flags: b.musicDrop, beat: b.id + '-drop' });
    } else music.push({ start: bo.start, end: bo.end, flags: b.music, beat: b.id });
  }
  if (ec) music.push({ start: L.endStart * beat, end: L.total + 2, flags: ec.music || music[music.length - 1].flags, beat: 'END' });
  L.lines.sort((a, b) => a.start - b.start);
  L.lines.forEach((l, i) => { l.nextStart = L.lines[i + 1]?.start ?? null; });
  sfx.sort((a, b) => a.t - b.t);

  const out = {
    series: src.series, part: src.part, output: src.output, width: src.width, height: src.height, fps: src.fps, bpm: src.bpm,
    duration: +L.total.toFixed(4), frames: Math.round(L.total * src.fps), voice: src.voice,
    beats: L.beatsOut.map((b) => ({ id: b.id, name: b.name, start: +b.start.toFixed(3), end: +b.end.toFixed(3) })),
    shots, lines: L.lines, overlays, music, sfx,
  };
  const problems = [];
  if (out.duration < minD || out.duration > maxD) problems.push(`duration ${out.duration.toFixed(2)}s outside [${minD}, ${maxD}]`);
  for (const s of shots) if (s.dur > 5.0 + 1e-6) problems.push(`shot ${s.id} is ${s.dur.toFixed(2)}s (> 5s)`);
  for (const l of L.lines) {
    const sh = shots.filter((s) => s.start < l.end && s.end > l.start);
    if (!sh.length) problems.push(`line ${l.beat}.${l.li} not covered by a shot`);
  }
  fs.mkdirSync(dataDir, { recursive: true });
  fs.writeFileSync(path.join(dataDir, 'timeline.json'), JSON.stringify(out, null, 1));
  return { out, problems };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const part = process.argv[2] || process.env.PART || process.env.npm_package_config_part || 'part1';
  const { out, problems } = fit(part, { verbose: true });
  console.log(`fit ${part}: ${out.duration.toFixed(2)}s, ${out.shots.length} shots, ${out.lines.length} lines, cuts on ${out.bpm} BPM grid`);
  for (const b of out.beats) {
    const sh = out.shots.filter((s) => s.beat === b.id);
    console.log(`  ${b.id.padEnd(3)} ${(b.end - b.start).toFixed(2).padStart(6)}s  ${sh.map((s) => `${s.id}:${s.dur.toFixed(2)}`).join('  ')}`);
  }
  if (problems.length) { console.error('FIT FAILED:\n  ' + problems.join('\n  ')); process.exit(1); }
}
