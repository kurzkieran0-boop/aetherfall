// npm run shots [-- <part>] — QA: renders frames from every shot (mid + one
// per beat at 3 points) to out/qa/<part>/ and a contact sheet per beat.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { serve } from './serve.mjs';

const require = createRequire(import.meta.url);
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const args = process.argv.slice(2);
const part = args.find((a) => !a.startsWith('--')) || process.env.PART || process.env.npm_package_config_part || 'part1';
const only = args.includes('--only') ? args[args.indexOf('--only') + 1].split(',') : null;
const data = path.join(ROOT, 'build', part, 'data');
const tl = JSON.parse(fs.readFileSync(path.join(data, 'timeline.json'), 'utf8'));
const outDir = path.join(ROOT, 'out', 'qa', part);
fs.mkdirSync(outDir, { recursive: true });
const { srv, url } = await serve(path.join(ROOT, 'dist'), data);
const { chromium } = require('playwright');
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const p = await browser.newPage({ viewport: { width: 540, height: 960 } });
p.on('pageerror', (e) => console.error('PAGE ERROR', e.message));
await p.goto(url);
await p.waitForFunction(() => window.MC_READY, null, { timeout: 180000 });
const times = [];
for (const s of tl.shots) {
  if (only && !only.includes(s.id) && !only.includes(s.beat)) continue;
  const fr = args.includes('--three') ? [0.08, 0.5, 0.92] : [0.5];
  for (const k of fr) times.push({ t: s.start + s.dur * k, name: `${s.id}_${Math.round(k * 100)}` });
}
if (!only) times.unshift({ t: 0, name: 'first_frame' }, { t: tl.duration - 1 / tl.fps, name: 'last_frame' });
for (const { t, name } of times) {
  const b64 = await p.evaluate((t) => MC.jpeg(t, 0.9), t);
  fs.writeFileSync(path.join(outDir, `${name}.jpg`), Buffer.from(b64, 'base64'));
  process.stdout.write('.');
}
await browser.close();
srv.close();
// contact sheets per beat
for (const b of [...new Set(tl.shots.map((s) => s.beat))]) {
  const files = fs.readdirSync(outDir).filter((f) => f.startsWith(b === 'END' ? 'END' : b + '-') && f.endsWith('_50.jpg')).sort();
  if (files.length < 2) continue;
  const inputs = files.flatMap((f) => ['-i', path.join(outDir, f)]);
  const n = files.length;
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...inputs, '-filter_complex', files.map((_, i) => `[${i}:v]scale=360:640[v${i}]`).join(';') + ';' + files.map((_, i) => `[v${i}]`).join('') + `hstack=inputs=${n}[o]`, '-map', '[o]', path.join(outDir, `sheet_${b}.jpg`)]);
}
console.log(`\nwrote ${times.length} frames to ${outDir}`);
