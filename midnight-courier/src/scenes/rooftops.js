// ROOFTOPS — rooftop-parallel tracking shots. Juno runs along a dynamic row of
// rooftops (individual sprites, so gaps can close behind her), leaps the
// gaps; the clock tower, the greenhouse bridge and the Spire Library rise in
// the parallax layers behind.
import { W, H, css, mix, shade, clamp, h1, makeCanvas, rng, fract } from '../core/util.js';
import { genCityLayer, bakeLayer } from '../core/citygen.js';
import { drawSky, drawLayer, drawFog } from '../core/stage.js';
import { craneFlock, lanternField, petals, smoke } from '../core/sprites.js';
import { tenement, canalhouse, greenhouse, spireLibrary, clocktower, makeEnv, bridge } from '../core/buildings.js';
import { finishLayer, glowSprite } from '../core/paint.js';
import { win, useLayer, layerSmoke, clockHands, glowPoints, juno } from './common.js';

export const CAM = { x0: -900, x1: 9200, y0: -1500, y1: 500 };
const ROW_D = 1.5;

export function build(pal, opts = {}, seed = 21) {
  const L = [];
  L.push(genCityLayer(seed + 1, { d: 8, kind: 'mountains', y: 120, islands: 6, rim: false, shadow: 0.12, laundry: false, grain: 0.3 }, pal, CAM));
  L.push(genCityLayer(seed + 2, {
    d: 5.5, litP: 0.5,
    tiers: [{ y: 220, hMin: 160, hMax: 560, wMin: 100, wMax: 220, gapMax: 14, types: { tenement: 3, dome: 2, pagoda: 2, canalhouse: 2 } }],
    landmarks: [{ type: 'dome', x: 300, w: 520, h: 900, tier: 0 }],
  }, pal, CAM));
  // the Spire Library, on its own layer so it can rise
  const libB = { x0: 900, x1: 2000, y0: -1900, y1: 1400 };
  L.push(bakeLayer(4.4, libB, pal, (ctx, r, env) => {
    spireLibrary(ctx, r, 1250, 520, 300, 2100, env);
  }, { seed: seed + 3, s: 0.6, depthT: 0.32, litP: 0.85 }));
  L[2].isLibrary = true;
  L.push(genCityLayer(seed + 4, {
    d: 3.4, litP: 0.5,
    tiers: [{ y: 300, canal: 100, hMin: 220, hMax: 600, bridgeP: 0.25, types: { tenement: 3, canalhouse: 2, pagoda: 1.6, greenhouse: 1, dome: 1 } }],
    landmarks: [{ type: 'clocktower', x: 420, w: 300, h: 2300, tier: 0 }],
  }, pal, CAM));
  // near-mid: city + the greenhouse bridge
  const mid = genCityLayer(seed + 5, {
    d: 2.2, litP: 0.45,
    tiers: [{ y: 640, hMin: 260, hMax: 700, bridgeP: 0.2, types: { tenement: 4, canalhouse: 3, pagoda: 1, greenhouse: 1 } }],
  }, pal, CAM);
  L.push(mid);
  const gh = greenhouseBridge(pal, seed + 6);
  // rooftop sprites for the running row
  const row = [];
  const r = rng(seed + 7);
  let x = -700;
  while (x < CAM.x1 / ROW_D + 900) {
    const w = r.range(260, 440);
    const top = r.range(60, 190);
    const spr = roofSprite(pal, r, w);
    const gap = row.length % 3 === 2 ? 0 : r.range(70, 150);
    row.push({ x, w, top, spr, gap });
    x += w + gap;
  }
  return { layers: L, row, gh, pal };
}

// Sprite whose flat roof sits at sprite-local y = 0 (canvas y = 200).
function roofSprite(pal, r, w) {
  const H2 = 1300;
  const c = makeCanvas(w + 80, H2 + 200);
  const g = c.getContext('2d');
  g.translate(40, 200);
  const env = makeEnv(pal, 1.0, 0.04, 0.4);
  tenement(g, r, 0, H2, w, H2, env);
  const out = finishLayer(c, pal, { rimWidth: 5, shadow: 0.55, shadowBlur: 26 });
  return { canvas: out, smoke: env.info.chimneys };
}

