// Shared helpers for shots/export: local Vite server + headless Chromium (SwiftShader WebGL).
import { createServer } from 'vite';
import { chromium } from 'playwright';
import fs from 'node:fs';

export async function startServer() {
  const server = await createServer({ configFile: new URL('../vite.config.js', import.meta.url).pathname, root: new URL('..', import.meta.url).pathname, logLevel: 'error', server: { port: 0, host: '127.0.0.1' } });
  await server.listen();
  return { server, url: `http://127.0.0.1:${server.httpServer.address().port}` };
}
export async function launch() {
  const args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--autoplay-policy=no-user-gesture-required'];
  try { return await chromium.launch({ args }); } catch (e) {
    if (fs.existsSync('/opt/pw-browsers/chromium')) return chromium.launch({ args, executablePath: '/opt/pw-browsers/chromium' });
    throw e;
  }
}
export async function openStory(browser, base, { ep = 'part1', w, h, extra = '' }) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log(`[page ${m.type()}]`, m.text()); });
  page.on('pageerror', (e) => console.log('[pageerror]', e.message));
  await page.goto(`${base}/?ep=${ep}&w=${w}&h=${h}&export=1${extra}`);
  await page.waitForFunction(() => window.__sbReady || window.__sbError, null, { timeout: 180000 });
  const err = await page.evaluate(() => window.__sbError);
  if (err) throw new Error(err);
  return page;
}
