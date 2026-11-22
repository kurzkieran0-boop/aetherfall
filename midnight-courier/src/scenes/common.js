// Shared scene helpers.
import gsap from 'gsap';
import { css, mix, clamp, h1 } from '../core/util.js';
import { layerXf, applyXf } from '../core/stage.js';
import { smoke } from '../core/sprites.js';
import { drawJuno } from '../core/juno.js';
import { glowSprite } from '../core/paint.js';

export const ease = (name) => gsap.parseEase(name || 'power2.inOut');
const easeIO = ease('power2.inOut');

// Window [start,end] (0..1 of shot) -> eased 0..1
export function win(p, a = 0, b = 1, e = easeIO) { return e(clamp((p - a) / Math.max(1e-4, b - a))); }

export function useLayer(ctx, d, cam, offX = 0, offY = 0) {
  const xf = layerXf(d, cam, offX, offY);
  applyXf(ctx, xf, cam.roll || 0);
  return xf;
}

export function layerSmoke(ctx, L, f, alpha = 0.45) {
  if (!L.info.chimneys.length) return;
  smoke(ctx, L.info.chimneys, f.pt, f.pal, { alpha, max: 70 });
}

export function clockHands(ctx, L, f, timeH = null) {
  for (const [x, y, r, s] of L.info.clocks) {
    const hours = timeH ?? (11 + 50 / 60 + f.t / 60);
    // crisp vector face (stays sharp on push-ins)
    ctx.fillStyle = css(mix('#fff3d6', f.pal.window, 0.35));
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = css(mix('#2a1c30', f.pal.near, 0.3));
    ctx.lineCap = 'round';
    for (let i = 0; i < 60; i++) {
      const a = (i / 60) * Math.PI * 2;
      const big = i % 5 === 0;
      ctx.lineWidth = Math.max(0.6, (big ? 2.4 : 0.9) * s);
      ctx.beginPath();
      ctx.moveTo(x + Math.cos(a) * r * (big ? 0.78 : 0.88), y + Math.sin(a) * r * (big ? 0.78 : 0.88));
      ctx.lineTo(x + Math.cos(a) * r * 0.95, y + Math.sin(a) * r * 0.95);
      ctx.stroke();
    }
    ctx.lineWidth = Math.max(1, 1.5 * s);
    ctx.beginPath(); ctx.arc(x, y, r * 0.98, 0, Math.PI * 2); ctx.stroke();
    const ma = ((hours % 1) * Math.PI * 2) - Math.PI / 2;
    const ha = (((hours % 12) / 12) * Math.PI * 2) - Math.PI / 2;
    ctx.lineWidth = Math.max(2, 5 * s);
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(ha) * r * 0.5, y + Math.sin(ha) * r * 0.5); ctx.stroke();
    ctx.lineWidth = Math.max(1.5, 3 * s);
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(ma) * r * 0.8, y + Math.sin(ma) * r * 0.8); ctx.stroke();
    ctx.fillStyle = '#ffc43d';
    ctx.beginPath(); ctx.arc(x, y, Math.max(2, 5 * s), 0, Math.PI * 2); ctx.fill();
  }
}

export function glowPoints(ctx, L, f, pulse = 1) {
  for (const [x, y, r] of L.info.glows) {
    const a = 0.6 + 0.4 * Math.sin(f.t * 3 + x);
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = a * pulse;
    ctx.drawImage(glowSprite(f.pal.lamp), x - r * 4, y - r * 4, r * 8, r * 8);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
}

// Every lit window becomes an eye; pupils swing to stare at the viewer.
export function windowEyes(ctx, L, f, amt, look) {
  if (amt <= 0) return;
  const pal = f.pal;
  for (let i = 0; i < L.info.windows.length; i++) {
    const [x, y, w, h] = L.info.windows[i];
    if (w < 6 || h < 6) continue;
    const delay = h1(i, 77) * 0.35;
    const a = clamp((amt - delay) / 0.3);
    if (a <= 0) continue;
    const cx = x + w / 2, cy = y + h / 2;
    const ew = w * 0.5, eh = Math.min(h * 0.44, ew * 0.78) * a;
    ctx.fillStyle = '#fffaf0';
    ctx.beginPath(); ctx.ellipse(cx, cy, ew, eh, 0, 0, Math.PI * 2); ctx.fill();
    const side = (h1(i, 78) < 0.5 ? -1 : 1) * (1 - clamp(look - h1(i, 79) * 0.3));
    ctx.fillStyle = '#1a1030';
    ctx.beginPath(); ctx.arc(cx + side * ew * 0.45, cy, Math.min(ew, eh) * 0.62, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ffc43d';
    ctx.beginPath(); ctx.arc(cx + side * ew * 0.45, cy, Math.min(ew, eh) * 0.22, 0, Math.PI * 2); ctx.fill();
  }
}

// Juno in a layer's local coords. motion: {vx, vy} in px/s (local), used by
// the scarf cloth sim.
export function juno(ctx, x, y, h, f, st = {}) {
  const vx = st.vx ?? 0, vy = st.vy ?? 0;
  drawJuno(ctx, x, y, h, {
    mode: st.mode || 'stand',
    phase: st.phase ?? f.t * 11,
    facing: st.facing ?? 1,
    t: f.t,
    scarfT: f.t,
    rim: f.pal.rim,
    knocking: st.knocking,
    reach: st.reach,
    letter: st.letter,
    wind: st.wind ?? 1.2,
    motionAt: st.motionAt || (() => ({ vx: (vx / h) * (st.facing ?? 1), vy: vy / h })),
  });
}

export function roofAt(L, x) {
  let best = null;
  for (const r of L.info.roofs) if (x >= r[0] && x <= r[1] && (!best || r[2] < best[2])) best = r;
  return best;
}

export function nearestRoof(L, x, minW = 60) {
  let best = null, bd = 1e9;
  for (const r of L.info.roofs) {
    if (r[1] - r[0] < minW) continue;
    const c = (r[0] + r[1]) / 2;
    if (Math.abs(c - x) < bd) { bd = Math.abs(c - x); best = r; }
  }
  return best;
}
