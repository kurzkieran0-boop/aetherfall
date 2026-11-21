#!/usr/bin/env node
// Scaffold the next part: copies the latest part's timeline.json structure into public/episodes/partN/
// with computed fields stripped. Title card, sonar sting and "PART X" end card come from the template
// automatically — a new part only needs its own timeline.json (scenes, narration, visuals, sound).
//   npm run new-part -- 2
import fs from 'node:fs';
import path from 'node:path';

const n = Number(process.argv[2]);
if (!n) { console.error('usage: npm run new-part -- <partNumber>'); process.exit(1); }
const root = 'public/episodes';
const prev = fs.readdirSync(root).filter((d) => /^part\d+$/.test(d)).sort((a, b) => Number(a.slice(4)) - Number(b.slice(4))).pop();
const src = JSON.parse(fs.readFileSync(path.join(root, prev, 'timeline.json'), 'utf8'));
const dir = path.join(root, `part${n}`);
if (fs.existsSync(path.join(dir, 'timeline.json'))) { console.error(`${dir}/timeline.json already exists`); process.exit(1); }
const strip = ['start', 'duration', 'voice'];
const out = {
  episode: { part: n, next: n + 1, subtitle: `PART ${n}` },
  _doc: src._doc,
  endCard: { text: `PART ${n + 1}: Follow so you don't miss it.` },
  scenes: src.scenes.map((s) => { const c = { ...s }; strip.forEach((k) => delete c[k]); c.narration = ['TODO: write narration.']; return c; }),
};
fs.mkdirSync(path.join(dir, 'audio'), { recursive: true });
fs.writeFileSync(path.join(dir, 'timeline.json'), JSON.stringify(out, null, 2) + '\n');
console.log(`created ${dir}/timeline.json from ${prev} — edit scenes/narration, then: npm run export -- part${n}`);
