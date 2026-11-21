#!/usr/bin/env node
// Scaffold the next episode: node scripts/new-part.mjs part2
// Copies the set/palette conventions and the title/end card wiring; you only write scenes.
import fs from 'node:fs';
import path from 'node:path';
const ep = process.argv[2];
if (!ep) { console.error('usage: npm run new-part -- part2'); process.exit(1); }
const n = Number((ep.match(/\d+/) || [2])[0]);
const dir = path.join('public', 'episodes', ep);
if (fs.existsSync(path.join(dir, 'script.json'))) { console.error(`${dir}/script.json already exists`); process.exit(1); }
fs.mkdirSync(dir, { recursive: true });
const prev = JSON.parse(fs.readFileSync('public/episodes/part1/script.json', 'utf8'));
const script = {
  episode: { ...prev.episode, part: n, next: n + 1, subtitle: `PART ${n}` },
  voice: prev.voice,
  _timeSpec: prev._timeSpec,
  scenes: [
    {
      id: 'cold_open', title: 'COLD OPEN', palette: 'dawn', leadIn: 4.6, hold: 1.2, transitionIn: 'fadeFromBlack', titleCard: true,
      narration: ['Write the first line of the next part here.'],
      sound: { mood: 'dawn-hush', drone: 0.55, pad: 0.25, box: 0.35, tick: 0.1, chord: 'Dm' },
      camera: [
        { at: 0, pos: [0.5, 17.2, -16.4], look: [0, 18.0, -24], fov: 34 },
        { at: 1, pos: [-2.2, 1.9, -2.1], look: [-5.6, 0.9, -5.0], fov: 42 },
      ],
      actors: { bell: [{ at: 0, action: 'swing', amp: 0.55 }] },
      events: [{ at: { t: 0.25 }, type: 'bell' }],
      set: { chalk: true },
    },
  ],
};
fs.writeFileSync(path.join(dir, 'script.json'), JSON.stringify(script, null, 2));
console.log(`created ${dir}/script.json — add scenes, then: npm run export -- ${ep}`);
