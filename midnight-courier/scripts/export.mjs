// npm run export [-- <part>] [--workers N] [--skip-voice] [--from s --to s]
// voice (Kokoro) -> fit -> vite build -> parallel deterministic Playwright
// frame capture piped into ffmpeg -> score render (OfflineAudioContext) ->
// voice track assembly -> mux H.264/AAC 1080x1920 30fps -> size + duration
// checks (fails outside the part's min/max duration).
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { fit } from './fit.mjs';
import { serve } from './serve.mjs';

const require = createRequire(import.meta.url);
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const args = process.argv.slice(2);
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const part = args.find((a) => !a.startsWith('--') && !/^\d/.test(a)) || process.env.PART || process.env.npm_package_config_part || 'part1';
const WORKERS = +flag('--workers', Math.max(1, Math.min(4, os.cpus().length)));
const MAX_MB = 50;

const log = (...m) => console.log(`[export ${new Date().toISOString().slice(11, 19)}]`, ...m);
function run(cmd, a, opt = {}) {
  const r = spawnSync(cmd, a, { stdio: 'inherit', cwd: ROOT, ...opt });
  if (r.status !== 0) throw new Error(`${cmd} ${a.join(' ')} failed (${r.status})`);
}
function ensureFfmpeg() {
  try { execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' }); return; } catch {}
  log('ffmpeg missing — installing');
  try { run('bash', ['-lc', 'apt-get update -qq && apt-get install -y -qq ffmpeg']); } catch {
    run('bash', ['-lc', 'pip install -q imageio-ffmpeg && ln -sf $(python3 -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())") /usr/local/bin/ffmpeg']);
  }
}
function probeDuration(f) {
  return +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', f]).toString().trim();
}

// --------------------------------------------------------------- WAV helpers
function readWav(file) {
  const b = fs.readFileSync(file);
  let o = 12, fmt = null, data = null;
  while (o < b.length) {
    const id = b.toString('ascii', o, o + 4), sz = b.readUInt32LE(o + 4);
    if (id === 'fmt ') fmt = { ch: b.readUInt16LE(o + 10), sr: b.readUInt32LE(o + 12), bits: b.readUInt16LE(o + 22) };
    if (id === 'data') data = b.subarray(o + 8, o + 8 + sz);
    o += 8 + sz + (sz % 2);
  }
  const n = data.length / 2 / fmt.ch;
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = data.readInt16LE(i * 2 * fmt.ch) / 32768;
  return { sr: fmt.sr, samples: out };
}
function writeWav(file, samples, sr) {
  const b = Buffer.alloc(44 + samples.length * 2);
  b.write('RIFF', 0); b.writeUInt32LE(36 + samples.length * 2, 4); b.write('WAVE', 8); b.write('fmt ', 12);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22); b.writeUInt32LE(sr, 24); b.writeUInt32LE(sr * 2, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34);
  b.write('data', 36); b.writeUInt32LE(samples.length * 2, 40);
  for (let i = 0; i < samples.length; i++) b.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(samples[i] * 32767))), 44 + i * 2);
  fs.writeFileSync(file, b);
}

