// Colour script. Every palette is free of saturated red: the only red in the
// film is Juno's scarf (SCARF below).
import { mix, hex } from './util.js';

export const SCARF = { main: '#e0313f', dark: '#8e1424', light: '#ff6b5e' };
export const GOLD = '#ffc43d';

export const PALETTES = {
  // B0/B1 — dusk peach / violet
  dusk: {
    sky: ['#2c2160', '#5d3b86', '#a6589a', '#e98a8f', '#ffc79a'],
    sun: { color: '#fff0c8', glow: '#ffb27a', x: 0.72, y: 0.58, r: 120, kind: 'sun' },
    haze: '#e59c9a', fog: '#f4b3a0', far: '#a47aa6', near: '#2a1a3e', rim: '#ffd3a3',
    window: '#ffd27a', lamp: '#ffc24a', water: '#5a4a8c',
    paints: ['#7a4f86', '#94607a', '#5c5b8e', '#86687a', '#6b6e9a', '#a07a6e'],
    roof: ['#3e3462', '#4f3c6a', '#2f4a62', '#5a4560'], copper: ['#4f9a8a', '#7cc0a4', '#2f6d6a'],
    stars: 0.15, light: [0.8, -0.6], cloud: '#f3a6a0',
  },
  // B2 — violet dusk turning to night, market glow
  violet: {
    sky: ['#1a1446', '#33276c', '#5b3d8a', '#8d5a9a', '#c98aa4'],
    sun: { color: '#ffe9c4', glow: '#c77fb0', x: 0.25, y: 0.3, r: 70, kind: 'moon' },
    haze: '#7c5c9c', fog: '#9a72b0', far: '#6e5a96', near: '#1a1232', rim: '#ffcf8a',
    window: '#ffc860', lamp: '#ffb83a', water: '#3a3478',
    paints: ['#5b4380', '#6e4a72', '#41477e', '#6a5878', '#4f5a86', '#7a5a68'],
    roof: ['#2e2752', '#3a2c58', '#243a56', '#46385a'], copper: ['#3f8a80', '#69b09a', '#285f5e'],
    stars: 0.5, light: [-0.7, -0.7], cloud: '#8e6aa8',
  },
  // B3–B5 — midnight indigo with gold lamp light
  midnight: {
    sky: ['#070a26', '#121a4a', '#1f2a68', '#2e3c82', '#45509a'],
    sun: { color: '#f4f1ff', glow: '#7f8fe0', x: 0.78, y: 0.2, r: 85, kind: 'moon' },
    haze: '#34418a', fog: '#4a58a0', far: '#36407c', near: '#0a0b22', rim: '#9fb4ff',
    window: '#ffc552', lamp: '#ffb02e', water: '#1e2a66',
    paints: ['#2c3466', '#35305e', '#263c66', '#3c3a64', '#2a4060', '#433a5c'],
    roof: ['#1c2048', '#241f46', '#16304a', '#2a2848'], copper: ['#2f7f7a', '#57a89a', '#1d5656'],
    stars: 1, light: [0.6, -0.8], cloud: '#3a4890',
  },
  // B6–B8 — pre-dawn rose / teal
  predawn: {
    sky: ['#1b2a4e', '#2f557a', '#5f9aa2', '#d99aa6', '#ffcdbb'],
    sun: { color: '#fff4e0', glow: '#ffb2a8', x: 0.5, y: 0.86, r: 160, kind: 'dawn' },
    haze: '#c79aaa', fog: '#e8b2b4', far: '#7d93a6', near: '#16203a', rim: '#ffc9bd',
    window: '#ffd89a', lamp: '#ffc46a', water: '#3e6f86',
    paints: ['#4f6a86', '#6a6082', '#3f7886', '#7a6a80', '#4a6f7e', '#8a7280'],
    roof: ['#2a3c5a', '#3a3a5c', '#22485a', '#45405e'], copper: ['#4fb0a4', '#86d4c0', '#2f7a7a'],
    stars: 0.05, light: [0.0, -1], cloud: '#f2b8b8',
  },
};

export function getPalette(name) {
  return PALETTES[name] || PALETTES.midnight;
}

// Blend two palettes (used for the sky, which is redrawn every frame so the
// dawn can creep in mid-shot).
export function lerpPalette(a, b, t) {
  if (t <= 0) return a;
  if (t >= 1) return b;
  const out = { ...a };
  for (const k of ['haze', 'fog', 'far', 'near', 'rim', 'window', 'lamp', 'water', 'cloud']) out[k] = mix(a[k], b[k], t);
  out.sky = a.sky.map((c, i) => mix(c, b.sky[i], t));
  out.sun = { ...a.sun, color: mix(a.sun.color, b.sun.color, t), glow: mix(a.sun.glow, b.sun.glow, t),
    x: a.sun.x + (b.sun.x - a.sun.x) * t, y: a.sun.y + (b.sun.y - a.sun.y) * t, r: a.sun.r + (b.sun.r - a.sun.r) * t,
    kind: t < 0.5 ? a.sun.kind : b.sun.kind };
  out.stars = a.stars + (b.stars - a.stars) * t;
  return out;
}

export function rgbArr(c) { return hex(c); }
