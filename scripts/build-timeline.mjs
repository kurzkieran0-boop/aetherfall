#!/usr/bin/env node
// Builds public/episodes/<ep>/timeline.json from script.json + the measured voiceover.
//  - scene duration = leadIn + voice (sentences + breathing gaps) + breathPause(0.8s) + hold
//  - if the episode is shorter than series.timing.targetMin (and never below minTotal=120s)
//    the ambient holds, camera drifts and the breathing pauses between lines are lengthened
//    until it passes; if it is longer than targetMax they are tightened (never below floor).
//  - writes one WAV per narration line (sentence clips + measured gaps), absolute word timings,
//    caption chunks, global camera spline keys, palette keys, actor keys and sound events.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ep = process.argv[2] || 'part1';
const epDir = path.join(ROOT, 'public', 'episodes', ep);
const series = JSON.parse(fs.readFileSync(path.join(ROOT, 'public', 'series.json'), 'utf8'));
const script = JSON.parse(fs.readFileSync(path.join(epDir, 'script.json'), 'utf8'));
const manifestPath = path.join(epDir, 'audio', 'voice_manifest.json');
if (!fs.existsSync(manifestPath)) {
  console.error(`[timeline] missing ${manifestPath} — run "npm run voice" first`);
  process.exit(1);
}
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const T = { ...series.timing, ...(script.timing || {}) };
const r3 = (x) => Math.round(x * 1000) / 1000;

// ------------------------------------------------------------------ WAV helpers (PCM16 mono)
function readWav(file) {
  const b = fs.readFileSync(file);
  let off = 12, fmt = null, data = null;
  while (off < b.length) {
    const id = b.toString('ascii', off, off + 4);
    const size = b.readUInt32LE(off + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(off + 10), sr: b.readUInt32LE(off + 12), bits: b.readUInt16LE(off + 22) };
    if (id === 'data') data = b.subarray(off + 8, off + 8 + size);
    off += 8 + size + (size & 1);
  }
  if (!fmt || fmt.bits !== 16 || fmt.ch !== 1) throw new Error(`unsupported wav ${file}`);
  return { sr: fmt.sr, pcm: new Int16Array(data.buffer.slice(data.byteOffset, data.byteOffset + data.length)) };
}
function writeWav(file, sr, pcm) {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0); h.writeUInt32LE(36 + pcm.length * 2, 4); h.write('WAVE', 8);
  h.write('fmt ', 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22);
  h.writeUInt32LE(sr, 24); h.writeUInt32LE(sr * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34);
  h.write('data', 36); h.writeUInt32LE(pcm.length * 2, 40);
  fs.writeFileSync(file, Buffer.concat([h, Buffer.from(pcm.buffer, pcm.byteOffset, pcm.length * 2)]));
}

// ------------------------------------------------------------------ durations
const scenes = script.scenes.map((sc, i) => {
  const m = manifest.scenes.find((s) => s.id === sc.id);
  if (!m) throw new Error(`voice manifest has no scene ${sc.id}; re-run npm run voice`);
  return {
    src: sc, index: i, sentences: m.sentences,
    pauses: (sc.narration || []).map((x) => (typeof x === 'object' && x.pauseAfter) || 0),
    leadIn: sc.leadIn ?? T.defaultLeadIn,
    hold: sc.hold ?? T.defaultHold,
    stretch: sc.stretch ?? 1,
  };
});
const titleDur = series.titleCard.duration;
const endDur = series.endCard.duration;
let gap = T.sentenceGap;
const nGaps = scenes.reduce((a, s) => a + Math.max(0, s.sentences.length - 1), 0);
const voiceRaw = scenes.reduce((a, s) => a + s.sentences.reduce((b, x) => b + x.duration, 0), 0);
const sceneDur = (s) => s.leadIn + s.sentences.reduce((b, x) => b + x.duration, 0) + gap * Math.max(0, s.sentences.length - 1) + s.pauses.slice(0, -1).reduce((a, b) => a + b, 0) + T.breathPause + s.hold;
const total = () => scenes.reduce((a, s) => a + sceneDur(s), 0) + endDur;

