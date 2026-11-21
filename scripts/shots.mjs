#!/usr/bin/env node
// QA: screenshot every scene (start/mid/late) in both aspect ratios -> out/shots/
// usage: node scripts/shots.mjs [ep] [--only=portrait|landscape] [--t=12.5,40] [--scale=0.5]
import fs from 'node:fs';
import path from 'node:path';
import { startServer, launch, openStory } from './lib.mjs';

const args = process.argv.slice(2);
const ep = args.find((a) => !a.startsWith('--')) || 'part1';
const opt = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')));
const scale = +(opt.scale || 0.5);
const formats = [['portrait', 1080, 1920], ['landscape', 1920, 1080]].filter(([n]) => !opt.only || opt.only === n);
const out = path.resolve('out/shots');
fs.mkdirSync(out, { recursive: true });

const { server, url } = await startServer();
const browser = await launch();
try {
  for (const [name, W, H] of formats) {
    const w = Math.round(W * scale), h = Math.round(H * scale);
    const page = await openStory(browser, url, { ep, w, h });
    const info = await page.evaluate(() => window.__vtr.info());
    let times;
    if (opt.t) times = opt.t.split(',').map((x) => [Number(x), `t${x}`]);
    else {
      times = [];
      for (const s of info.scenes) for (const f of [0.2, 0.55, 0.88]) times.push([s.start + s.duration * f, `${String(info.scenes.indexOf(s)).padStart(2, '0')}_${s.id}_${Math.round(f * 100)}`]);
      times.push([info.endCard.start + 3.5, '11_endcard']);
    }
    for (const [t, label] of times) {
      const t0 = Date.now();
      await page.evaluate((t) => window.__vtr.frame(t), t);
      const file = path.join(out, `${name}_${label}.jpg`);
      await page.screenshot({ path: file, type: 'jpeg', quality: 85 });
      console.log(`${name} ${label} @${t.toFixed(2)}s  (${Date.now() - t0}ms)`);
    }
    await page.close();
  }
} finally {
  await browser.close();
  await server.close();
}
