// Juno: a small flat-shaded courier silhouette with a procedural run cycle,
// a big satchel, and the only red in the film — a verlet-simulated scarf.
import { css, mix, clamp, noise1 } from './util.js';
import { SCARF } from './palettes.js';

const BODY = '#191530';
const BODY_LIT = '#3a3462';
const BAG = '#9a6a34';
const BAG_FLAP = '#b98446';

// ---- scarf cloth (deterministic: re-simulated from a fixed warm-up window)
const SEG = 10;
export function simulateScarf(t, motionAt, opts = {}) {
  const L = 0.062; // segment length in body-heights
  const dt = 1 / 120;
  const warm = 1.6;
  const t0 = t - warm;
  const pts = [], prev = [];
  for (let i = 0; i <= SEG; i++) { pts.push([-i * L * 0.3, i * L * 0.95]); prev.push([pts[i][0], pts[i][1]]); }
  const steps = Math.round(warm / dt);
  for (let s = 0; s <= steps; s++) {
    const tt = t0 + s * dt;
    const m = motionAt(tt); // {vx, vy} in body-heights / s (facing-local)
    const gust = (noise1(tt * 2.2, 5) - 0.5) * 2.2 + (opts.wind ?? 0.6);
    const wx = -m.vx * 0.9 - gust;
    const wy = -m.vy * 0.5 + (noise1(tt * 3.1, 9) - 0.5) * 0.8;
    for (let i = 1; i <= SEG; i++) {
      const p = pts[i], q = prev[i];
      const vx = (p[0] - q[0]) / dt, vy = (p[1] - q[1]) / dt;
      const flutter = Math.sin(tt * 17 + i * 0.9) * 0.9 * Math.min(1, Math.abs(wx) / 2);
      const ax = (wx - vx) * 5.5;
      const ay = 4.2 + (wy - vy) * 5.5 + flutter * 3;
      q[0] = p[0]; q[1] = p[1];
      p[0] += vx * dt * 0.995 + ax * dt * dt;
      p[1] += vy * dt * 0.995 + ay * dt * dt;
    }
    for (let it = 0; it < 4; it++) {
      pts[0][0] = 0; pts[0][1] = 0;
      for (let i = 0; i < SEG; i++) {
        const a = pts[i], b = pts[i + 1];
        const dx = b[0] - a[0], dy = b[1] - a[1];
        const d = Math.hypot(dx, dy) || 1e-6;
        const k = (d - L) / d;
        if (i === 0) { b[0] -= dx * k; b[1] -= dy * k; }
        else { a[0] += dx * k * 0.5; a[1] += dy * k * 0.5; b[0] -= dx * k * 0.5; b[1] -= dy * k * 0.5; }
      }
    }
  }
  return pts;
}

function drawScarfTail(ctx, pts, h) {
  const n = pts.length;
  const left = [], right = [];
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)];
    let dx = b[0] - a[0], dy = b[1] - a[1];
    const d = Math.hypot(dx, dy) || 1;
    dx /= d; dy /= d;
    const w = h * 0.034 * (1 - (i / n) * 0.35);
    left.push([pts[i][0] * h - dy * w, pts[i][1] * h + dx * w]);
    right.push([pts[i][0] * h + dy * w, pts[i][1] * h - dx * w]);
  }
  for (let i = 0; i < n - 1; i++) {
    const cross = (pts[i + 1][0] - pts[i][0]) * (i > 0 ? pts[i][1] - pts[i - 1][1] : 1) - (pts[i + 1][1] - pts[i][1]) * (i > 0 ? pts[i][0] - pts[i - 1][0] : 0);
    ctx.fillStyle = (i % 3 === 1) !== cross > 0 ? SCARF.dark : SCARF.main;
    ctx.beginPath();
    ctx.moveTo(left[i][0], left[i][1]);
    ctx.lineTo(left[i + 1][0], left[i + 1][1]);
    ctx.lineTo(right[i + 1][0], right[i + 1][1]);
    ctx.lineTo(right[i][0], right[i][1]);
    ctx.closePath();
    ctx.fill();
  }
  // fringe
  const e = pts[n - 1], e2 = pts[n - 2];
  ctx.strokeStyle = SCARF.main;
  ctx.lineWidth = Math.max(1, h * 0.012);
  ctx.beginPath();
  for (let k = -1; k <= 1; k++) {
    ctx.moveTo(e[0] * h + k * h * 0.015, e[1] * h);
    ctx.lineTo((e[0] + (e[0] - e2[0]) * 0.8) * h + k * h * 0.02, (e[1] + (e[1] - e2[1]) * 0.8) * h);
  }
  ctx.stroke();
}