function greenhouseBridge(pal, seed) {
  const r = rng(seed);
  const c = makeCanvas(1500, 1500);
  const g = c.getContext('2d');
  const env = makeEnv(pal, 0.7, 0.18, 0.6);
  // two towers
  tenement(g, r, 40, 1500, 240, 1150, env);
  tenement(g, r, 1220, 1500, 240, 1250, env);
  // the glass bridge: long greenhouse tube between them
  const y = 520;
  g.save();
  greenhouse(g, r, 270, y + 120, 960, 300, env);
  g.restore();
  bridge(g, r, 270, 1230, y + 128, env, { archH: 120 });
  return { canvas: finishLayer(c, pal, { rimWidth: 4, shadow: 0.45 }), w: 1500, h: 1500 };
}

// Juno's local x on the row for this frame
function junoX(f, j, st) {
  if (j.x !== undefined) {
    let best = st.row[0], bd = 1e9;
    for (const b of st.row) { const c = b.x + b.w / 2; if (Math.abs(c - j.x) < bd) { bd = Math.abs(c - j.x); best = b; } }
    return best.x + best.w * (j.u ?? 0.45);
  }
  return f.cam.x / ROW_D + (j.offset ?? -120);
}

function rowLayout(st, jx) {
  // gaps close behind Juno: the building left of a gap slides right to meet
  // the next one once she has crossed.
  const out = [];
  for (let i = 0; i < st.row.length; i++) {
    const b = st.row[i];
    let dx = 0;
    if (b.gap > 0) {
      const gapEnd = b.x + b.w + b.gap;
      const k = clamp((jx - gapEnd - 60) / 260);
      dx = b.gap * k * k * (3 - 2 * k);
    }
    out.push({ ...b, dx });
  }
  return out;
}

function roofY(layout, x) {
  for (const b of layout) if (x >= b.x + b.dx && x <= b.x + b.dx + b.w) return b.top;
  return null;
}

function junoY(layout, x, h) {
  // inside a building span -> roof; inside a gap -> parabolic leap
  for (let i = 0; i < layout.length; i++) {
    const b = layout[i];
    const x0 = b.x + b.dx, x1 = x0 + b.w;
    if (x >= x0 && x <= x1) {
      // take-off ramp: start the leap a little before the edge
      const nb = layout[i + 1];
      if (nb && b.gap > 0 && x > x1 - 50) return leap(b, nb, x, h, x1 - 50);
      const pb = layout[i - 1];
      if (pb && pb.gap > 0 && x < x0 + 40) return leap(pb, b, x, h, pb.x + pb.dx + pb.w - 50);
      return { y: b.top, air: false };
    }
    const nb = layout[i + 1];
    if (nb && x > x1 && x < nb.x + nb.dx) return leap(b, nb, x, h, x1 - 50);
  }
  return { y: 150, air: false };
}

function leap(a, b, x, h, start) {
  const end = b.x + b.dx + 40;
  const u = clamp((x - start) / (end - start));
  const y = a.top + (b.top - a.top) * u - Math.sin(u * Math.PI) * h * 1.1;
  return { y, air: u > 0.02 && u < 0.98, u };
}

