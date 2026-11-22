// Deterministic helpers: seeded RNG, hashing, value noise, colour math.
export const W = 1080;
export const H = 1920;

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function hashStr(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

export function rng(seed) {
  const r = mulberry32(typeof seed === 'string' ? hashStr(seed) : seed);
  const api = {
    next: r,
    range: (a, b) => a + (b - a) * r(),
    int: (a, b) => Math.floor(a + (b - a + 1) * r()),
    pick: (arr) => arr[Math.floor(r() * arr.length) % arr.length],
    chance: (p) => r() < p,
    weighted(obj) {
      const entries = Object.entries(obj); let tot = 0;
      for (const [, w] of entries) tot += w;
      let x = r() * tot;
      for (const [k, w] of entries) { if ((x -= w) <= 0) return k; }
      return entries[entries.length - 1][0];
    },
  };
  return api;
}

// integer hash -> [0,1)
export function h1(n, seed = 0) {
  let x = (Math.imul(n | 0, 374761393) + Math.imul(seed | 0, 668265263)) | 0;
  x = Math.imul(x ^ (x >>> 13), 1274126177);
  x ^= x >>> 16;
  return (x >>> 0) / 4294967296;
}

export function noise1(x, seed = 0) {
  const i = Math.floor(x), f = x - i;
  const u = f * f * (3 - 2 * f);
  return h1(i, seed) * (1 - u) + h1(i + 1, seed) * u;
}

export function fbm1(x, seed = 0, oct = 3) {
  let a = 0, amp = 0.5, fr = 1, n = 0;
  for (let o = 0; o < oct; o++) { a += amp * noise1(x * fr, seed + o * 17); n += amp; amp *= 0.5; fr *= 2.03; }
  return a / n;
}

export const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
export const fract = (x) => x - Math.floor(x);

// ---------- colour ----------
const hexCache = new Map();
export function hex(h) {
  if (Array.isArray(h)) return h;
  let c = hexCache.get(h);
  if (c) return c;
  let s = h.replace('#', '');
  if (s.length === 3) s = s.split('').map((ch) => ch + ch).join('');
  const n = parseInt(s, 16);
  c = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  hexCache.set(h, c);
  return c;
}
export function mix(a, b, t) {
  const A = hex(a), B = hex(b);
  return [A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t];
}
export function css(c, a = 1) {
  const C = hex(c);
  return `rgba(${C[0] | 0},${C[1] | 0},${C[2] | 0},${a})`;
}
export function shade(c, k) {
  return k >= 0 ? mix(c, [255, 255, 255], k) : mix(c, [0, 0, 0], -k);
}
export function sampleStops(stops, t) {
  t = clamp(t) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(t));
  return mix(stops[i], stops[i + 1], t - i);
}

export function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return c;
}
