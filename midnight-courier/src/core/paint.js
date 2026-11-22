// Painterly "paper-cut gouache" toolkit: rough brushed edges, posterised
// gradients, dry-brush texture, paper grain, rim light and cut-paper shadows.
import { makeCanvas, css, mix, shade, rng, clamp } from './util.js';

// Build a jittered path through pts (closed polygon by default).
export function roughPath(ctx, r, pts, jitter = 1.5, seg = 18, closed = true) {
  ctx.beginPath();
  const n = pts.length;
  const last = closed ? n : n - 1;
  for (let i = 0; i < last; i++) {
    const [x0, y0] = pts[i];
    const [x1, y1] = pts[(i + 1) % n];
    const len = Math.hypot(x1 - x0, y1 - y0);
    const steps = Math.max(1, Math.round(len / seg));
    const nx = -(y1 - y0) / (len || 1), ny = (x1 - x0) / (len || 1);
    for (let s = 0; s < steps; s++) {
      const t = s / steps;
      const j = s === 0 ? 0 : (r.next() - 0.5) * 2 * jitter;
      const x = x0 + (x1 - x0) * t + nx * j, y = y0 + (y1 - y0) * t + ny * j;
      if (i === 0 && s === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
  }
  if (closed) ctx.closePath(); else ctx.lineTo(pts[n - 1][0], pts[n - 1][1]);
}

export function roughRect(ctx, r, x, y, w, h, jitter = 1.2) {
  roughPath(ctx, r, [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], jitter, Math.max(8, Math.min(w, h) / 3));
}

// Posterised vertical gradient inside the current clip. Bands get slightly
// wavy edges so they read as gouache rather than CSS.
export function posterV(ctx, r, x, y, w, h, top, bottom, bands = 5, wave = 3) {
  const bh = h / bands;
  for (let i = 0; i < bands; i++) {
    const c = mix(top, bottom, bands === 1 ? 0 : i / (bands - 1));
    ctx.fillStyle = css(c);
    const y0 = y + i * bh;
    ctx.beginPath();
    ctx.moveTo(x - 2, y + h + 2);
    ctx.lineTo(x - 2, y0);
    const steps = Math.max(2, Math.round(w / 40));
    for (let s = 1; s <= steps; s++) {
      const xx = x + (w * s) / steps;
      ctx.lineTo(xx + 2, y0 + (i === 0 ? 0 : (r.next() - 0.5) * wave * 2));
    }
    ctx.lineTo(x + w + 2, y + h + 2);
    ctx.closePath();
    ctx.fill();
  }
}

// Dry-brush strokes for gouache texture.
export function brushTexture(ctx, r, x, y, w, h, color, n = 20, alpha = 0.12, len = 18, width = 3, horiz = false) {
  ctx.save();
  ctx.strokeStyle = css(color, alpha);
  ctx.lineCap = 'round';
  ctx.lineWidth = width;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const px = x + r.next() * w, py = y + r.next() * h;
    const a = horiz ? (r.next() - 0.5) * 0.4 : Math.PI / 2 + (r.next() - 0.5) * 0.5;
    const l = len * (0.5 + r.next());
    ctx.moveTo(px, py);
    ctx.quadraticCurveTo(px + Math.cos(a) * l * 0.5 + (r.next() - 0.5) * 4, py + Math.sin(a) * l * 0.5, px + Math.cos(a) * l, py + Math.sin(a) * l);
  }
  ctx.stroke();
  ctx.restore();
}

// ---------------- cached sprites ----------------
const glowCache = new Map();
export function glowSprite(color, size = 128, falloff = 2.2) {
  const key = css(color) + size + falloff;
  if (glowCache.has(key)) return glowCache.get(key);
  const c = makeCanvas(size, size);
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (let i = 0; i <= 8; i++) {
    const t = i / 8;
    grd.addColorStop(t, css(color, Math.pow(1 - t, falloff)));
  }
  g.fillStyle = grd;
  g.fillRect(0, 0, size, size);
  glowCache.set(key, c);
  return c;
}

let grainTileCanvas = null;
export function grainTile() {
  if (grainTileCanvas) return grainTileCanvas;
  const S = 256;
  const c = makeCanvas(S, S);
  const g = c.getContext('2d');
  const img = g.createImageData(S, S);
  const r = rng(99);
  for (let i = 0; i < S * S; i++) {
    const v = r.next();
    const light = v > 0.5;
    const a = Math.abs(v - 0.5) * 2;
    img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = light ? 255 : 20;
    img.data[i * 4 + 3] = Math.floor(a * a * 90);
  }
  g.putImageData(img, 0, 0);
  // paper fibres
  g.lineCap = 'round';
  for (let i = 0; i < 140; i++) {
    const x = r.next() * S, y = r.next() * S, a = r.next() * Math.PI * 2, l = 6 + r.next() * 22;
    g.strokeStyle = r.next() < 0.5 ? 'rgba(255,250,235,0.22)' : 'rgba(30,20,40,0.18)';
    g.lineWidth = 0.6 + r.next() * 0.8;
    g.beginPath();
    g.moveTo(x, y);
    g.quadraticCurveTo(x + Math.cos(a + 0.5) * l * 0.5, y + Math.sin(a + 0.5) * l * 0.5, x + Math.cos(a) * l, y + Math.sin(a) * l);
    g.stroke();
  }
  grainTileCanvas = c;
  return c;
}

// Rim light + grain + cut-paper drop shadow, baked into a layer.
export function finishLayer(src, pal, opts = {}) {
  const { rim = true, rimWidth = 4, rimAlpha = 0.75, grain = 0.5, shadow = 0.5, shadowBlur = 22, shadowOff = [5, 12] } = opts;
  const w = src.width, h = src.height;
  const g = src.getContext('2d');
  const [lx, ly] = pal.light || [0.7, -0.7];
  if (rim) {
    const tmp = makeCanvas(w, h);
    const t = tmp.getContext('2d');
    t.drawImage(src, 0, 0);
    t.globalCompositeOperation = 'source-in';
    t.fillStyle = css(opts.rimColor || pal.rim);
    t.fillRect(0, 0, w, h);
    t.globalCompositeOperation = 'destination-out';
    t.drawImage(src, -lx * rimWidth, -ly * rimWidth);
    g.save();
    g.globalCompositeOperation = 'source-atop';
    g.globalAlpha = rimAlpha;
    g.filter = 'blur(1px)';
    g.drawImage(tmp, 0, 0);
    g.restore();
  }
  if (grain > 0) {
    g.save();
    g.globalCompositeOperation = 'source-atop';
    g.globalAlpha = grain;
    g.fillStyle = g.createPattern(grainTile(), 'repeat');
    g.fillRect(0, 0, w, h);
    g.restore();
  }
  if (shadow <= 0) return src;
  const out = makeCanvas(w, h);
  const o = out.getContext('2d');
  o.shadowColor = `rgba(8,4,20,${shadow})`;
  o.shadowBlur = shadowBlur;
  o.shadowOffsetX = shadowOff[0];
  o.shadowOffsetY = shadowOff[1];
  o.drawImage(src, 0, 0);
  src.width = 1; // free memory
  return out;
}

// Soft posterised cloud (cut paper).
export function drawCloud(ctx, r, x, y, w, h, color, alpha = 0.85) {
  ctx.save();
  ctx.fillStyle = css(color, alpha);
  const n = 5 + Math.floor(r.next() * 4);
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const cx = x + (i / (n - 1) - 0.5) * w * 0.85;
    const rr = h * (0.35 + r.next() * 0.45) * (1 - Math.abs(i / (n - 1) - 0.5));
    ctx.moveTo(cx + rr, y);
    ctx.arc(cx, y - rr * 0.3, rr, 0, Math.PI * 2);
  }
  ctx.rect(x - w * 0.45, y - h * 0.05, w * 0.9, h * 0.25);
  ctx.fill();
  ctx.fillStyle = css(shade(color, 0.25), alpha * 0.6);
  ctx.beginPath();
  ctx.ellipse(x - w * 0.1, y - h * 0.4, w * 0.22, h * 0.16, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

export function glow(ctx, color, x, y, radius, alpha = 1) {
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = clamp(alpha);
  ctx.drawImage(glowSprite(color), x - radius, y - radius, radius * 2, radius * 2);
  ctx.restore();
}
