// Animated paper elements. Everything is a pure function of time so frames
// render identically in any order (required for parallel export).
import { css, mix, shade, h1, clamp, fract, makeCanvas } from './util.js';
import { glowSprite } from './paint.js';

const PAPER = '#f7ecd6';

// Origami crane, side view, wings flapping. (x,y) centre, size ~ wingspan.
export function crane(ctx, x, y, size, t, phase, pal, dir = 1, tint = 0.15) {
  const f = Math.sin(t * 9 + phase);
  const k = size / 60;
  const paper = mix(PAPER, pal.haze, tint);
  const dark = mix(paper, pal.near, 0.35);
  const mid = mix(paper, pal.near, 0.16);
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(dir * k, k);
  ctx.rotate(Math.sin(t * 2 + phase) * 0.08);
  // far wing
  ctx.fillStyle = css(dark);
  ctx.beginPath();
  ctx.moveTo(-6, -2); ctx.lineTo(10, -2); ctx.lineTo(4 + f * 4, -30 * f - 4); ctx.closePath(); ctx.fill();
  // tail
  ctx.fillStyle = css(mid);
  ctx.beginPath();
  ctx.moveTo(-8, 0); ctx.lineTo(-30, -20); ctx.lineTo(-22, -16); ctx.lineTo(-4, 4); ctx.fill();
  // neck + head
  ctx.beginPath();
  ctx.moveTo(8, 0); ctx.lineTo(26, -24); ctx.lineTo(34, -22); ctx.lineTo(27, -20); ctx.lineTo(12, 4); ctx.fill();
  // body
  ctx.fillStyle = css(paper);
  ctx.beginPath();
  ctx.moveTo(-14, 0); ctx.lineTo(0, -7); ctx.lineTo(16, 0); ctx.lineTo(0, 9); ctx.closePath(); ctx.fill();
  ctx.fillStyle = css(mid);
  ctx.beginPath();
  ctx.moveTo(-14, 0); ctx.lineTo(16, 0); ctx.lineTo(0, 9); ctx.closePath(); ctx.fill();
  // near wing
  ctx.fillStyle = css(paper);
  ctx.beginPath();
  ctx.moveTo(-8, -1); ctx.lineTo(10, -1); ctx.lineTo(-2 - f * 4, -36 * f); ctx.closePath(); ctx.fill();
  ctx.fillStyle = css(mid, 0.8);
  ctx.beginPath();
  ctx.moveTo(1, -1); ctx.lineTo(10, -1); ctx.lineTo(-2 - f * 4, -36 * f); ctx.closePath(); ctx.fill();
  ctx.restore();
}

// A flock flying across the frame. Positions are in layer-local coords.
export function craneFlock(ctx, t, pal, opt) {
  const { n = 14, x0 = -1500, x1 = 1500, y = -300, spread = 500, speed = 120, size = 40, seed = 3, dir = 1, rise = 0 } = opt;
  const span = x1 - x0;
  for (let i = 0; i < n; i++) {
    const off = h1(i, seed) * span;
    const sp = speed * (0.75 + h1(i, seed + 1) * 0.5);
    let x = x0 + fract((off + t * sp * dir) / span) * span;
    const yy = y + (h1(i, seed + 2) - 0.5) * spread + Math.sin(t * 1.3 + i) * 18 - rise * fract((off + t * sp) / span) * 400;
    crane(ctx, x, yy, size * (0.6 + h1(i, seed + 3) * 0.8), t, i * 1.7, pal, dir);
  }
}

// Floating paper sky lantern.
export function skyLantern(ctx, x, y, size, t, phase, pal) {
  const fl = 0.85 + 0.15 * Math.sin(t * 7 + phase * 3);
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.55 * fl;
  ctx.drawImage(glowSprite(pal.lamp), x - size * 3, y - size * 3, size * 6, size * 6);
  ctx.restore();
  const body = mix(pal.lamp, '#fff1c8', 0.35);
  ctx.fillStyle = css(body);
  ctx.beginPath();
  ctx.moveTo(x - size * 0.55, y - size * 0.7);
  ctx.lineTo(x + size * 0.55, y - size * 0.7);
  ctx.lineTo(x + size * 0.42, y + size * 0.7);
  ctx.lineTo(x - size * 0.42, y + size * 0.7);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = css(shade(pal.lamp, -0.25), 0.7);
  ctx.fillRect(x - size * 0.55, y - size * 0.78, size * 1.1, size * 0.16);
  ctx.fillStyle = css('#fffbe8', 0.9 * fl);
  ctx.beginPath(); ctx.ellipse(x, y + size * 0.45, size * 0.14, size * 0.22, 0, 0, Math.PI * 2); ctx.fill();
}