export function render(ctx, f, st) {
  const { cam, fx, pal } = f;
  const L = st.layers;
  drawSky(ctx, f.skyPal || pal, cam, f.pt, { parallax: 34 });
  for (let i = 0; i < L.length; i++) {
    const lib = L[i].isLibrary;
    let offY = 0;
    if (lib && fx.libRise) offY = fx.libRise[0] + (fx.libRise[1] - fx.libRise[0]) * win(f.p, 0, 1);
    const { visible } = drawLayer(ctx, L[i], cam, { offY });
    if (!visible) continue;
    useLayer(ctx, L[i].d, cam, 0, offY);
    if (lib) glowPoints(ctx, L[i], f, 1.5);
    if (i === 1) drawFog(ctx, pal, cam, f.pt, { d: 5.5, y: 220, h: 480, alpha: 0.35 });
    if (i === 3) {
      clockHands(ctx, L[i], f, fx.clock);
      layerSmoke(ctx, L[i], f, 0.35);
      useLayer(ctx, 3.0, cam);
      lanternField(ctx, f.pt, pal, { n: 30, x0: cam.x / 3 - 900, x1: cam.x / 3 + 900, y0: -1300, y1: 500, size: 14, speed: 24 });
    }
    if (i === 4) {
      // greenhouse bridge lives at world x ~ 3500 * 2.2
      ctx.drawImage(st.gh.canvas, fx.ghX ?? 2450, -560, st.gh.w * 0.72, st.gh.h * 0.72);
      layerSmoke(ctx, L[i], f, 0.4);
      drawFog(ctx, pal, cam, f.pt, { d: 2.2, y: 700, h: 420, alpha: 0.28 });
      useLayer(ctx, 1.9, cam);
      craneFlock(ctx, f.pt, pal, { n: 9, x0: cam.x / 1.9 - 900, x1: cam.x / 1.9 + 900, y: -380, spread: 400, speed: 140, size: 44 });
    }
  }
  // the running row
  useLayer(ctx, ROW_D, cam);
  const j = fx.juno || { offset: -120 };
  const jx = junoX(f, j, st);
  const layout = rowLayout(st, jx);
  const viewL = cam.x / ROW_D - 900, viewR = cam.x / ROW_D + 900;
  // string lights between neighbours
  for (let i = 0; i < layout.length - 1; i++) {
    const a = layout[i], b = layout[i + 1];
    if (a.x + a.dx + a.w < viewL - 200 || a.x > viewR + 200) continue;
    stringLights(ctx, a.x + a.dx + a.w - 10, a.top - 40, b.x + b.dx + 10, b.top - 50, pal, f.pt, i);
  }
  for (const b of layout) {
    if (b.x + b.dx + b.w < viewL - 100 || b.x + b.dx > viewR + 100) continue;
    ctx.drawImage(b.spr.canvas, b.x + b.dx - 40, b.top - 200);
    if (b.dx > 0.5 && b.dx < b.gap - 0.5) dust(ctx, b.x + b.dx + b.w, b.top + 40, f.pt);
    smoke(ctx, b.spr.smoke.map(([x, y, s]) => [x + b.x + b.dx, y + b.top, s]), f.pt, pal, { alpha: 0.45, max: 4 });
  }
  // Juno
  const h = j.h || 132;
  const jy = junoY(layout, jx, h);
  const mode = j.mode || 'run';
  const runPhase = (jx / (h * 1.15)) * Math.PI * 2;
  const speed = (j.speed ?? 2.4) * h;
  juno(ctx, jx, jy.y, h, f, {
    mode: mode === 'run' ? (jy.air ? 'jump' : 'run') : mode,
    phase: runPhase,
    facing: j.facing ?? 1,
    vx: mode === 'run' ? speed : 0,
    vy: 0,
    reach: j.reach !== undefined ? win(f.p, j.reach[0], j.reach[1]) : undefined,
    letter: j.letter && (!j.letterAt || f.p > j.letterAt),
    wind: mode === 'run' ? 0.4 : 1.4,
  });
  // foreground petals / paper scraps
  useLayer(ctx, 0.95, cam);
  petals(ctx, f.pt, { n: 26, x0: cam.x / 0.95 - 800, x1: cam.x / 0.95 + 800, y0: cam.y / 0.95 - 1200, y1: cam.y / 0.95 + 1200, size: 11, wind: 160 });
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function stringLights(ctx, x0, y0, x1, y1, pal, t, seed) {
  const sag = 50;
  ctx.strokeStyle = css(shade(pal.near, 0.2), 0.8);
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.quadraticCurveTo((x0 + x1) / 2, (y0 + y1) / 2 + sag * 2, x1, y1);
  ctx.stroke();
  const n = Math.max(3, Math.floor((x1 - x0) / 34));
  for (let k = 1; k < n; k++) {
    const u = k / n;
    const x = (1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * ((x0 + x1) / 2) + u * u * x1;
    const y = (1 - u) * (1 - u) * y0 + 2 * (1 - u) * u * ((y0 + y1) / 2 + sag * 2) + u * u * y1;
    const fl = 0.7 + 0.3 * Math.sin(t * 5 + k * 1.7 + seed);
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.45 * fl;
    ctx.drawImage(glowSprite(pal.lamp), x - 18, y - 14, 36, 36);
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.fillStyle = css(mix(pal.lamp, '#fff4c8', 0.4));
    ctx.beginPath(); ctx.arc(x, y + 4, 4, 0, Math.PI * 2); ctx.fill();
  }
}

function dust(ctx, x, y, t) {
  for (let k = 0; k < 6; k++) {
    const a = fract(t * 1.7 + k / 6);
    ctx.fillStyle = `rgba(235,220,240,${(1 - a) * 0.35})`;
    ctx.beginPath();
    ctx.arc(x + (h1(k, 3) - 0.5) * 30, y - a * 90 + k * 30, 10 + a * 30, 0, Math.PI * 2);
    ctx.fill();
  }
}
