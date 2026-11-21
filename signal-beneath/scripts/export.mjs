#!/usr/bin/env node
// npm run export [ep] [--workers=3] [--seconds=N preview] [--skip-prepare]
// 1. voiceover (Kokoro, cached) + timeline (durations from voice, auto-lengthened to >=120 s)
// 2. score + voice rendered offline in the page (Web Audio) -> out/<ep>_mix.wav
// 3. deterministic frame capture with Playwright (parallel workers, frame ranges) -> H.264 segments
// 4. concat + mux AAC -> out/signal-partN.mp4 (1080x1920, 30 fps); re-encode crf 24 veryfast if > 50 MB
// 5. FAIL (exit 1) if duration < 120 s or > 170 s, or resolution is not 1080x1920
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, execFileSync } from 'node:child_process';
import { startServer, launch, openStory } from './lib.mjs';

const args = process.argv.slice(2);
const ep = args.find((a) => !a.startsWith('--')) || 'part1';
const opt = Object.fromEntries(args.filter((a) => a.startsWith('--')).map((a) => { const [k, v] = a.slice(2).split('='); return [k, v ?? true]; }));
const series = JSON.parse(fs.readFileSync('public/series.json', 'utf8'));
const { width: W, height: H, fps: FPS } = series.format;
const { minTotal: MIN, maxTotal: MAX } = series.timing;
const MAX_MB = 50;
const OUT = path.resolve('out'); const SEG = path.join(OUT, `${ep}_segments`);
fs.mkdirSync(SEG, { recursive: true });

function need(bin) { try { execFileSync(bin, ['-version'], { stdio: 'ignore' }); } catch { console.log(`[export] ${bin} missing — installing`); execFileSync('bash', ['-c', 'apt-get update -qq && apt-get install -y -qq ffmpeg'], { stdio: 'inherit' }); } }
need('ffmpeg'); need('ffprobe');
if (!opt['skip-prepare']) {
  execFileSync('python3', ['scripts/tts.py', ep], { stdio: 'inherit' });
  execFileSync('node', ['scripts/build-timeline.mjs', ep], { stdio: 'inherit' }); // exits 1 if outside [120,170]
}
const probe = (f) => JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration,size:stream=width,height,codec_name,r_frame_rate', '-of', 'json', f]).toString());
const mmss = (s) => `${Math.floor(s / 60)}m${String(Math.round(s % 60)).padStart(2, '0')}s`;
const partNo = JSON.parse(fs.readFileSync(`public/episodes/${ep}/timeline.json`, 'utf8')).episode.part;
const final = path.join(OUT, `signal-part${partNo}.mp4`);