function limb(ctx, x0, y0, a1, l1, a2, l2, w, color) {
  const x1 = x0 + Math.sin(a1) * l1, y1 = y0 + Math.cos(a1) * l1;
  const x2 = x1 + Math.sin(a2) * l2, y2 = y1 + Math.cos(a2) * l2;
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.beginPath();
  ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.lineTo(x2, y2);
  ctx.stroke();
  return [x2, y2];
}

// Pose generator. Angles are from vertical-down; + is forward.
function pose(mode, ph, t, st) {
  const P = { lean: 0, bob: 0, legs: [[0, 0], [0, 0]], arms: [[0, 0.3], [0, 0.3]], head: 0 };
  if (mode === 'run' || mode === 'climb') {
    const amp = mode === 'climb' ? 0.7 : 0.95;
    P.lean = mode === 'climb' ? 0.12 : 0.28;
    P.bob = -Math.abs(Math.sin(ph)) * 0.045;
    for (let i = 0; i < 2; i++) {
      const p = ph + i * Math.PI;
      const th = Math.sin(p) * amp + 0.15;
      const knee = 0.15 + 1.45 * Math.max(0, Math.cos(p)) * (mode === 'climb' ? 0.8 : 1);
      P.legs[i] = [th, th - knee];
      const sh = -Math.sin(p) * 0.9;
      P.arms[i] = [sh, sh + 1.5];
    }
  } else if (mode === 'jump') {
    P.lean = 0.35;
    P.legs = [[1.1, -0.4], [-0.2, -1.2]];
    P.arms = [[-1.6, -0.8], [2.2, 2.9]];
  } else if (mode === 'knock') {
    const k = Math.max(0, Math.sin(t * 16)) * (st.knocking ? 1 : 0);
    P.legs = [[0.12, 0.05], [-0.1, -0.12]];
    P.arms = [[2.2, 1.3 + k * 0.9], [0.1, 0.3]];
    P.lean = 0.05;
  } else if (mode === 'hold') {
    P.legs = [[0.1, 0.05], [-0.08, -0.1]];
    P.arms = [[1.3, 1.9], [1.1, 1.8]];
    P.head = 0.25;
  } else if (mode === 'reach') {
    const r = clamp(st.reach ?? 0.5);
    P.legs = [[0.12, 0.05], [-0.1, -0.12]];
    P.arms = [[-0.5 + r * 1.9, 0.8 + r * 0.9], [0.2, 0.4]];
    P.head = 0.3;
  } else if (mode === 'look') {
    P.legs = [[0.1, 0.05], [-0.12, -0.12]];
    P.arms = [[0.15, 0.35], [-0.1, 0.1]];
    P.head = -0.35;
  } else {
    // stand / idle
    const br = Math.sin(t * 2.2) * 0.02;
    P.legs = [[0.12, 0.08], [-0.1, -0.1]];
    P.arms = [[0.12 + br, 0.35], [-0.12 - br, 0.2]];
    P.bob = br * 0.3;
  }
  return P;
}

