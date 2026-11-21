// Background layer shared by every scene: deep navy, bioluminescent jellyfish silhouettes (far),
// marine snow, faint sonar rings from the ping schedule, and the terminal HUD frame.
import { C, DW, DH, rgba, rng, text, stroke, clamp, SAFE } from './draw.js';

const R = rng(2024);
const SNOW = Array.from({ length: 170 }, () => ({ x: R() * DW, y: R() * DH, v: 6 + R() * 26, s: 0.8 + R() * R() * 3.2, ph: R() * 6.28, a: 0.12 + R() * 0.5, tw: R() }));
const JELLY = [
  { x: 190, y: 1500, s: 120, v: 11, ph: 0.0, a: 0.15 },
  { x: 880, y: 800, s: 90, v: 8, ph: 2.1, a: 0.12 },
  { x: 610, y: 1950, s: 70, v: 13, ph: 4.0, a: 0.10 },
  { x: 330, y: 420, s: 55, v: 7, ph: 1.3, a: 0.09 },
  { x: 960, y: 1750, s: 140, v: 9, ph: 3.3, a: 0.11 },
];

function jellyfish(ctx, j, jt, alpha) {
  const span = DH + 600;
  const y = ((j.y - jt * j.v) % span + span) % span - 300;
  const x = j.x + Math.sin(jt * 0.13 + j.ph) * 40;
  const pulse = Math.pow((Math.sin(jt * 1.25 + j.ph) + 1) / 2, 2);
  const w = j.s * (1 - 0.14 * pulse), h = j.s * (0.62 + 0.1 * pulse);
  const a = j.a * alpha;
  ctx.save(); ctx.translate(x, y);
  // bell
  stroke(ctx, C.cyan, a, 2.2);
  ctx.beginPath(); ctx.moveTo(-w, 0);
  ctx.bezierCurveTo(-w, -h * 1.35, w, -h * 1.35, w, 0);
  // scalloped rim
  const n = 8;
  for (let i = n; i >= 0; i--) { const xx = -w + (2 * w * i) / n; ctx.lineTo(xx, (i % 2 ? 7 : 0) + 0); }
  ctx.stroke();
  ctx.fillStyle = rgba(C.cyan, a * 0.18); ctx.fill();
  // inner bell
  stroke(ctx, C.cyan, a * 0.6, 1.4);
  ctx.beginPath(); ctx.ellipse(0, -h * 0.35, w * 0.45, h * 0.4, 0, Math.PI, 0); ctx.stroke();
  // tentacles
  for (let k = 0; k < 6; k++) {
    const x0 = -w * 0.8 + (1.6 * w * k) / 5, len = j.s * (1.6 + 0.6 * ((k * 37) % 5) / 5);
    stroke(ctx, C.cyan, a * 0.55, 1.2);
    ctx.beginPath(); ctx.moveTo(x0, 4);
    for (let s = 1; s <= 14; s++) { const f = s / 14; ctx.lineTo(x0 + Math.sin(jt * 1.6 + f * 5 + k) * 10 * f, 4 + f * len); }
    ctx.stroke();
  }
  ctx.restore();
}

export function drawAmbient(ctx, t, env, o = {}) {
  const alpha = o.alpha ?? 1;
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, DW, DH);
  if (alpha <= 0) return;
  const jt = env.jelly(t);
  for (const j of JELLY) jellyfish(ctx, j, jt + 40, alpha);
  // marine snow (drifts down, slows with the jellyfish when the station "holds its breath")
  const st = env.snowClock(t);
  for (const p of SNOW) {
    const y = ((p.y + st * p.v) % (DH + 20) + DH + 20) % (DH + 20) - 10;
    const x = p.x + Math.sin(st * 0.3 + p.ph) * 14;
    const tw = 0.6 + 0.4 * Math.sin(t * (0.8 + p.tw * 2) + p.ph);
    ctx.fillStyle = rgba(C.cyan, p.a * tw * alpha * 0.8);
    ctx.fillRect(x, y, p.s, p.s);
  }
  // ambient sonar rings from the ping schedule
  if (o.rings !== false) {
    const [cx, cy] = o.origin || [540, 700];
    for (const p of env.pings) {
      const age = t - p.t;
      if (age < 0 || age > 5 || p.strong) continue;
      const r = age * 330, fa = (1 - age / 5) * 0.22 * alpha;
      stroke(ctx, p.color === 'magenta' ? C.mag : C.cyan, fa, 2);
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();
      stroke(ctx, C.cyan, fa * 0.45, 1.2);
      ctx.beginPath(); ctx.arc(cx, cy, Math.max(0, r - 22), 0, Math.PI * 2); ctx.stroke();
    }
  }
}

export function drawHUD(ctx, t, env, o = {}) {
  const a = o.alpha ?? 1;
  if (a <= 0) return;
  const k = 34;
  stroke(ctx, C.cyan, 0.5 * a, 2);
  const x0 = 44, x1 = DW - 44, y0 = SAFE.top + 8, y1 = SAFE.bottom - 8;
  for (const [cx, cy, sx, sy] of [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]]) {
    ctx.beginPath(); ctx.moveTo(cx + sx * k, cy); ctx.lineTo(cx, cy); ctx.lineTo(cx, cy + sy * k); ctx.stroke();
  }
  text(ctx, o.left || 'HADAL-9 // RX-LOG', 70, 232, { size: 22, alpha: 0.8 * a, weight: 500 });
  const mm = Math.floor(t / 60), ss = (t % 60).toFixed(1).padStart(4, '0');
  const w = text(ctx, `REC T+${String(mm).padStart(2, '0')}:${ss}`, DW - 70, 232, { size: 22, alpha: 0.8 * a, align: 'right', weight: 500 });
  if ((t % 1.2) < 0.7) { ctx.fillStyle = rgba(C.cyan, 0.9 * a); ctx.beginPath(); ctx.arc(DW - 70 - w - 16, 232, 6, 0, 7); ctx.fill(); }
  text(ctx, o.bottom || 'DEPTH 11,000 M  ·  1,086 BAR  ·  1.9°C', DW / 2, 1508, { size: 21, alpha: 0.6 * a, align: 'center' });
  // scan tick line under the header
  stroke(ctx, C.cyan, 0.18 * a, 1);
  ctx.beginPath(); ctx.moveTo(70, 256); ctx.lineTo(DW - 70, 256); ctx.stroke();
  const sx = 70 + ((t * 120) % (DW - 140));
  stroke(ctx, C.cyan, 0.7 * a, 2); ctx.beginPath(); ctx.moveTo(sx, 252); ctx.lineTo(sx + 40, 252); ctx.stroke();
}
