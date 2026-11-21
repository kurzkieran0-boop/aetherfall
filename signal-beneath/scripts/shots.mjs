#!/usr/bin/env node
// QA: screenshot every scene (early / mid / late) + transitions, and verify every text element
// stays inside the safe area (nothing in the top 10% or bottom 20%). Writes out/shots/ + report.
//   node scripts/shots.mjs [ep] [--scale=0.5] [--t=12.5,40] [--audit-step=0.25]
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { startServer, launch, openStory } from './lib.mjs';

const args = process.argv.slice(2);
const ep = args.find((a) => !a.startsWith('--')) || 'part1';
const opt = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const [k, v] = a.slice(2).split('='); return [k, v ?? true]; }));
const scale = Number(opt.scale || 0.5), W = Math.round(1080 * scale), H = Math.round(1920 * scale);
const out = path.resolve('out/shots'); fs.mkdirSync(out, { recursive: true });
const { server, url } = await startServer();
const browser = await launch();
let bad = [];
try {
  const page = await openStory(browser, url, { ep, w: W, h: H });
  const info = await page.evaluate(() => window.__sb.info());
  const safe = info.safe;
  let times = [];
  if (opt.t) times = String(opt.t).split(',').map((x) => [Number(x), `t${x}`]);
  else info.segments.forEach((s, i) => { for (const f of [0.25, 0.6, 0.92]) times.push([s.start + s.duration * f, `${String(i).padStart(2, '0')}_${s.id}_${Math.round(f * 100)}`]); if (i) times.push([s.start + 0.05, `${String(i).padStart(2, '0')}_${s.id}_wipe`]); });
  for (const [t, label] of times) {
    await page.evaluate((t) => window.__sb.frame(t), t);
    await page.screenshot({ path: path.join(out, `${label}.jpg`), type: 'jpeg', quality: 85 });
    console.log(`shot ${label} @ ${t.toFixed(2)}s`);
  }
  // safe-area audit across the whole timeline
  const step = Number(opt['audit-step'] || 0.25); let checked = 0;
  for (let t = 0; t < info.duration; t += step) {
    const texts = await page.evaluate((t) => window.__sb.texts(t), t);
    for (const b of texts) { checked++; if (b.y0 < safe.top - 0.5 || b.y1 > safe.bottom + 0.5 || b.x0 < 0 || b.x1 > 1080) bad.push({ t: +t.toFixed(2), ...b }); }
  }
  const uniq = [...new Map(bad.map((b) => [b.str, b])).values()];
  fs.writeFileSync(path.join(out, 'safe-area.json'), JSON.stringify({ safe, checked, violations: uniq }, null, 2));
  console.log(`[shots] safe-area audit: ${checked} text boxes checked, ${uniq.length} distinct violations`);
  uniq.slice(0, 20).forEach((b) => console.log('  VIOLATION', b));
  try { execFileSync('python3', ['scripts/contact.py', out], { stdio: 'inherit' }); } catch { /* optional */ }
} finally { await browser.close(); await server.close(); }
if (bad.length) process.exitCode = 1;
