// 2.5D multi-plane stage: projects depth layers through a dolly camera,
// draws the dynamic sky, volumetric fog bands and light shafts.
import { W, H, clamp, css, mix, shade, sampleStops, h1, noise1, makeCanvas, rng } from './util.js';
import { glowSprite, drawCloud } from './paint.js';

// Camera: {x, y, z (dolly toward scene), zoom, roll (deg)}
export function layerXf(d, cam, offX = 0, offY = 0) {
  const dz = Math.max(0.05, d - cam.z);
  const k = (cam.zoom * d) / dz;
  return { k, ox: W / 2 - (cam.zoom * cam.x) / dz + offX * k, oy: H / 2 - (cam.zoom * cam.y) / dz + offY * k, dz };
}

// Set the canvas transform so that layer-local coordinates map to screen.
export function applyXf(ctx, xf, roll = 0) {
  const r = (roll * Math.PI) / 180;
  const c = Math.cos(r), s = Math.sin(r);
  const ex = xf.ox - W / 2, ey = xf.oy - H / 2;
  ctx.setTransform(xf.k * c, xf.k * s, -xf.k * s, xf.k * c, c * ex - s * ey + W / 2, s * ex + c * ey + H / 2);
}

export function project(d, cam, lx, ly) {
  const xf = layerXf(d, cam);
  return [xf.ox + lx * xf.k, xf.oy + ly * xf.k, xf.k];
}

export function layerAlpha(d, cam) {
  const dz = d - cam.z;
  return clamp((dz - 0.12) / 0.3);
}

// Draw a baked layer (and optional lit overlay). Returns its transform.
export function drawLayer(ctx, L, cam, opt = {}) {
  const a = layerAlpha(L.d, cam) * (opt.alpha ?? 1);
  const xf = layerXf(L.d, cam, opt.offX || 0, opt.offY || 0);
  if (a <= 0.003) return { xf, visible: false };
  applyXf(ctx, xf, cam.roll || 0);
  ctx.globalAlpha = a;
  ctx.drawImage(L.canvas, L.x0, L.y0);
  if (L.lit && opt.lit > 0) {
    ctx.globalAlpha = a * clamp(opt.lit);
    ctx.drawImage(L.lit, L.x0, L.y0);
  }
  ctx.globalAlpha = 1;
  return { xf, visible: true };
}

// ---------------------------------------------------------------- sky
const cloudCache = new Map();
function cloudSprites(pal) {
  const key = css(pal.cloud) + css(pal.sky[2]);
  if (cloudCache.has(key)) return cloudCache.get(key);
  const r = rng(5);
  const list = [];
  for (let i = 0; i < 5; i++) {
    const c = makeCanvas(520, 220);
    const g = c.getContext('2d');
    drawCloud(g, r, 260, 150, r.range(300, 480), r.range(90, 150), mix(pal.cloud, pal.sky[1], r.range(0, 0.35)), 0.9);
    list.push(c);
  }
  cloudCache.set(key, list);
  if (cloudCache.size > 6) cloudCache.delete(cloudCache.keys().next().value);
  return list;
}

