#!/usr/bin/env node
// Cut the 1080p masters into seamless, individually playable fMP4 chunks (< 15 MB each) for the
// streaming watch page: out/stream/<ep>_<fmt>/chunk_NNN.mp4 + manifest.json
//   node scripts/share.mjs part1 [--crf=24]
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
const args = process.argv.slice(2);
const ep = args.find((a) => !a.startsWith('--')) || 'part1';
const crf = (args.find((a) => a.startsWith('--crf=')) || '--crf=27').split('=')[1];
const out = [];
for (const fmt of ['9x16', '16x9']) {
  const src = path.join('out', `${ep}_${fmt}.mp4`);
  if (!fs.existsSync(src)) { console.error(`missing ${src}`); process.exit(1); }
  const dir = path.join('out', 'stream', `${ep}_${fmt}`);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', src,
    '-vf', 'hqdn3d=1.2:1.2:3:3', '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-maxrate', '6M', '-bufsize', '12M',
    '-profile:v', 'high', '-level', '4.0', '-pix_fmt', 'yuv420p', '-g', '60', '-keyint_min', '60', '-sc_threshold', '0',
    '-c:a', 'aac', '-b:a', '160k', '-ac', '2',
    '-f', 'hls', '-hls_time', '6', '-hls_playlist_type', 'vod', '-hls_segment_type', 'fmp4',
    '-hls_fmp4_init_filename', 'init.mp4', '-hls_segment_filename', path.join(dir, 'seg_%03d.m4s'), path.join(dir, 'index.m3u8')], { stdio: 'inherit' });
  const m3u8 = fs.readFileSync(path.join(dir, 'index.m3u8'), 'utf8').split('\n');
  const init = fs.readFileSync(path.join(dir, 'init.mp4'));
  const chunks = [];
  let start = 0;
  for (let i = 0; i < m3u8.length; i++) {
    const m = m3u8[i].match(/^#EXTINF:([\d.]+)/);
    if (!m) continue;
    const seg = m3u8[i + 1].trim();
    const file = `chunk_${String(chunks.length).padStart(3, '0')}.mp4`;
    fs.writeFileSync(path.join(dir, file), Buffer.concat([init, fs.readFileSync(path.join(dir, seg))]));
    fs.rmSync(path.join(dir, seg));
    const dur = Number(m[1]);
    chunks.push({ file, start: Math.round(start * 1000) / 1000, duration: dur, bytes: fs.statSync(path.join(dir, file)).size });
    start += dur;
  }
  fs.rmSync(path.join(dir, 'index.m3u8')); fs.rmSync(path.join(dir, 'init.mp4'));
  const big = Math.max(...chunks.map((c) => c.bytes));
  const total = chunks.reduce((a, c) => a + c.bytes, 0);
  const man = { ep, format: fmt, codecs: 'avc1.640028,mp4a.40.2', duration: Math.round(start * 1000) / 1000, chunks };
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(man, null, 1));
  console.log(`${ep} ${fmt}: ${chunks.length} chunks, ${(total / 1e6).toFixed(1)} MB total, largest ${(big / 1e6).toFixed(1)} MB, ${start.toFixed(2)}s`);
  if (big > 15e6) { console.error('a chunk is over 15 MB; re-run with a higher --crf'); process.exit(1); }
  out.push(man);
}