const { server, url } = await startServer();
let info;
try {
  // ---------------------------------------------------------------- audio
  const wav = path.join(OUT, `${ep}_mix.wav`);
  {
    const browser = await launch();
    const page = await openStory(browser, url, { ep, w: 270, h: 480 });
    info = await page.evaluate(() => window.__sb.info());
    console.log(`[export] ${ep}: timeline ${info.duration}s @ ${info.fps} fps — rendering score + voice offline…`);
    const n = await page.evaluate(() => window.__sb.renderAudio());
    const chunks = [];
    for (let o = 0; o < n; o += 4 << 20) chunks.push(Buffer.from(await page.evaluate(([a, b]) => window.__sb.audioChunk(a, b), [o, 4 << 20]), 'base64'));
    fs.writeFileSync(wav, Buffer.concat(chunks));
    const am = await page.evaluate(() => window.__sb.audioMeta());
    fs.writeFileSync(path.join(OUT, `${ep}_audio.json`), JSON.stringify(am, null, 1));
    await browser.close();
    // verify: true silence before the final line, no clipping
    const chk = JSON.parse(execFileSync('python3', ['-c', `
import sys, json, soundfile as sf, numpy as np
x, sr = sf.read(sys.argv[1]); w = json.loads(sys.argv[2])
out = {"peak": float(np.abs(x).max()), "silence": []}
for s in w:
    seg = x[int((s["a"] + 0.03) * sr):int((s["b"] - 0.03) * sr)]
    out["silence"].append(float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)))
print(json.dumps(out))`, wav, JSON.stringify(am.silence)]).toString());
    console.log(`[export] audio peak ${(20 * Math.log10(chk.peak)).toFixed(1)} dBFS; silence window RMS ${chk.silence.map((x) => x.toFixed(1) + ' dB').join(', ')}`);
    if (chk.silence.some((x) => x > -60)) { console.error('[export] FAIL: silence window is not silent'); process.exit(1); }
    console.log(`[export] audio -> ${path.relative('.', wav)}`);
  }

  // ---------------------------------------------------------------- video (parallel frame ranges)
  const dur = opt.seconds ? Math.min(info.duration, Number(opt.seconds)) : info.duration;
  const N = Math.round(dur * FPS);
  const K = Math.max(1, Number(opt.workers || Math.min(3, Math.max(1, os.cpus().length - 1))));
  const t0 = Date.now(); let done = 0;
  const worker = async (k) => {
    const a = Math.floor((N * k) / K), b = Math.floor((N * (k + 1)) / K);
    const file = path.join(SEG, `seg_${k}.mp4`);
    const browser = await launch();
    const page = await openStory(browser, url, { ep, w: W, h: H });
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-g', '60', '-bf', '2', file], { stdio: ['pipe', 'inherit', 'inherit'] });
    const closed = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg ${c}`)))));
    for (let i = a; i < b; i++) {
      await page.evaluate((t) => window.__sb.frame(t), i / FPS);
      const jpg = await page.screenshot({ type: 'jpeg', quality: 93 });
      if (!ff.stdin.write(jpg)) await new Promise((r) => ff.stdin.once('drain', r));
      done++;
      if (done % 300 === 0) { const el = (Date.now() - t0) / 1000; console.log(`[export] ${done}/${N} frames  ${((done / N) * 100).toFixed(1)}%  elapsed ${mmss(el)}  eta ${mmss((el / done) * (N - done))}`); }
    }
    ff.stdin.end(); await closed; await browser.close();
    return file;
  };
  const files = await Promise.all(Array.from({ length: K }, (_, k) => worker(k)));
  const list = path.join(SEG, 'list.txt');
  fs.writeFileSync(list, files.map((f) => `file '${f}'`).join('\n'));
  const mux = (out, extra) => execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-i', wav, '-map', '0:v', '-map', '1:a', ...extra,
    '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-t', dur.toFixed(3), '-movflags', '+faststart', out], { stdio: 'inherit' });
  mux(final, ['-c:v', 'copy']);
  let mb = fs.statSync(final).size / 1e6;
  if (mb > MAX_MB) {
    console.log(`[export] ${mb.toFixed(1)} MB > ${MAX_MB} MB — re-encoding with -crf 24 -preset veryfast`);
    const tmp = final.replace('.mp4', '.tmp.mp4');
    mux(tmp, ['-c:v', 'libx264', '-crf', '24', '-preset', 'veryfast', '-pix_fmt', 'yuv420p']);
    fs.renameSync(tmp, final); mb = fs.statSync(final).size / 1e6;
  }
} finally { await server.close(); }

const p = probe(final), v = p.streams.find((s) => s.width), d = Number(p.format.duration), mb = Number(p.format.size) / 1e6;
const errs = [];
if (!opt.seconds && d < MIN) errs.push(`duration ${d.toFixed(2)}s < ${MIN}s`);
if (!opt.seconds && d > MAX) errs.push(`duration ${d.toFixed(2)}s > ${MAX}s`);
if (v.width !== W || v.height !== H) errs.push(`resolution ${v.width}x${v.height} != ${W}x${H}`);
if (mb > MAX_MB) errs.push(`size ${mb.toFixed(1)} MB > ${MAX_MB} MB`);
const report = { ep, file: path.relative('.', final), duration: +d.toFixed(3), width: v.width, height: v.height, fps: v.r_frame_rate, sizeMB: +mb.toFixed(2), ok: !errs.length, errors: errs };
fs.writeFileSync(path.join(OUT, `${ep}_export.json`), JSON.stringify(report, null, 2));
console.log(`[export] ${report.file}  ${v.width}x${v.height}  ${v.r_frame_rate} fps  ${d.toFixed(2)}s  ${mb.toFixed(1)} MB  ${errs.length ? 'FAIL: ' + errs.join('; ') : 'OK'}`);
if (errs.length) process.exit(1);
