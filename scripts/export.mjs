#!/usr/bin/env node
// Deterministic export: Playwright drives window.__vtr.frame(t) frame by frame, JPEG
// screenshots are piped into ffmpeg, muxed with the offline-rendered score + voice mix.
// Produces out/<ep>_9x16.mp4 (1080x1920) and out/<ep>_16x9.mp4 (1920x1080) and FAILS
// (exit 1) if any MP4 is shorter than the series minimum (120 s).
//   node scripts/export.mjs [ep] [--only=9x16|16x9] [--seconds=N (preview cut, skips check)] [--quality=92] [--rs=0.75]
import fs from 'node:fs';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { startServer, launch, openStory } from './lib.mjs';

const args = process.argv.slice(2);
const ep = args.find((a) => !a.startsWith('--')) || 'part1';
const opt = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const [k, v] = a.slice(2).split('='); return [k, v ?? true]; }));
const series = JSON.parse(fs.readFileSync('public/series.json', 'utf8'));
const MIN = series.timing.minTotal;
const OUT = path.resolve('out');
fs.mkdirSync(OUT, { recursive: true });
const FORMATS = [
  { name: '9x16', w: 1080, h: 1920 },
  { name: '16x9', w: 1920, h: 1080 },
].filter((f) => !opt.only || opt.only === f.name);

// prepare: voiceover (cached) + timeline, unless --skip-prepare
if (!opt['skip-prepare']) {
  execFileSync('python3', ['scripts/tts.py', ep], { stdio: 'inherit' });
  execFileSync('node', ['scripts/build-timeline.mjs', ep], { stdio: 'inherit' });
}

const probe = (file) => Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file]).toString().trim());
const fmt = (s) => `${Math.floor(s / 60)}m${String(Math.round(s % 60)).padStart(2, '0')}s`;

const { server, url } = await startServer();
let failed = false;
try {
  // ---------------------------------------------------------------- audio (offline render, once)
  const wavPath = path.join(OUT, `${ep}_mix.wav`);
  {
    const browser = await launch();
    const page = await openStory(browser, url, { ep, w: 320, h: 180 });
    const info = await page.evaluate(() => window.__vtr.info());
    console.log(`[export] ${ep}: timeline ${info.duration}s @ ${info.fps}fps — rendering score + voice offline...`);
    const n = await page.evaluate(() => window.__vtr.renderAudio());
    const chunks = [];
    for (let off = 0; off < n; off += 4 << 20) chunks.push(Buffer.from(await page.evaluate(([o, l]) => window.__vtr.audioChunk(o, l), [off, 4 << 20]), 'base64'));
    fs.writeFileSync(wavPath, Buffer.concat(chunks));
    console.log(`[export] audio mix -> ${path.relative('.', wavPath)} (${probe(wavPath).toFixed(2)}s)`);
    await browser.close();
  }

  // ---------------------------------------------------------------- video, one browser per format (in parallel)
  const renderFormat = async (F) => {
    const browser = await launch();
    const page = await openStory(browser, url, { ep, w: F.w, h: F.h, extra: opt.rs ? `&rs=${opt.rs}` : '' });
    const info = await page.evaluate(() => window.__vtr.info());
    const fps = info.fps;
    const dur = opt.seconds ? Math.min(info.duration, Number(opt.seconds)) : info.duration;
    const N = Math.round(dur * fps);
    const file = path.join(OUT, `${ep}_${F.name}${opt.seconds ? '_preview' : ''}.mp4`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
      '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-i', wavPath, '-map', '0:v', '-map', '1:a',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(fps),
      '-c:a', 'aac', '-b:a', '192k', '-t', dur.toFixed(3), '-movflags', '+faststart', file], { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));
    const t0 = Date.now();
    for (let i = 0; i < N; i++) {
      await page.evaluate((t) => window.__vtr.frame(t), i / fps);
      const jpg = await page.screenshot({ type: 'jpeg', quality: Number(opt.quality || 92) });
      if (!ff.stdin.write(jpg)) await new Promise((r) => ff.stdin.once('drain', r));
      if (i % 150 === 0 || i === N - 1) {
        const el = (Date.now() - t0) / 1000;
        console.log(`[export ${F.name}] frame ${i + 1}/${N}  ${(((i + 1) / N) * 100).toFixed(1)}%  elapsed ${fmt(el)}  eta ${fmt((el / (i + 1)) * (N - i - 1))}`);
      }
    }
    ff.stdin.end();
    await done;
    await browser.close();
    const d = probe(file);
    const ok = opt.seconds ? true : d >= MIN;
    console.log(`[export ${F.name}] ${path.relative('.', file)}  ${F.w}x${F.h}  duration ${d.toFixed(2)}s  ${ok ? 'OK' : `FAIL (< ${MIN}s)`}`);
    if (!ok) failed = true;
    return { format: F.name, file: path.relative('.', file), width: F.w, height: F.h, duration: d };
  };
  const results = await Promise.all(FORMATS.map(renderFormat));
  fs.writeFileSync(path.join(OUT, `${ep}_export.json`), JSON.stringify({ ep, minSeconds: MIN, results, ok: !failed }, null, 2));
} finally {
  await server.close();
}
if (failed) {
  console.error(`[export] FAILED: final MP4 shorter than ${MIN}s`);
  process.exit(1);
}
console.log('[export] done.');