export function lanternField(ctx, t, pal, opt) {
  const { n = 20, x0 = -1500, x1 = 1500, y0 = -1400, y1 = 600, size = 16, seed = 9, speed = 30 } = opt;
  const h = y1 - y0;
  for (let i = 0; i < n; i++) {
    const x = x0 + h1(i, seed) * (x1 - x0) + Math.sin(t * 0.5 + i) * 20;
    const y = y1 - fract(h1(i, seed + 1) + (t * speed * (0.7 + h1(i, seed + 2) * 0.6)) / h) * h;
    skyLantern(ctx, x, y, size * (0.6 + h1(i, seed + 3) * 0.8), t, i, pal);
  }
}

// Falling blossom petals (pale, never red).
export function petals(ctx, t, opt) {
  const { n = 40, x0 = -700, x1 = 700, y0 = -1100, y1 = 1100, size = 9, seed = 13, wind = 60, color = '#f6cfd6' } = opt;
  const h = y1 - y0, w = x1 - x0;
  for (let i = 0; i < n; i++) {
    const fall = 70 + h1(i, seed) * 80;
    const y = y0 + fract(h1(i, seed + 1) + (t * fall) / h) * h;
    const x = x0 + fract(h1(i, seed + 2) + (t * wind) / w + Math.sin(t * 1.2 + i) * 0.01) * w;
    const rot = t * (1 + h1(i, seed + 3) * 3) + i;
    const sz = size * (0.6 + h1(i, seed + 4) * 0.9);
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rot);
    ctx.scale(1, Math.abs(Math.cos(rot * 1.3)) * 0.8 + 0.2);
    ctx.fillStyle = css(mix(color, '#ffffff', h1(i, seed + 5) * 0.4), 0.9);
    ctx.beginPath();
    ctx.ellipse(0, 0, sz, sz * 0.6, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

// Chimney smoke from recorded emitters [x, y, s] (layer-local coords).
let smokeSpr = null;
function smokeSprite() {
  if (smokeSpr) return smokeSpr;
  const c = makeCanvas(96, 96);
  const g = c.getContext('2d');
  for (let k = 0; k < 4; k++) {
    g.fillStyle = `rgba(255,255,255,${0.18 + k * 0.08})`;
    g.beginPath();
    g.arc(48 + (k - 1.5) * 3, 48 - k * 2, 46 - k * 10, 0, Math.PI * 2);
    g.fill();
  }
  smokeSpr = c;
  return c;
}
export function smoke(ctx, emitters, t, pal, opt = {}) {
  const spr = smokeSprite();
  const tint = makeTinted(spr, mix(pal.fog, '#e8e0f0', 0.25));
  const n = opt.puffs ?? 6;
  const max = opt.max ?? 60;
  for (let e = 0; e < Math.min(emitters.length, max); e++) {
    const [x, y, s] = emitters[e];
    for (let k = 0; k < n; k++) {
      const age = fract(t * 0.22 + k / n + h1(e, 31));
      const px = x + age * 60 * s + Math.sin(age * 6 + e) * 8 * s;
      const py = y - age * 190 * s;
      const r = (8 + age * 42) * s;
      ctx.globalAlpha = (1 - age) * Math.min(1, age * 6) * (opt.alpha ?? 0.5);
      ctx.drawImage(tint, px - r, py - r, r * 2, r * 2);
    }
  }
  ctx.globalAlpha = 1;
}
const tintCache = new Map();
function makeTinted(spr, color) {
  const key = css(color);
  if (tintCache.has(key)) return tintCache.get(key);
  const c = makeCanvas(spr.width, spr.height);
  const g = c.getContext('2d');
  g.drawImage(spr, 0, 0);
  g.globalCompositeOperation = 'source-in';
  g.fillStyle = key;
  g.fillRect(0, 0, c.width, c.height);
  tintCache.set(key, c);
  return c;
}

// A fluttering page that flies like a bird.
export function pageBird(ctx, x, y, size, t, phase, pal, glowAmt = 0) {
  const f = Math.sin(t * 11 + phase);
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(Math.sin(t * 1.7 + phase) * 0.35);
  if (glowAmt > 0) {
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = glowAmt;
    ctx.drawImage(glowSprite('#ffd36a'), -size * 3, -size * 3, size * 6, size * 6);
    ctx.restore();
  }
  const paper = mix(PAPER, pal.window, 0.12 + glowAmt * 0.3);
  for (const side of [-1, 1]) {
    const lift = f * 0.9 * side;
    ctx.fillStyle = css(side < 0 ? shade(paper, -0.12) : paper);
    ctx.beginPath();
    ctx.moveTo(0, -size * 0.5);
    ctx.lineTo(side * size * 0.9, -size * 0.5 - lift * size * 0.6);
    ctx.lineTo(side * size * 0.9, size * 0.5 - lift * size * 0.6);
    ctx.lineTo(0, size * 0.5);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = 'rgba(60,40,60,0.35)';
    ctx.lineWidth = Math.max(0.8, size * 0.04);
    ctx.beginPath();
    for (let l = 0; l < 4; l++) {
      const yy = -size * 0.3 + l * size * 0.18;
      ctx.moveTo(side * size * 0.15, yy - lift * size * 0.1);
      ctx.lineTo(side * size * 0.75, yy - lift * size * 0.5);
    }
    ctx.stroke();
  }
  ctx.restore();
}

// Floating tram car.
export function tram(ctx, x, y, s, pal, t) {
  const w = 190 * s, h = 70 * s;
  ctx.save();
  ctx.translate(x, y);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.4;
  ctx.drawImage(glowSprite(pal.window), -w * 0.8, -h * 1.6, w * 1.6, h * 2.4);
  ctx.restore();
  ctx.save();
  ctx.translate(x, y);
  const body = mix('#2f8a86', pal.near, 0.35);
  ctx.fillStyle = css(body);
  ctx.beginPath();
  ctx.roundRect(-w / 2, -h, w, h, 18 * s);
  ctx.fill();
  ctx.fillStyle = css(mix('#efe0c0', pal.near, 0.25));
  ctx.fillRect(-w / 2, -h * 0.35, w, h * 0.12);
  for (let i = 0; i < 6; i++) {
    ctx.fillStyle = css(mix(pal.window, '#fff2cc', 0.3));
    ctx.fillRect(-w / 2 + 14 * s + i * 28 * s, -h * 0.85, 20 * s, h * 0.42);
  }
  // pantograph
  ctx.strokeStyle = css(shade(body, -0.4));
  ctx.lineWidth = 3 * s;
  ctx.beginPath();
  ctx.moveTo(-20 * s, -h); ctx.lineTo(0, -h - 28 * s); ctx.lineTo(20 * s, -h);
  ctx.stroke();
  // under-glow sparks
  if (Math.sin(t * 23) > 0.6) {
    ctx.fillStyle = '#fff4c0';
    ctx.fillRect(-4 * s, -h - 32 * s, 8 * s, 6 * s);
  }
  ctx.restore();
}

// Swinging bell (for belfries). angle in radians.
export function bell(ctx, x, y, size, angle, pal) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle);
  const c = mix('#d9a441', pal.near, 0.15);
  ctx.fillStyle = css(shade(c, -0.35));
  ctx.fillRect(-size * 0.08, -size * 0.15, size * 0.16, size * 0.2);
  ctx.fillStyle = css(c);
  ctx.beginPath();
  ctx.moveTo(-size * 0.3, 0);
  ctx.quadraticCurveTo(-size * 0.34, size * 0.55, -size * 0.55, size * 0.85);
  ctx.lineTo(size * 0.55, size * 0.85);
  ctx.quadraticCurveTo(size * 0.34, size * 0.55, size * 0.3, 0);
  ctx.quadraticCurveTo(0, -size * 0.12, -size * 0.3, 0);
  ctx.fill();
  ctx.fillStyle = css(shade(c, 0.35));
  ctx.fillRect(-size * 0.22, size * 0.15, size * 0.08, size * 0.6);
  ctx.fillStyle = css(shade(c, -0.4));
  ctx.beginPath(); ctx.arc(Math.sin(angle * 2) * size * 0.2, size * 0.9, size * 0.1, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

export { clamp };
