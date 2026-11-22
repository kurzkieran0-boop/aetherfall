// npm run voice [-- <part>] — Kokoro TTS (fallback Piper, edge-tts), one WAV per line.
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const part = process.argv[2] || process.env.PART || process.env.npm_package_config_part || 'part1';
const r = spawnSync('python3', [path.join(ROOT, 'scripts', 'tts.py'), path.join(ROOT, 'series', part, 'timeline.json'), path.join(ROOT, 'build', part, 'data', 'voice')], { stdio: 'inherit' });
process.exit(r.status ?? 1);