const before = total();
const targetMin = Math.max(T.targetMin, T.minTotal);
if (total() < targetMin) {
  // 1) lengthen breathing pauses between lines (up to 0.7s)
  let need = targetMin - total();
  const gapRoom = (0.7 - gap) * nGaps;
  if (gapRoom > 0) gap += Math.min(need, gapRoom) / nGaps;
  // 2) lengthen ambient holds / camera drifts, weighted by scene "stretch"
  need = targetMin - total();
  if (need > 0) {
    const w = scenes.reduce((a, s) => a + s.stretch, 0);
    for (const s of scenes) s.hold += (need * s.stretch) / w;
  }
} else if (total() > T.targetMax) {
  // tighten ambient holds first, then breathing gaps, then lead-ins
  let over = total() - T.targetMax;
  for (const s of scenes) {
    if (over <= 0) break;
    const room = s.hold - 0.35;
    if (room > 0) { const d = Math.min(room, over); s.hold -= d; over -= d; }
  }
  const gapRoom = (gap - 0.28) * nGaps;
  if (over > 0 && gapRoom > 0) { const d = Math.min(over, gapRoom); gap -= d / nGaps; over -= d; }
  for (const s of scenes) {
    if (over <= 0 || s.index === 0) continue;
    const room = s.leadIn - 0.45;
    if (room > 0) { const d = Math.min(room, over); s.leadIn -= d; over -= d; }
  }
}
const duration = r3(total());
if (duration < T.minTotal) {
  console.error(`[timeline] FAILED: duration ${duration}s is under the hard minimum ${T.minTotal}s`);
  process.exit(2);
}

// ------------------------------------------------------------------ absolute layout
let t = 0;
for (const s of scenes) {
  s.start = t;
  s.duration = sceneDur(s);
  s.end = t + s.duration;
  s.voiceStart = s.start + s.leadIn;
  let v = s.voiceStart;
  s.sentAbs = s.sentences.map((x, k) => {
    const o = { ...x, start: v, end: v + x.duration };
    v = o.end + gap + (s.pauses[k] || 0);
    return o;
  });
  s.voiceEnd = s.sentAbs.length ? s.sentAbs[s.sentAbs.length - 1].end : s.voiceStart;
  t = s.end;
}
const endCardStart = t;

function at(spec, s) {
  if (spec === undefined || spec === null) return s.start;
  if (typeof spec === 'number') return s.start + spec * s.duration;
  if ('t' in spec) return s.start + spec.t;
  if ('end' in spec) return s.voiceEnd + spec.end;
  if ('s' in spec) {
    const x = s.sentAbs[spec.s];
    if (!x) throw new Error(`scene ${s.src.id}: no sentence ${spec.s}`);
    return (spec.edge === 'end' ? x.end : x.start) + (spec.o || 0);
  }
  throw new Error(`bad time spec ${JSON.stringify(spec)}`);
}
const pal = (name, extra = {}) => {
  const p = series.palettes[name];
  if (!p) throw new Error(`unknown palette ${name}`);
  return { name, ...p, ...extra };
};

