// Copies the fitted timeline + voice into public/data for `npm run dev`.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const part = process.env.PART || process.env.npm_package_config_part || 'part1';
const src = path.join(ROOT, 'build', part, 'data');
if (!fs.existsSync(path.join(src, 'timeline.json'))) { console.log(`no build/${part}/data yet — run: npm run voice && npm run fit`); process.exit(0); }
fs.rmSync(path.join(ROOT, 'public', 'data'), { recursive: true, force: true });
fs.cpSync(src, path.join(ROOT, 'public', 'data'), { recursive: true });
console.log(`prepared public/data from build/${part}/data`);
