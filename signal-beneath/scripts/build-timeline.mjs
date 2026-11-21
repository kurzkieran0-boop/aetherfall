#!/usr/bin/env node
// Measures the voiceover (voice_manifest.json from tts.py) and writes start/duration/voice
// back into public/episodes/<ep>/timeline.json.
//   scene duration = leadIn + voice line + breathingPause (+ tailHold) (+ auto hold)
// If the whole video (title card + scenes + end card) is under series.timing.targetMin, the
// shortfall is spread over the scenes as longer holds / sonar sweeps / breathing pauses.
// Exits non-zero if the total falls outside [minTotal, maxTotal].
import fs from 'node:fs';
import path from 'node:path';

const ep = process.argv[2] || 'part1';
const dir = path.resolve('public/episodes', ep);
const series = JSON.parse(fs.readFileSync('public/series.json', 'utf8'));
const file = path.join(dir, 'timeline.json');
const tl = JSON.parse(fs.readFileSync(file, 'utf8'));
const man = JSON.parse(fs.readFileSync(path.join(dir, 'audio/voice_manifest.json'), 'utf8'));
const T = series.timing;
const r3 = (x) => Math.round(x * 1000) / 1000;

const scenes = tl.scenes.map((s) => {
  const line = man.lines.find((l) => l.id === s.id);
  if (!line) throw new Error(`no voice line for scene ${s.id} — run npm run voice`);
  const lead = s.leadIn ?? T.leadIn;
  const natural = lead + line.duration + T.breathingPause + (s.tailHold || 0);
  return { s, line, lead, natural, base: Math.max(natural, s.minDuration || 0) };
});
const tc = series.template.titleCard, ec = series.template.endCard;
const fixed = tc.duration + ec.duration;
let total = fixed + scenes.reduce((a, x) => a + x.base, 0);
const extra = Math.max(0, T.targetMin - total);
// spread the shortfall: weight by scene length so long scenes get longer sweeps
const wsum = scenes.reduce((a, x) => a + (x.s.holdWeight ?? 1) * x.base, 0);
let t = 0;
const out = [];
for (const [i, x] of scenes.entries()) {
  const add = extra * ((x.s.holdWeight ?? 1) * x.base) / wsum;
  const leadAdd = add * 0.3, tailAdd = add * 0.7; // longer settle-in + longer breathing pause / sweep hold
  const dur = x.base + add;
  const lead = x.lead + leadAdd;
  if (i === (tc.after ?? 0) + 1) t += tc.duration; // title card sits after the cold open
  x.s.start = r3(t);
  x.s.duration = r3(dur);
  x.s.voice = {
    file: x.line.file,
    offset: r3(lead),
    duration: x.line.duration,
    breathingPause: r3(T.breathingPause + tailAdd + Math.max(0, x.base - x.natural)),
    sentences: x.line.sentences.map((q) => ({ ...q, start: r3(q.start + lead), words: q.words.map((w) => ({ w: w.w, t0: r3(w.t0 + lead), t1: r3(w.t1 + lead) })) })),
  };
  t += dur;
  out.push(`${String(i).padStart(2)} ${x.s.id.padEnd(14)} voice ${x.line.duration.toFixed(2)}s  natural ${x.natural.toFixed(2)}s  -> ${dur.toFixed(2)}s${add ? `  (+${add.toFixed(2)}s hold)` : ''}`);
}
const titleStart = scenes[(tc.after ?? 0)].s.start + scenes[(tc.after ?? 0)].s.duration;
tl.titleCard = { start: r3(titleStart), duration: tc.duration };
tl.endCard = { ...tl.endCard, start: r3(t), duration: ec.duration };
total = r3(t + ec.duration);
tl.total = total;
tl.fps = series.format.fps;
tl.engine = man.engine;
tl.voiceName = man.voice;
fs.writeFileSync(file, JSON.stringify(tl, null, 2) + '\n');
console.log(out.join('\n'));
console.log(`[timeline] ${ep}: total ${total.toFixed(2)}s (title ${tc.duration}s + end ${ec.duration}s; auto-lengthened by ${extra.toFixed(2)}s) -> ${path.relative('.', file)}`);
if (total < T.minTotal || total > T.maxTotal) {
  console.error(`[timeline] FAIL: total ${total}s outside [${T.minTotal}, ${T.maxTotal}]`);
  process.exit(1);
}