// ------------------------------------------------------------------ voice lines + captions
const words = [];
const captions = [];
const voiceLines = [];
for (const s of scenes) {
  if (!s.sentAbs.length) continue;
  const clips = s.sentAbs.map((x) => readWav(path.join(epDir, x.file)));
  const sr = clips[0].sr;
  const len = Math.round((s.voiceEnd - s.voiceStart) * sr) + 1;
  const pcm = new Int16Array(len);
  s.sentAbs.forEach((x, k) => pcm.set(clips[k].pcm.subarray(0, Math.max(0, len - Math.round((x.start - s.voiceStart) * sr))), Math.round((x.start - s.voiceStart) * sr)));
  const file = `audio/line_${String(s.index).padStart(2, '0')}_${s.src.id}.wav`;
  writeWav(path.join(epDir, file), sr, pcm);
  voiceLines.push({ scene: s.src.id, file, start: r3(s.voiceStart), duration: r3(s.voiceEnd - s.voiceStart), whisper: !!s.src.whisper });

  const sceneWords = [];
  s.sentAbs.forEach((x, si) => x.words.forEach((w, wi) => sceneWords.push({
    w: w.w, t0: r3(x.start + w.t0), t1: r3(x.start + w.t1), sentence: si, last: wi === x.words.length - 1,
  })));
  words.push(...sceneWords.map((w) => ({ ...w, scene: s.index })));
  // caption chunks: <= 7 words, break at sentence ends and after punctuation
  let cur = [];
  const flush = () => { if (cur.length) captions.push({ scene: s.index, words: cur }); cur = []; };
  sceneWords.forEach((w) => {
    cur.push(w);
    const punct = /[,;:…]$|\.\.\.$/.test(w.w);
    if (w.last || cur.length >= 7 || (punct && cur.length >= 3)) flush();
  });
  flush();
}
captions.forEach((c, i) => {
  const next = captions[i + 1];
  c.start = r3(c.words[0].t0 - 0.18);
  c.end = r3(Math.min(c.words[c.words.length - 1].t1 + 0.55, next ? next.words[0].t0 - 0.22 : 1e9));
  c.text = c.words.map((w) => w.w).join(' ');
});

// ------------------------------------------------------------------ camera / palette / events / actors
const cameraKeys = [];
const paletteKeys = [];
const events = [];
const actors = {};
const overlays = [];
let lastPalette = null;
for (const s of scenes) {
  const sc = s.src;
  const tin = sc.transitionIn || 'blend';
  const cutIn = tin === 'reset' || tin === 'fog' || tin === 'whip' || tin === 'dark';
  if (tin === 'whip') events.push({ t: r3(s.start), type: 'whip', scene: s.index, dir: sc.whipDir ?? 1 });
  if (tin === 'dark') events.push({ t: r3(s.start), type: 'dip', scene: s.index });
  if (tin === 'reset') events.push({ t: r3(s.start), type: 'reset', scene: s.index });
  if (tin === 'fog') events.push({ t: r3(s.start), type: 'fogPulse', scene: s.index });
  if (tin === 'fadeFromBlack') events.push({ t: r3(s.start), type: 'fadeIn', scene: s.index });

  sc.camera.forEach((k, j) => {
    cameraKeys.push({ t: r3(at(k.at, s)), pos: k.pos, look: k.look, fov: k.fov ?? 45, cut: !!k.cut || (j === 0 && cutIn), scene: s.index });
  });

  const p = pal(sc.palette);
  if (cutIn || !lastPalette) paletteKeys.push({ t: r3(s.start), palette: p, cut: true });
  else {
    paletteKeys.push({ t: r3(s.start - T.blend / 2), palette: lastPalette });
    paletteKeys.push({ t: r3(s.start + T.blend / 2), palette: p });
  }
  lastPalette = p;
  for (const k of sc.paletteKeys || []) {
    const { at: a, palette, cut, ...extra } = k;
    const pk = pal(palette, extra);
    if (!cut) paletteKeys.push({ t: r3(at(a, s) - 0.01), palette: lastPalette, hold: true });
    paletteKeys.push({ t: r3(at(a, s) + (cut ? 0 : 0.9)), palette: pk, cut: !!cut });
    lastPalette = pk;
  }

  for (const e of sc.events || []) {
    const { at: a, type, ...rest } = e;
    events.push({ t: r3(at(a, s)), type, scene: s.index, ...rest });
  }

  for (const [name, keys] of Object.entries(sc.actors || {})) {
    const A = (actors[name] ||= { spans: [], keys: [] });
    A.spans.push([r3(s.start - (cutIn ? 0 : T.blend / 2)), r3(s.end + T.blend / 2), s.index]);
    let prev = A.keys.length ? A.keys[A.keys.length - 1] : {};
    for (const k of keys) {
      const { at: a, ...rest } = k;
      const key = { pos: prev.pos, rot: prev.rot ?? 0, action: prev.action ?? 'idle', ...rest, t: r3(at(a, s)), scene: s.index };
      A.keys.push(key);
      prev = key;
    }
  }
  for (const o of sc.overlays || []) {
    overlays.push({ ...o, from: r3(at(o.from, s)), to: r3(at(o.to, s)), scene: s.index });
  }
  if (sc.shadowSweep) s.shadowSweepAbs = { from: r3(at(sc.shadowSweep.from, s)), to: r3(at(sc.shadowSweep.to, s)) };
}
// title card bell sting + end card
events.push({ t: 0.0, type: 'titleSting' });
events.push({ t: r3(endCardStart + 0.15), type: 'endSting' });
// sort + sanity
const byT = (a, b) => a.t - b.t;
cameraKeys.sort(byT);
for (let i = 1; i < cameraKeys.length; i++) {
  if (cameraKeys[i].t <= cameraKeys[i - 1].t) {
    console.warn(`[timeline] camera key order fix at ${cameraKeys[i].t}s (scene ${cameraKeys[i].scene})`);
    cameraKeys[i].t = r3(cameraKeys[i - 1].t + 0.02);
  }
}
paletteKeys.sort(byT);
events.sort(byT);
for (const A of Object.values(actors)) A.keys.sort(byT);

