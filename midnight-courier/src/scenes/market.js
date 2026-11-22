// LANTERN MARKET — street-level dolly through glowing stacked stalls. Stalls
// fold up into paper cranes and fly away; the baker waves; finally the whole
// street lifts into the sky.
import { css, mix, shade, clamp, h1, makeCanvas, rng, fract } from '../core/util.js';
import { genCityLayer, bakeLayer } from '../core/citygen.js';
import { drawSky, drawLayer, drawFog, drawShafts } from '../core/stage.js';
import { crane, craneFlock, lanternField, skyLantern, petals } from '../core/sprites.js';
import { stall, makeEnv } from '../core/buildings.js';
import { finishLayer, glowSprite, roughRect, posterV } from '../core/paint.js';
import { win, useLayer, layerSmoke, juno } from './common.js';

export const CAM = { x0: -2200, x1: 2200, y0: -1500, y1: 300 };
const STREET_D = 1.6;
const GROUND = 210; // street level (local y at STREET_D) -> screen y ~1170, above the caption band
const CANAL = 430;

export function build(pal, opts = {}, seed = 31) {
  const L = [];
  L.push(genCityLayer(seed + 1, { d: 7, kind: 'mountains', y: -60, islands: 5, rim: false, shadow: 0.1, laundry: false, grain: 0.3 }, pal, CAM));
  L.push(genCityLayer(seed + 2, {
    d: 4.5, litP: 0.55,
    tiers: [{ y: 60, hMin: 300, hMax: 800, wMin: 110, wMax: 220, gapMax: 10, types: { tenement: 3, canalhouse: 3, pagoda: 2, dome: 1 } }],
  }, pal, CAM));
  // back facades with shops at street level
  L.push(genCityLayer(seed + 3, {
    d: 2.7, litP: 0.6, laundry: true,
    tiers: [{ y: 150, hMin: 700, hMax: 1250, wMin: 160, wMax: 260, gapMin: 0, gapMax: 12, types: { tenement: 4, canalhouse: 4, pagoda: 1.2 } }],
  }, pal, CAM));
  // static back row of stacked stalls on scaffolding
  L.push(genCityLayer(seed + 4, {
    d: 2.0, litP: 0.6, laundry: false,
    tiers: [{ y: 190, hMin: 260, hMax: 460, wMin: 260, wMax: 420, gapMin: 20, gapMax: 70, types: { stalls: 1 }, wall: false }],
  }, pal, CAM));
  // street ground (cobbles + canal edge)
  const gb = { x0: CAM.x0 / STREET_D - 700, x1: CAM.x1 / STREET_D + 700, y0: GROUND - 20, y1: CAM.y1 / STREET_D + 1200 };
  L.push(bakeLayer(STREET_D, gb, pal, (ctx, r, env, b) => {
    const st = mix(pal.near, '#8a7080', 0.22);
    ctx.fillStyle = css(st);
    ctx.fillRect(b.x0, GROUND, b.x1 - b.x0, b.y1 - GROUND);
    posterV(ctx, r, b.x0, GROUND, b.x1 - b.x0, 500, shade(st, 0.18), shade(st, -0.3), 5, 3);
    for (let y = GROUND + 8, row = 0; y < b.y1; y += 16 + row * 2, row++) {
      for (let x = b.x0 + (row % 2) * 14; x < b.x1; x += 28 + row * 3) {
        ctx.fillStyle = css(shade(st, r.range(-0.2, 0.15)), 0.55);
        ctx.beginPath();
        ctx.ellipse(x, y, 12 + row * 1.5, 5 + row * 0.6, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    // canal in the foreground with lantern reflections and gondolas
    const wc = pal.water;
    posterV(ctx, r, b.x0, CANAL, b.x1 - b.x0, b.y1 - CANAL, shade(wc, 0.15), shade(wc, -0.35), 5, 3);
    ctx.fillStyle = css(shade(st, 0.25));
    ctx.fillRect(b.x0, CANAL - 10, b.x1 - b.x0, 14);
    for (let x = b.x0; x < b.x1; x += 60 + r.next() * 80) {
      ctx.fillStyle = css(mix(pal.lamp, '#fff4d0', 0.3), 0.35 + r.next() * 0.25);
      for (let k = 0; k < 6; k++) ctx.fillRect(x + (r.next() - 0.5) * 14, CANAL + 20 + k * 22 + r.next() * 8, 18 + r.next() * 40, 4);
    }
    ctx.strokeStyle = css(shade(wc, 0.45), 0.4);
    ctx.lineWidth = 2;
    for (let i = 0; i < (b.x1 - b.x0) / 20; i++) {
      const xx = b.x0 + r.next() * (b.x1 - b.x0), yy = CANAL + 30 + r.next() * (b.y1 - CANAL);
      ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + 20 + r.next() * 40, yy); ctx.stroke();
    }
    for (let x = b.x0 + 100; x < b.x1; x += 500 + r.next() * 500) {
      const gw = 260, gy = CANAL + 120 + r.next() * 160;
      ctx.fillStyle = css(shade(pal.near, -0.1));
      ctx.beginPath();
      ctx.moveTo(x, gy); ctx.quadraticCurveTo(x + gw / 2, gy + 50, x + gw, gy);
      ctx.lineTo(x + gw + 24, gy - 40); ctx.lineTo(x + gw - 10, gy); ctx.lineTo(x + 10, gy); ctx.lineTo(x - 24, gy - 40);
      ctx.fill();
      ctx.fillStyle = css(mix(pal.lamp, '#fff1c0', 0.3));
      ctx.beginPath(); ctx.ellipse(x + gw * 0.8, gy - 50, 9, 13, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillRect(x + gw * 0.8 - 1, gy - 40, 3, 40);
    }
    // lamp light pools
    ctx.globalCompositeOperation = 'lighter';
    for (let x = b.x0; x < b.x1; x += 300) {
      ctx.globalAlpha = 0.25;
      ctx.drawImage(glowSprite(pal.lamp), x - 200, GROUND - 40, 400, 160);
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }, { seed: seed + 5, rim: false, shadow: 0, s: 1 }));
  L[L.length - 1].ground = true;
  // folding stalls (individual sprites)
  const r = rng(seed + 6);
  const folders = [];
  let x = CAM.x0 / STREET_D - 500;
  const AW = ['#3f9a8e', '#e2b04a', '#6a5aa8', '#4a7ab0', '#d98a4a', '#7aa860'];
  while (x < CAM.x1 / STREET_D + 500) {
    const w = r.range(170, 260), h = r.range(200, 260);
    const c = makeCanvas(w + 60, h + 100);
    const g = c.getContext('2d');
    g.translate(30, h + 60);
    const env = makeEnv(pal, 1, 0.02, 0.8);
    stall(g, r, 0, 0, w, h, env, { awning: AW[folders.length % AW.length] });
    folders.push({ x, w, h, canvas: finishLayer(c, pal, { rimWidth: 4, shadow: 0.5 }), seed: folders.length, baker: folders.length % 5 === 2 });
    x += w + r.range(30, 90);
  }
  return { layers: L, folders, pal };
}

export function render(ctx, f, st) {
  const { cam, fx, pal } = f;
  const L = st.layers;
  drawSky(ctx, f.skyPal || pal, cam, f.pt, { parallax: 40 });
  const gone = fx.streetGone ? win(f.p, fx.streetGone[0], fx.streetGone[1], (x) => x * x) : 0;
  for (let i = 0; i < L.length; i++) {
    let offY = 0, alpha = 1;
    if (gone > 0 && (i === 2 || i === 3)) { offY = -gone * (i === 2 ? 1800 : 1400); alpha = 1 - clamp(gone * 1.3 - 0.2); }
    const { visible } = drawLayer(ctx, L[i], cam, { offY, alpha });
    if (!visible) continue;
    useLayer(ctx, L[i].d, cam, 0, offY);
    if (i === 1) drawFog(ctx, pal, cam, f.pt, { d: 4.5, y: 60, h: 500, alpha: 0.35 });
    if (i === 2) {
      layerSmoke(ctx, L[i], f, 0.4);
      lanternStrings(ctx, L[i], f, 2.7);
      if (gone > 0) {
        useLayer(ctx, 2.4, cam);
        craneFlock(ctx, f.pt, pal, { n: 40, x0: cam.x / 2.4 - 800, x1: cam.x / 2.4 + 800, y: 300 - gone * 900, spread: 1100, speed: 60, size: 50, rise: 1 });
      }
    }
    if (i === 3) {
      useLayer(ctx, 2.3, cam);
      lanternField(ctx, f.pt, pal, { n: 34, x0: cam.x / 2.3 - 700, x1: cam.x / 2.3 + 700, y0: -1100, y1: 500, size: 16, speed: 30 });
    }
  }
  // street level: folding stalls, crowd, baker, Juno
  useLayer(ctx, STREET_D, cam);
  const fold = fx.fold;
  const viewL = cam.x / STREET_D - 800, viewR = cam.x / STREET_D + 800;
  for (const s of st.folders) {
    if (s.x + s.w < viewL - 200 || s.x > viewR + 200) continue;
    let k = 0;
    if (fold) {
      // fold wave sweeps across the street
      const u = (s.x - viewL) / (viewR - viewL);
      const start = fold[0] + (fold[2] === 'rtl' ? 1 - u : u) * (fold[1] - fold[0]) * 0.6;
      k = clamp((f.p - start) / 0.25);
    }
    if (gone > 0) k = Math.max(k, clamp(gone * 2 - h1(s.seed, 4) * 0.6));
    drawFoldingStall(ctx, s, k, f);
  }
  crowd(ctx, f, viewL, viewR, gone);
  if (fx.baker) baker(ctx, fx.baker.x ?? cam.x / STREET_D + 140, GROUND + 4, f, true);
  if (fx.juno) {
    const j = fx.juno;
    const h = j.h || 150;
    const jx = j.x !== undefined ? j.x : cam.x / STREET_D + (j.offset ?? -80);
    juno(ctx, jx, GROUND + 10, h, f, { mode: j.mode || 'run', phase: (jx / (h * 1.15)) * Math.PI * 2, facing: j.facing ?? 1, vx: (j.mode || 'run') === 'run' ? 2.6 * h : 0, wind: 0.5 });
  }
  // foreground hanging lanterns passing by (parallax)
  useLayer(ctx, 1.05, cam);
  for (let i = -4; i < 6; i++) {
    const gx = Math.floor(cam.x / 1.05 / 420) * 420 + i * 420;
    const sway = Math.sin(f.pt * 1.5 + gx) * 8;
    ctx.strokeStyle = css(shade(pal.near, -0.2));
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(gx, -1200);
    ctx.lineTo(gx + sway, -560 + h1(gx, 1) * 140);
    ctx.stroke();
    skyLantern(ctx, gx + sway, -520 + h1(gx, 1) * 140, 34, f.pt, gx, pal);
  }
  useLayer(ctx, 0.9, cam);
  petals(ctx, f.pt, { n: 30, x0: cam.x / 0.9 - 800, x1: cam.x / 0.9 + 800, y0: cam.y / 0.9 - 1200, y1: cam.y / 0.9 + 1200, size: 10 });
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function drawFoldingStall(ctx, s, k, f) {
  const cx = s.x + s.w / 2, by = GROUND + 6;
  if (k <= 0) {
    ctx.drawImage(s.canvas, s.x - 30, by - s.h - 60);
    return;
  }
  if (k < 0.55) {
    // the stall creases and folds up like paper
    const q = k / 0.55;
    ctx.save();
    ctx.translate(cx, by - s.h * 0.5 * q);
    ctx.scale(1 - q * 0.75, 1 - q * 0.8);
    ctx.rotate(Math.sin(q * Math.PI) * 0.25);
    ctx.drawImage(s.canvas, -s.w / 2 - 30, -s.h - 60 + s.h * 0.5 * q);
    // paper fold shading
    ctx.fillStyle = `rgba(250,240,220,${q * 0.7})`;
    ctx.beginPath();
    ctx.moveTo(-s.w / 2, -s.h); ctx.lineTo(0, -s.h * (1 - q)); ctx.lineTo(s.w / 2, -s.h); ctx.lineTo(0, 0);
    ctx.fill();
    ctx.restore();
    return;
  }
  // a paper crane flies away from where the stall stood
  const q = (k - 0.55) / 0.45;
  const fx = cx + q * q * 600 * (h1(s.seed, 2) < 0.5 ? -1 : 1) * 0.6;
  const fy = by - s.h * 0.5 - q * q * 1500;
  crane(ctx, fx, fy, 70 + 40 * (1 - q), f.pt, s.seed, f.pal, h1(s.seed, 2) < 0.5 ? -1 : 1, 0.05);
  // ghost outline of where it was
  ctx.strokeStyle = `rgba(255,240,210,${0.25 * (1 - q)})`;
  ctx.setLineDash([8, 10]);
  ctx.strokeRect(s.x, by - s.h * 0.75, s.w, s.h * 0.75);
  ctx.setLineDash([]);
}

function baker(ctx, x, y, f, wave) {
  const h = 170;
  const body = '#2a2140';
  ctx.save();
  ctx.translate(x, y);
  ctx.lineCap = 'round';
  // round body + apron
  ctx.fillStyle = body;
  ctx.beginPath(); ctx.ellipse(0, -h * 0.38, h * 0.2, h * 0.3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#f2e6d0';
  ctx.beginPath(); ctx.ellipse(h * 0.02, -h * 0.32, h * 0.13, h * 0.22, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = body;
  ctx.lineWidth = h * 0.09;
  ctx.beginPath(); ctx.moveTo(-h * 0.07, -h * 0.12); ctx.lineTo(-h * 0.09, 0); ctx.moveTo(h * 0.07, -h * 0.12); ctx.lineTo(h * 0.09, 0); ctx.stroke();
  // head + chef hat
  ctx.fillStyle = body;
  ctx.beginPath(); ctx.arc(0, -h * 0.74, h * 0.1, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#fff6e6';
  ctx.beginPath(); ctx.ellipse(0, -h * 0.9, h * 0.11, h * 0.08, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillRect(-h * 0.08, -h * 0.88, h * 0.16, h * 0.06);
  // waving arm
  const a = wave ? -2.4 + Math.sin(f.pt * 10) * 0.45 : -0.3;
  ctx.strokeStyle = body;
  ctx.lineWidth = h * 0.07;
  ctx.beginPath();
  ctx.moveTo(h * 0.14, -h * 0.58);
  const ex = h * 0.14 + Math.sin(-a) * h * 0.18, ey = -h * 0.58 - Math.cos(a) * h * 0.18;
  ctx.lineTo(ex, ey);
  ctx.lineTo(ex + Math.sin(-a + 0.4) * h * 0.16, ey - Math.cos(a - 0.4) * h * 0.16);
  ctx.stroke();
  // a loaf in the other hand
  ctx.fillStyle = '#e0a860';
  ctx.beginPath(); ctx.ellipse(-h * 0.22, -h * 0.4, h * 0.1, h * 0.05, -0.4, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
}

function crowd(ctx, f, viewL, viewR, gone) {
  const n = 14;
  for (let i = 0; i < n; i++) {
    const span = viewR - viewL + 400;
    const base = h1(i, 50) * 4000 - 2000;
    const walk = (h1(i, 51) - 0.5) * 70 * f.pt;
    let x = base + walk;
    x = viewL - 200 + (((x - viewL + 200) % span) + span) % span;
    const h = 120 + h1(i, 52) * 50;
    const k = clamp(gone * 2.2 - h1(i, 53));
    if (k >= 1) continue;
    ctx.save();
    ctx.globalAlpha = 1 - k;
    ctx.translate(x, GROUND + 8 - k * 400);
    const bob = Math.abs(Math.sin(f.pt * 6 + i)) * 4;
    ctx.fillStyle = css(mix('#1c1530', f.pal.near, 0.3));
    ctx.beginPath(); ctx.ellipse(0, -h * 0.4 - bob, h * 0.14, h * 0.32, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(0, -h * 0.82 - bob, h * 0.1, 0, Math.PI * 2); ctx.fill();
    if (i % 3 === 0) { ctx.beginPath(); ctx.ellipse(0, -h * 0.9 - bob, h * 0.16, h * 0.04, 0, 0, Math.PI * 2); ctx.fill(); }
    if (i % 4 === 1) skyLantern(ctx, h * 0.25, -h * 0.55 - bob, 12, f.pt, i, f.pal);
    ctx.restore();
  }
}

function lanternStrings(ctx, L, f, d) {
  const tops = L.info.tops.slice().sort((a, b) => a[0] - b[0]);
  for (let i = 0; i < tops.length - 1; i += 1) {
    const a = tops[i], b = tops[i + 1];
    const y0 = Math.max(a[2], b[2]) + 120 + h1(i, 3) * 200;
    const x0 = (a[0] + a[1]) / 2, x1 = (b[0] + b[1]) / 2;
    const sag = 60;
    ctx.strokeStyle = css(shade(f.pal.near, 0.15), 0.7);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.quadraticCurveTo((x0 + x1) / 2, y0 + sag * 2, x1, y0);
    ctx.stroke();
    for (let k = 1; k < 6; k++) {
      const u = k / 6;
      const x = x0 + (x1 - x0) * u, y = y0 + 4 * u * (1 - u) * sag;
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.5 * (0.7 + 0.3 * Math.sin(f.pt * 4 + k + i));
      ctx.drawImage(glowSprite(f.pal.lamp), x - 16, y - 12, 32, 32);
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      ctx.fillStyle = css(mix(f.pal.lamp, '#fff1c0', 0.35));
      ctx.beginPath(); ctx.ellipse(x, y + 5, 5, 7, 0, 0, Math.PI * 2); ctx.fill();
    }
  }
}

export { roughRect, fract, drawShafts };