async function main() {
  const t0 = Date.now();
  ensureFfmpeg();
  const build = path.join(ROOT, 'build', part);
  const data = path.join(build, 'data');
  const voiceDir = path.join(data, 'voice');
  if (!args.includes('--skip-voice') || !fs.existsSync(path.join(voiceDir, 'manifest.json'))) {
    log('voice: synthesizing narration (Kokoro, fallbacks Piper / edge-tts)');
    run('python3', [path.join(ROOT, 'scripts', 'tts.py'), path.join(ROOT, 'series', part, 'timeline.json'), voiceDir]);
  }
  const { out: tl, problems } = fit(part);
  if (problems.length) throw new Error('fit failed:\n  ' + problems.join('\n  '));
  log(`fit: ${tl.duration.toFixed(2)}s, ${tl.shots.length} shots, ${tl.frames} frames`);
  log('vite build');
  run('npx', ['vite', 'build', '--logLevel', 'warn']);

  const { srv, url } = await serve(path.join(ROOT, 'dist'), data);
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-timer-throttling'] });
  const tmp = path.join(build, 'tmp');
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(tmp, { recursive: true });
  const openPage = async () => {
    const p = await browser.newPage({ viewport: { width: 540, height: 960 } });
    p.on('pageerror', (e) => console.error('PAGE ERROR', e.message));
    await p.goto(url);
    await p.waitForFunction(() => window.MC_READY, null, { timeout: 180000 });
    return p;
  };

  // ---- score + sfx (deterministic OfflineAudioContext)
  log('audio: rendering procedural score');
  const ap = await openPage();
  const scoreB64 = await ap.evaluate(() => MC.audio());
  fs.writeFileSync(path.join(tmp, 'score.wav'), Buffer.from(scoreB64, 'base64'));
  await ap.close();

  // ---- voice track
  const SR = 24000;
  const voice = new Float32Array(Math.ceil((tl.duration + 1) * SR));
  for (const l of tl.lines) {
    const w = readWav(path.join(voiceDir, l.file));
    const off = Math.round(l.start * SR);
    for (let i = 0; i < w.samples.length && off + i < voice.length; i++) voice[off + i] += w.samples[i] * (l.gain ?? 1);
  }
  writeWav(path.join(tmp, 'voice.wav'), voice, SR);

  // ---- frames (parallel, each worker encodes its own segment)
  const from = +flag('--from', 0), to = +flag('--to', tl.duration);
  const f0 = Math.round(from * tl.fps), f1 = Math.min(tl.frames, Math.round(to * tl.fps));
  const per = Math.ceil((f1 - f0) / WORKERS);
  log(`frames: ${f1 - f0} with ${WORKERS} workers`);
  let done = 0;
  const tick = setInterval(() => log(`  ${done}/${f1 - f0} frames (${((done / (f1 - f0)) * 100).toFixed(0)}%)`), 20000);
  const segs = [];
  await Promise.all(Array.from({ length: WORKERS }, async (_, w) => {
    const a = f0 + w * per, b = Math.min(f1, a + per);
    if (a >= b) return;
    const seg = path.join(tmp, `seg_${String(w).padStart(2, '0')}.mp4`);
    segs[w] = seg;
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(tl.fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', String(tl.fps), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
    const closed = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg segment failed ' + c)))));
    const p = await openPage();
    await p.evaluate(([x, y]) => MC.warm(x, y), [a / tl.fps, b / tl.fps]);
    for (let f = a; f < b; f++) {
      const b64 = await p.evaluate((t) => MC.jpeg(t, 0.94), f / tl.fps);
      const buf = Buffer.from(b64, 'base64');
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      done++;
    }
    ff.stdin.end();
    await closed;
    await p.close();
  }));
  clearInterval(tick);
  await browser.close();
  srv.close();

  const list = path.join(tmp, 'segs.txt');
  fs.writeFileSync(list, segs.filter(Boolean).map((s) => `file '${s}'`).join('\n'));
  const video = path.join(tmp, 'video.mp4');
  run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', video]);

  // ---- mux: voice + score (score already ducked 8 dB under the voice)
  const outDir = path.join(ROOT, 'out');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, tl.output || `${part}.mp4`);
  const mux = (crf, preset) => run('ffmpeg', ['-y', '-loglevel', 'error', '-i', video, '-i', path.join(tmp, 'voice.wav'), '-i', path.join(tmp, 'score.wav'),
    '-filter_complex', '[1:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.0[v];[2:a]volume=0.9[m];[v][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]',
    '-map', '0:v', '-map', '[a]',
    ...(crf ? ['-c:v', 'libx264', '-crf', String(crf), '-preset', preset, '-pix_fmt', 'yuv420p'] : ['-c:v', 'copy']),
    '-c:a', 'aac', '-b:a', '192k', '-t', tl.duration.toFixed(3), '-movflags', '+faststart', outFile]);
  mux(null);
  let mb = fs.statSync(outFile).size / 1048576;
  if (mb > MAX_MB) { log(`size ${mb.toFixed(1)} MB > ${MAX_MB} MB, re-encoding -crf 24 -preset veryfast`); mux(24, 'veryfast'); mb = fs.statSync(outFile).size / 1048576; }

  const dur = probeDuration(outFile);
  const minD = 120, maxD = 170;
  const info = execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,codec_name', '-of', 'csv=p=0', outFile]).toString().trim();
  log(`done in ${((Date.now() - t0) / 1000).toFixed(0)}s -> ${outFile}`);
  log(`duration ${dur.toFixed(2)}s · ${tl.shots.length} shots · video ${info} · ${mb.toFixed(1)} MB`);
  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify({ file: outFile, duration: dur, shots: tl.shots.length, video: info, sizeMB: +mb.toFixed(2) }, null, 1));
  if (dur < minD || dur > maxD) { console.error(`EXPORT FAILED: duration ${dur.toFixed(2)}s outside ${minD}-${maxD}s`); process.exit(1); }
}

main().catch((e) => { console.error(e); process.exit(1); });