export function drawSky(ctx, pal, cam, t, opts = {}) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const par = opts.parallax ?? 28;
  const sy = -cam.y / par;
  const bands = 10;
  // base fill
  ctx.fillStyle = css(pal.sky[pal.sky.length - 1]);
  ctx.fillRect(0, 0, W, H);
  const span = H * 1.25;
  const top = -H * 0.2 + sy - 200;
  for (let i = bands - 1; i >= 0; i--) {
    const c = sampleStops(pal.sky, i / (bands - 1));
    ctx.fillStyle = css(c);
    const y0 = top + (span * i) / bands;
    ctx.beginPath();
    ctx.moveTo(-10, -10);
    ctx.lineTo(W + 10, -10);
    const steps = 12;
    for (let k = steps; k >= 0; k--) {
      const x = (W * k) / steps;
      const yy = y0 + span / bands + Math.sin(x * 0.006 + i * 1.7 + t * 0.15) * 14 + (noise1(x * 0.01 + i * 3.1, i) - 0.5) * 20;
      ctx.lineTo(x + (k === steps ? 10 : 0) - (k === 0 ? 10 : 0), yy);
    }
    ctx.closePath();
    ctx.globalAlpha = i === bands - 1 ? 1 : 1;
    ctx.fill();
  }
  // re-fill bottom (bands are drawn top-down; ensure lower sky colour)
  // stars
  if (pal.stars > 0.02) {
    for (let i = 0; i < 220; i++) {
      const x = ((h1(i, 7) * W * 1.6 - cam.x / 60) % (W * 1.6) + W * 1.6) % (W * 1.6) - W * 0.3;
      const y = h1(i, 8) * H * 0.75 + sy * 0.5;
      const tw = 0.5 + 0.5 * Math.sin(t * (1.5 + h1(i, 9) * 3) + i);
      const sz = (0.8 + h1(i, 10) * 2.2) * (0.6 + tw * 0.4);
      ctx.fillStyle = `rgba(255,248,225,${pal.stars * (0.35 + tw * 0.55)})`;
      ctx.fillRect(x, y, sz, sz);
      if (h1(i, 11) < 0.06) {
        ctx.globalAlpha = pal.stars * 0.5 * tw;
        ctx.drawImage(glowSprite('#fff4d8'), x - 10, y - 10, 20, 20);
        ctx.globalAlpha = 1;
      }
    }
  }
  // sun / moon
  const sun = pal.sun;
  if (sun && !opts.noSun) {
    const sx = sun.x * W - cam.x / (par * 1.5), syy = sun.y * H + sy;
    const R = sun.r;
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.55;
    ctx.drawImage(glowSprite(sun.glow, 256, 1.6), sx - R * 6, syy - R * 6, R * 12, R * 12);
    ctx.globalAlpha = 0.5;
    ctx.drawImage(glowSprite(sun.color, 256, 2.5), sx - R * 2.6, syy - R * 2.6, R * 5.2, R * 5.2);
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    // paper-cut halo rings
    for (let k = 3; k >= 1; k--) {
      ctx.fillStyle = css(mix(sun.glow, pal.sky[3], 0.3), 0.12);
      ctx.beginPath(); ctx.arc(sx, syy, R * (1 + k * 0.28), 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = css(sun.color);
    ctx.beginPath(); ctx.arc(sx, syy, R, 0, Math.PI * 2); ctx.fill();
    if (sun.kind === 'moon') {
      ctx.fillStyle = css(shade(sun.color, -0.12), 0.8);
      for (let k = 0; k < 5; k++) {
        ctx.beginPath();
        ctx.arc(sx + (h1(k, 3) - 0.5) * R * 1.1, syy + (h1(k, 4) - 0.5) * R * 1.1, R * (0.08 + h1(k, 5) * 0.14), 0, Math.PI * 2);
        ctx.fill();
      }
    } else {
      ctx.fillStyle = css(shade(sun.color, 0.4), 0.8);
      ctx.beginPath(); ctx.arc(sx - R * 0.25, syy - R * 0.25, R * 0.55, 0, Math.PI * 2); ctx.fill();
    }
  }
  // drifting paper clouds
  const clouds = cloudSprites(pal);
  for (let i = 0; i < 7; i++) {
    const cw = 520 * (0.8 + h1(i, 21) * 0.9);
    const range = W + cw * 2;
    const x = ((h1(i, 22) * range + t * (8 + h1(i, 23) * 14) - cam.x / 18) % range + range) % range - cw;
    const y = h1(i, 24) * H * 0.7 + sy * 1.3 - 100;
    ctx.globalAlpha = 0.75;
    ctx.drawImage(clouds[i % clouds.length], x, y, cw, cw * 0.42);
  }
  ctx.globalAlpha = 1;
}

// Low-lying volumetric fog band, in screen space but riding the camera.
export function drawFog(ctx, pal, cam, t, opt = {}) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const d = opt.d || 3;
  const baseY = H / 2 + ((opt.y ?? 500) * d - cam.y) * cam.zoom / Math.max(0.1, d - cam.z);
  const hgt = opt.h ?? 700;
  const g = ctx.createLinearGradient(0, baseY - hgt, 0, baseY + 200);
  const c = opt.color || pal.fog;
  g.addColorStop(0, css(c, 0));
  g.addColorStop(0.6, css(c, (opt.alpha ?? 0.45) * 0.6));
  g.addColorStop(1, css(c, opt.alpha ?? 0.45));
  ctx.fillStyle = g;
  ctx.fillRect(0, baseY - hgt, W, H - (baseY - hgt) + 10);
  // wisps
  ctx.globalAlpha = (opt.alpha ?? 0.45) * 0.55;
  for (let i = 0; i < 9; i++) {
    const ww = 600 + h1(i, 41) * 700;
    const range = W + ww;
    const x = ((h1(i, 42) * range + t * (12 + h1(i, 43) * 20) * (i % 2 ? 1 : -0.6) - cam.x / d) % range + range) % range - ww / 2;
    const y = baseY - hgt * (0.1 + h1(i, 44) * 0.6);
    ctx.drawImage(glowSprite(c, 128, 1.2), x - ww / 2, y - 60, ww, 160);
  }
  ctx.globalAlpha = 1;
}

// Volumetric light shafts from a point (screen space, additive).
export function drawShafts(ctx, color, sx, sy, t, opt = {}) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = 'lighter';
  const n = opt.n || 5;
  for (let i = 0; i < n; i++) {
    const a = (opt.angle ?? Math.PI / 2) + (i - (n - 1) / 2) * (opt.spread ?? 0.22) + Math.sin(t * 0.3 + i) * 0.03;
    const len = opt.len || 1900;
    const w0 = opt.w0 ?? 20, w1 = (opt.w1 ?? 260) * (0.7 + h1(i, 5) * 0.6);
    const ex = sx + Math.cos(a) * len, ey = sy + Math.sin(a) * len;
    const nx = -Math.sin(a), ny = Math.cos(a);
    const g = ctx.createLinearGradient(sx, sy, ex, ey);
    const al = (opt.alpha ?? 0.12) * (0.6 + 0.4 * Math.sin(t * 0.7 + i * 2.1));
    g.addColorStop(0, css(color, al));
    g.addColorStop(1, css(color, 0));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(sx + nx * w0, sy + ny * w0);
    ctx.lineTo(ex + nx * w1, ey + ny * w1);
    ctx.lineTo(ex - nx * w1, ey - ny * w1);
    ctx.lineTo(sx - nx * w0, sy - ny * w0);
    ctx.fill();
  }
  ctx.globalCompositeOperation = 'source-over';
}

// Full-screen tint wash (used for haze between layers).
export function wash(ctx, color, alpha) {
  if (alpha <= 0) return;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = css(color, alpha);
  ctx.fillRect(0, 0, W, H);
}