// voice regions for ducking (merge short gaps)
const regions = [];
for (const s of scenes) for (const x of s.sentAbs) {
  const last = regions[regions.length - 1];
  if (last && x.start - last[1] < 0.9) last[1] = x.end; else regions.push([x.start, x.end]);
}

const timeline = {
  generated: new Date().toISOString(),
  series: { title: series.seriesTitle, fonts: series.fonts },
  episode: script.episode,
  fps: script.episode.fps || 30,
  duration,
  voiceEngine: manifest.engine,
  timing: { blend: T.blend, breathPause: T.breathPause, sentenceGap: r3(gap), adjustedFrom: r3(before) },
  titleCard: { start: 0, duration: titleDur, title: script.episode.title, subtitle: script.episode.subtitle, kicker: script.episode.kicker ?? series.titleCard.kicker },
  endCard: { start: r3(endCardStart), duration: endDur, text: series.endCard.text.replace('{next}', script.episode.next), title: script.episode.title },
  scenes: scenes.map((s) => ({
    index: s.index,
    id: s.src.id,
    title: s.src.title,
    start: r3(s.start),
    duration: r3(s.duration),
    end: r3(s.end),
    leadIn: r3(s.leadIn),
    hold: r3(s.hold),
    transitionIn: s.src.transitionIn || 'blend',
    palette: pal(s.src.palette),
    sound: s.src.sound,
    set: s.src.set || {},
    whisper: !!s.src.whisper,
    narration: {
      text: s.sentAbs.map((x) => x.text).join(' '),
      start: r3(s.voiceStart),
      end: r3(s.voiceEnd),
      voiceDuration: r3(s.voiceEnd - s.voiceStart),
      sentences: s.sentAbs.map((x) => ({ text: x.text, start: r3(x.start), end: r3(x.end) })),
    },
    camera: cameraKeys.filter((k) => k.scene === s.index),
    shadowSweep: s.shadowSweepAbs || null,
  })),
  cameraKeys,
  paletteKeys,
  events,
  actors,
  overlays,
  captions,
  words,
  voiceLines,
  voiceRegions: regions.map(([a, b]) => [r3(a), r3(b)]),
};
fs.writeFileSync(path.join(epDir, 'timeline.json'), JSON.stringify(timeline, null, 1));
console.log(`[timeline] ${ep}: ${scenes.length} scenes, raw voice ${voiceRaw.toFixed(1)}s, total ${before.toFixed(1)}s -> ${duration}s ` +
  `(gap ${gap.toFixed(2)}s, engine ${manifest.engine})`);
for (const s of scenes) console.log(`  ${String(s.index).padStart(2)} ${s.src.id.padEnd(16)} ${s.start.toFixed(2).padStart(7)}s  +${s.duration.toFixed(2)}s`);
console.log(`     end card         ${endCardStart.toFixed(2).padStart(7)}s  +${endDur}s`);