// Draw Juno. (x, y) = point between the feet; h = height in px.
// st: {mode, phase, facing, t, motionAt(t)->{vx,vy}, scarfT, rim}
export function drawJuno(ctx, x, y, h, st) {
  const mode = st.mode || 'stand';
  const P = pose(mode, st.phase || 0, st.t || 0, st);
  const facing = st.facing || 1;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(facing, 1);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const hipY = -h * 0.47 + P.bob * h;
  const shY = -h * 0.75 + P.bob * h;
  const lean = P.lean;
  const shX = Math.sin(lean) * h * 0.28;
  const rim = st.rim ? css(st.rim) : BODY_LIT;
  // scarf simulation (local to facing)
  const pts = simulateScarf(st.scarfT ?? st.t ?? 0, st.motionAt || (() => ({ vx: 0, vy: 0 })), { wind: st.wind });
  const neck = [shX + h * 0.01, shY - h * 0.02];
  // far limbs
  limb(ctx, 0, hipY, P.legs[1][0], h * 0.25, P.legs[1][1], h * 0.25, h * 0.075, '#120f24');
  limb(ctx, shX, shY + h * 0.03, P.arms[1][0], h * 0.17, P.arms[1][1], h * 0.16, h * 0.06, '#120f24');
  // scarf tail behind body
  ctx.save();
  ctx.translate(neck[0], neck[1]);
  drawScarfTail(ctx, pts, h);
  ctx.restore();
  // satchel (big) at the back hip
  ctx.save();
  ctx.translate(Math.sin(lean) * h * 0.1 - h * 0.12, hipY - h * 0.02);
  ctx.rotate(-lean * 0.5 + Math.sin((st.phase || 0) * 2) * 0.06);
  ctx.fillStyle = BAG;
  ctx.beginPath();
  ctx.roundRect(-h * 0.17, -h * 0.13, h * 0.26, h * 0.22, h * 0.04);
  ctx.fill();
  ctx.fillStyle = BAG_FLAP;
  ctx.beginPath();
  ctx.roundRect(-h * 0.17, -h * 0.13, h * 0.26, h * 0.1, h * 0.03);
  ctx.fill();
  ctx.fillStyle = '#ffd36a';
  ctx.fillRect(-h * 0.05, -h * 0.05, h * 0.03, h * 0.03);
  ctx.restore();
  // torso
  ctx.strokeStyle = BODY;
  ctx.lineWidth = h * 0.15;
  ctx.beginPath();
  ctx.moveTo(0, hipY);
  ctx.lineTo(shX, shY + h * 0.02);
  ctx.stroke();
  // coat tail
  ctx.fillStyle = BODY;
  ctx.beginPath();
  ctx.moveTo(-h * 0.07, hipY - h * 0.04);
  ctx.lineTo(h * 0.07, hipY - h * 0.04);
  ctx.lineTo(h * 0.05 - lean * h * 0.15, hipY + h * 0.11);
  ctx.lineTo(-h * 0.11 - lean * h * 0.25, hipY + h * 0.1);
  ctx.fill();
  // strap across chest
  ctx.strokeStyle = '#6e4a24';
  ctx.lineWidth = h * 0.025;
  ctx.beginPath();
  ctx.moveTo(shX + h * 0.04, shY + h * 0.01);
  ctx.lineTo(-h * 0.06, hipY - h * 0.02);
  ctx.stroke();
  // near limbs
  limb(ctx, 0, hipY, P.legs[0][0], h * 0.25, P.legs[0][1], h * 0.25, h * 0.08, BODY);
  const hand = limb(ctx, shX, shY + h * 0.03, P.arms[0][0], h * 0.17, P.arms[0][1], h * 0.16, h * 0.065, BODY);
  if (st.letter) {
    ctx.fillStyle = '#f7ecd6';
    ctx.save();
    ctx.translate(hand[0], hand[1]);
    ctx.rotate(-0.3);
    ctx.fillRect(-h * 0.02, -h * 0.09, h * 0.14, h * 0.1);
    ctx.fillStyle = '#ffc43d';
    ctx.fillRect(h * 0.04, -h * 0.05, h * 0.03, h * 0.03);
    ctx.restore();
  }
  // head + courier cap
  const hx = shX + h * 0.02 + Math.sin(P.head) * h * 0.03, hy = shY - h * 0.11;
  ctx.fillStyle = BODY;
  ctx.beginPath(); ctx.arc(hx, hy, h * 0.1, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath();
  ctx.ellipse(hx - h * 0.005, hy - h * 0.055, h * 0.11, h * 0.065, -0.15 + P.head * 0.3, Math.PI, 0);
  ctx.fill();
  ctx.fillRect(hx, hy - h * 0.06, h * 0.14, h * 0.025);
  // hair tuft
  ctx.beginPath();
  ctx.moveTo(hx - h * 0.08, hy + h * 0.02);
  ctx.quadraticCurveTo(hx - h * 0.17, hy + h * 0.06, hx - h * 0.15, hy + h * 0.12);
  ctx.lineTo(hx - h * 0.06, hy + h * 0.05);
  ctx.fill();
  // rim light (light from facing direction above)
  ctx.strokeStyle = rim;
  ctx.globalAlpha = 0.7;
  ctx.lineWidth = Math.max(1, h * 0.018);
  ctx.beginPath(); ctx.arc(hx, hy, h * 0.1, -Math.PI * 0.45, Math.PI * 0.15); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(shX + h * 0.075, shY + h * 0.02); ctx.lineTo(h * 0.07, hipY); ctx.stroke();
  ctx.globalAlpha = 1;
  // scarf wrap at the neck
  ctx.fillStyle = SCARF.main;
  ctx.beginPath();
  ctx.ellipse(neck[0], neck[1], h * 0.075, h * 0.04, -0.2, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = SCARF.light;
  ctx.fillRect(neck[0] - h * 0.02, neck[1] - h * 0.03, h * 0.05, h * 0.015);
  ctx.restore();
}

export { mix };
