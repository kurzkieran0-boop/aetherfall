// Shared drawing helpers. All drawing happens in DESIGN space (1080x1920); the ctx carries a scale.
export const DW = 1080, DH = 1920;
export const C = { bg: '#02060d', cyan: '#19f0ff', mag: '#ff2e88' };
export const MONO = '"IBM Plex Mono", monospace';
export const VT = 'VT323, monospace';
export const SAFE = { top: 192, bottom: 1536, left: 54, right: 1026 };

export function rgba(hex, a = 1) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${Math.max(0, Math.min(1, a))})`;
}
export const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
export function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6d2b79f5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
export function vnoise(x, seed = 0) { const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f); return lerp(hash(i + seed * 57.3), hash(i + 1 + seed * 57.3), u); }
export function vnoise2(x, y, seed = 0) {
  const i = Math.floor(x), j = Math.floor(y), fx = x - i, fy = y - j;
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  const h = (a, b) => hash(a * 157.31 + b * 113.97 + seed * 71.1);
  return lerp(lerp(h(i, j), h(i + 1, j), ux), lerp(h(i, j + 1), h(i + 1, j + 1), ux), uy);
}

// ------------------------------------------------------------------ text with safe-area bookkeeping
let TEXTS = [];
export const resetTexts = () => { TEXTS = []; };
export const getTexts = () => TEXTS;
export function text(ctx, str, x, y, o = {}) {
  const size = o.size || 28;
  ctx.font = `${o.weight || 400} ${size}px ${o.font || MONO}`;
  ctx.textAlign = o.align || 'left';
  ctx.textBaseline = o.baseline || 'middle';
  if (o.spacing) ctx.letterSpacing = `${o.spacing}px`; else ctx.letterSpacing = '0px';
  const a = o.alpha ?? 1;
  ctx.fillStyle = rgba(o.color || C.cyan, a);
  ctx.fillText(str, x, y);
  const w = ctx.measureText(str).width;
  if (a > 0.05 && str.trim()) {
    const x0 = o.align === 'center' ? x - w / 2 : o.align === 'right' ? x - w : x;
    const y0 = (o.baseline || 'middle') === 'middle' ? y - size * 0.5 : (o.baseline === 'top' ? y : y - size * 0.8);
    const m = ctx.getTransform(), s = ctx.__scale || 1;
    const p = (px, py) => [(m.a * px + m.c * py + m.e) / s, (m.b * px + m.d * py + m.f) / s];
    const [ax, ay] = p(x0, y0), [bx, by] = p(x0 + w, y0 + size);
    TEXTS.push({ str, x0: Math.min(ax, bx), y0: Math.min(ay, by), x1: Math.max(ax, bx), y1: Math.max(ay, by) });
  }
  return w;
}
export function measure(ctx, str, size, font = MONO, weight = 400) { ctx.font = `${weight} ${size}px ${font}`; ctx.letterSpacing = '0px'; return ctx.measureText(str).width; }

// draw a polyline up to fraction p of its length
export function poly(ctx, pts, p = 1, close = false) {
  if (p <= 0 || pts.length < 2) return;
  const P = close ? [...pts, pts[0]] : pts;
  let L = 0; const seg = [];
  for (let i = 1; i < P.length; i++) { const d = Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]); seg.push(d); L += d; }
  let left = L * clamp(p);
  ctx.beginPath(); ctx.moveTo(P[0][0], P[0][1]);
  for (let i = 1; i < P.length && left > 0; i++) {
    const d = seg[i - 1];
    if (left >= d) ctx.lineTo(P[i][0], P[i][1]);
    else { const f = left / d; ctx.lineTo(lerp(P[i - 1][0], P[i][0], f), lerp(P[i - 1][1], P[i][1], f)); }
    left -= d;
  }
  ctx.stroke();
}
export function circle(ctx, x, y, r, p = 1, a0 = -Math.PI / 2) { if (p <= 0) return; ctx.beginPath(); ctx.arc(x, y, Math.max(0.1, r), a0, a0 + Math.PI * 2 * clamp(p)); ctx.stroke(); }
export function stroke(ctx, color, a, w) { ctx.strokeStyle = rgba(color, a); ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; }

// thin terminal panel: corner brackets + hairline border + label
export function panel(ctx, x, y, w, h, label, o = {}) {
  const a = o.alpha ?? 1, k = 26;
  stroke(ctx, C.cyan, 0.16 * a, 1.5); ctx.strokeRect(x, y, w, h);
  stroke(ctx, C.cyan, 0.85 * a, 3);
  for (const [cx, cy, sx, sy] of [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]]) {
    ctx.beginPath(); ctx.moveTo(cx + sx * k, cy); ctx.lineTo(cx, cy); ctx.lineTo(cx, cy + sy * k); ctx.stroke();
  }
  if (label) text(ctx, label, x + 14, y + 22, { size: 20, alpha: 0.75 * a, weight: 500 });
  if (o.right) text(ctx, o.right, x + w - 14, y + 22, { size: 20, alpha: 0.75 * a, align: 'right', weight: 500, color: o.rightColor });
}

// typed string: reveal chars between t0 and t1, returns [shown, done]
export function typed(str, lt, t0, t1) { const n = Math.floor(str.length * clamp((lt - t0) / Math.max(0.01, t1 - t0))); return [str.slice(0, n), n >= str.length]; }
export const blink = (t, period = 1.06) => (t % period) < period * 0.55;
export function cursor(ctx, x, y, size, color, a = 1) { ctx.fillStyle = rgba(color, a); ctx.fillRect(x + 4, y - size * 0.42, size * 0.42, size * 0.8); }
