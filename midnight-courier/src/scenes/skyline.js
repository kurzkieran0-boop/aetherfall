// SKYLINE — the vertical, layered city of rooftops and canals.
// Used for flyovers, tilt-ups along towers, whip pans, push-ins, and the
// "city rearranges" effects (layers sliding apart, a walking tower, a bridge
// unfolding, the tram line unfolding, every window lighting / turning to look).
import { W, H, css, mix, shade, clamp, h1, makeCanvas, rng } from '../core/util.js';
import { genCityLayer } from '../core/citygen.js';
import { drawSky, drawLayer, drawFog, drawShafts, layerXf } from '../core/stage.js';
import { craneFlock, lanternField, petals, tram } from '../core/sprites.js';
import { pagoda, clocktower, makeEnv, bridge } from '../core/buildings.js';
import { finishLayer, glowSprite } from '../core/paint.js';
import { win, useLayer, layerSmoke, clockHands, glowPoints, windowEyes, juno, nearestRoof } from './common.js';

export const CAM = { x0: -1950, x1: 1950, y0: -2100, y1: 760 };

export function build(pal, opts = {}, seed = 1) {
  const lit = !!opts.lit;
  const L = [];
  L.push(genCityLayer(seed + 1, { d: 8, kind: 'mountains', y: 160, islands: 7, rim: false, shadow: 0.12, laundry: false, grain: 0.3 }, pal, CAM));
  L.push(genCityLayer(seed + 2, {
    d: 5.5, litP: 0.5, litVariant: lit,
    tiers: [{ y: 250, hMin: 150, hMax: 520, wMin: 100, wMax: 210, gapMax: 16, types: { tenement: 3, dome: 2, pagoda: 2, canalhouse: 2 } }],
    landmarks: [{ type: 'spireLibrary', x: 320, w: 340, h: 4700, tier: 0 }, { type: 'dome', x: -700, w: 520, h: 900, tier: 0 }],
  }, pal, CAM));
  L.push(genCityLayer(seed + 3, {
    d: 3.8, litP: 0.48, litVariant: lit, tram: { y: -250 },
    tiers: [
      { y: 70, hMin: 200, hMax: 560, types: { tenement: 3, canalhouse: 2, pagoda: 1.5, dome: 1, greenhouse: 0.8 } },
      { y: 380, canal: 110, hMin: 200, hMax: 480, bridgeP: 0.3 },
    ],
    landmarks: [{ type: 'clocktower', x: -430, w: 240, h: 2200, tier: 0 }, { type: 'pagoda', x: 900, w: 300, h: 1100, tier: 0 }],
  }, pal, CAM));
  L.push(genCityLayer(seed + 4, {
    d: 2.6, litP: 0.45, litVariant: lit,
    tiers: [{ y: 540, canal: 140, hMin: 260, hMax: 660, bridgeP: 0.22, types: { tenement: 4, canalhouse: 3, greenhouse: 1.2, pagoda: 1.1, dome: 0.6 } }],
  }, pal, CAM));
  L.push(genCityLayer(seed + 5, {
    d: 1.8, litP: 0.42, litVariant: lit,
    tiers: [{ y: 780, hMin: 300, hMax: 740, gapMin: 10, gapMax: 70, types: { tenement: 5, canalhouse: 3, pagoda: 1 } }],
  }, pal, CAM));
  L.push(genCityLayer(seed + 6, {
    d: 1.35, litP: 0.4, litVariant: lit,
    tiers: [{ y: 1080, hMin: 380, hMax: 740, wMin: 220, wMax: 380, gapMin: 30, gapMax: 170, types: { tenement: 6, canalhouse: 2 } }],
  }, pal, CAM));
  const st = { layers: L, pal };
  if (opts.walkingTower) st.tower = towerSprite(pal, seed);
  return st;
}

function towerSprite(pal, seed) {
  const r = rng(seed + 50);
  const c = makeCanvas(420, 1000);
  const g = c.getContext('2d');
  g.translate(60, 960);
  const env = makeEnv(pal, 0.75, 0.12, 0.7);
  pagoda(g, r, 0, 0, 300, 760, env);
  return finishLayer(c, pal, { rimWidth: 4, shadow: 0.4 });
}

export function render(ctx, f, st) {
  const { cam, fx } = f;
  const pal = f.pal;
  const L = st.layers;
  drawSky(ctx, f.skyPal || pal, cam, f.pt);
  if (fx.shafts) {
    const s = (f.skyPal || pal).sun;
    drawShafts(ctx, s.glow, s.x * W, s.y * H, f.pt, { alpha: 0.08, n: 6, angle: Math.PI * 0.62, spread: 0.18 });
  }
  const shift = (i) => {
    let dx = 0, dy = 0;
    for (const s of fx.shift || []) if (s[0] === i) { const k = win(f.p, s[3] ?? 0, s[4] ?? 1); dx += s[1] * k; dy += s[2] * k; }
    return [dx, dy];
  };
  const litAmt = fx.lit ? win(f.p, fx.lit[0], fx.lit[1], (x) => (x > 0 ? 1 : 0) * Math.min(1, x * 8)) : 0;
  for (let i = 0; i < L.length; i++) {
    const [dx, dy] = shift(i);
    const { visible } = drawLayer(ctx, L[i], cam, { offX: dx, offY: dy, lit: litAmt });
    if (!visible) continue;
    useLayer(ctx, L[i].d, cam, dx, dy);
    if (i === 1) {
      glowPoints(ctx, L[i], f, 1.2);
      drawFog(ctx, pal, cam, f.pt, { d: 5.5, y: 250, h: 520, alpha: 0.38 });
    }
    if (i === 2) {
      clockHands(ctx, L[i], f, fx.clock);
      if (L[i].info.tram && !fx.noTram) {
        const tr = L[i].info.tram;
        const x = tr.x0 + ((f.pt * 260 + 400) % (tr.x1 - tr.x0));
        tram(ctx, x, tr.y - 2, L[i].s * 1.2, pal, f.pt);
      }
      useLayer(ctx, 3.1, cam);
      if (!fx.noLanterns) lanternField(ctx, f.pt, pal, { n: 26, x0: -1300, x1: 1300, y0: -1500, y1: 500, size: 15, speed: 26 });
    }
    if (i === 3) {
      layerSmoke(ctx, L[i], f, 0.4);
      if (fx.walkingTower && st.tower) walkingTower(ctx, f, st, fx.walkingTower);
      if (fx.bridgeOpen) openingBridge(ctx, f, L[i], fx.bridgeOpen);
      if (fx.tramUnfold) unfoldingRail(ctx, f, L[i], fx.tramUnfold);
      drawFog(ctx, pal, cam, f.pt, { d: 2.6, y: 560, h: 420, alpha: 0.3 });
      useLayer(ctx, 2.2, cam);
      if (!fx.noCranes) craneFlock(ctx, f.pt, pal, { n: fx.cranes ?? 12, x0: -1400, x1: 1400, y: -350, spread: 600, speed: 110, size: 46 });
    }
    if (i === 4) layerSmoke(ctx, L[i], f, 0.45);
    if (i >= 3 && fx.eyes) {
      useLayer(ctx, L[i].d, cam, dx, dy);
      windowEyes(ctx, L[i], f, win(f.p, fx.eyes[0], fx.eyes[1]), win(f.p, fx.eyes[1], fx.eyes[2] ?? 1));
    }
    if (i === 4 && fx.mapLines) mapLines(ctx, f, L[i]);
    if (i === 5) {
      layerSmoke(ctx, L[i], f, 0.5);
      if (fx.juno) placeJuno(ctx, f, L[i], fx.juno);
    }
  }
  if (!fx.noPetals) {
    useLayer(ctx, 0.95, cam);
    petals(ctx, f.pt, { n: 34, x0: cam.x / 0.95 - 800, x1: cam.x / 0.95 + 800, y0: cam.y / 0.95 - 1200, y1: cam.y / 0.95 + 1200, size: 10, color: '#f8d4dc' });
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function placeJuno(ctx, f, L, j) {
  const roof = nearestRoof(L, j.x ?? 0, 120);
  if (!roof) return;
  const x = clamp(j.x ?? (roof[0] + roof[1]) / 2, roof[0] + 20, roof[1] - 20);
  juno(ctx, x, roof[2], j.h || 120, f, { mode: j.mode || 'stand', facing: j.facing ?? 1, letter: j.letter, wind: 1.6 });
}

function walkingTower(ctx, f, st, o) {
  const p = f.p;
  const x = o.x0 + (o.x1 - o.x0) * p;
  const by = o.y ?? 520;
  const k = o.scale ?? 0.6;
  const step = f.pt * 3.2;
  const bob = Math.abs(Math.sin(step)) * 22 * k;
  const img = st.tower;
  // mechanical legs
  ctx.strokeStyle = css(shade(f.pal.near, 0.1));
  ctx.lineCap = 'round';
  for (let i = 0; i < 2; i++) {
    const ph = step + i * Math.PI;
    const hipX = x + (i ? 70 : -70) * k, hipY = by - 120 * k - bob;
    const footX = hipX + Math.sin(ph) * 60 * k, footY = by - Math.max(0, Math.cos(ph)) * 40 * k;
    ctx.lineWidth = 16 * k;
    ctx.beginPath(); ctx.moveTo(hipX, hipY); ctx.lineTo((hipX + footX) / 2 + 26 * k, (hipY + footY) / 2); ctx.lineTo(footX, footY); ctx.stroke();
    ctx.fillStyle = css(shade(f.pal.near, 0.2));
    ctx.fillRect(footX - 22 * k, footY - 8 * k, 44 * k, 10 * k);
  }
  ctx.drawImage(img, x - (img.width / 2) * k + 10 * k, by - 120 * k - bob - (img.height - 40) * k, img.width * k, img.height * k);
}

function openingBridge(ctx, f, L, o) {
  const s = L.s;
  const k = win(f.p, o.a ?? 0.1, o.b ?? 0.8);
  const ang = (1 - k) * -1.25; // leaves rise from raised (-72deg) to flat
  const env = { s, pal: f.pal, fade: (c) => mix(c, f.pal.haze, L.depthT * 0.6), info: { lanterns: [] } };
  const leaf = o.w / 2;
  for (const side of [-1, 1]) {
    ctx.save();
    ctx.translate(o.x + side * leaf, o.y);
    ctx.rotate(side * -ang);
    ctx.fillStyle = css(env.fade(shade(f.pal.near, 0.1)));
    ctx.fillRect(side > 0 ? -leaf : 0, -10 * s, leaf, 16 * s);
    ctx.strokeStyle = css(env.fade(shade(f.pal.near, 0.15)));
    ctx.lineWidth = 3 * s;
    ctx.beginPath();
    for (let xx = 0; xx <= leaf; xx += 22 * s) {
      const X = side > 0 ? -xx : xx;
      ctx.moveTo(X, -10 * s); ctx.lineTo(X + (side > 0 ? -11 : 11) * s, -40 * s);
    }
    ctx.moveTo(0, -40 * s); ctx.lineTo(side > 0 ? -leaf : leaf, -40 * s);
    ctx.stroke();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.7;
    const lx = side > 0 ? -leaf * 0.5 : leaf * 0.5;
    ctx.drawImage(glowSprite(f.pal.lamp), lx - 30 * s, -80 * s, 60 * s, 60 * s);
    ctx.restore();
  }
  // towers
  ctx.fillStyle = css(env.fade(shade(f.pal.near, 0.05)));
  ctx.fillRect(o.x - leaf - 40 * s, o.y - 160 * s, 40 * s, 900 * s);
  ctx.fillRect(o.x + leaf, o.y - 160 * s, 40 * s, 900 * s);
  ctx.fillStyle = css(env.fade(pal(f).copper[0]));
  for (const xx of [o.x - leaf - 40 * s, o.x + leaf]) {
    ctx.beginPath(); ctx.moveTo(xx - 6 * s, o.y - 160 * s); ctx.lineTo(xx + 20 * s, o.y - 210 * s); ctx.lineTo(xx + 46 * s, o.y - 160 * s); ctx.fill();
  }
}
const pal = (f) => f.pal;

function unfoldingRail(ctx, f, L, o) {
  const s = L.s;
  const n = o.n || 14;
  const seg = o.seg || 120;
  const front = win(f.p, o.a ?? 0, o.b ?? 0.7, (x) => x) * n;
  ctx.strokeStyle = css(mix(f.pal.near, f.pal.haze, L.depthT * 0.5));
  for (let i = 0; i < n; i++) {
    const k = clamp(front - i);
    if (k <= 0) break;
    const ang = (1 - k) * -1.5;
    const x0 = o.x + i * seg;
    ctx.save();
    ctx.translate(x0, o.y);
    ctx.rotate(ang);
    ctx.lineWidth = 6 * s;
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(seg, 0); ctx.stroke();
    ctx.lineWidth = 2 * s;
    ctx.beginPath();
    for (let x = 0; x < seg; x += 14 * s) { ctx.moveTo(x, 0); ctx.lineTo(x + 7 * s, 10 * s); }
    ctx.moveTo(0, 10 * s); ctx.lineTo(seg, 10 * s);
    ctx.stroke();
    ctx.restore();
    ctx.lineWidth = 4 * s;
    ctx.beginPath(); ctx.moveTo(x0, o.y + 10 * s); ctx.lineTo(x0, o.y + 10 * s + 500 * s * k); ctx.stroke();
  }
  const tx = o.x + Math.max(0, front - 1.6) * seg;
  if (front > 1.6) tram(ctx, tx, o.y - 2, s * 1.1, f.pal, f.pt);
}

function mapLines(ctx, f, L) {
  const tops = L.info.roofs.slice().sort((a, b) => a[0] - b[0]);
  const k = win(f.p, 0.05, 0.85);
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.setLineDash([18, 16]);
  ctx.lineDashOffset = -f.pt * 60;
  for (let route = 0; route < 3; route++) {
    const pts = tops.filter((_, i) => i % 3 === route).map((r) => [(r[0] + r[1]) / 2, r[2] - 30 - route * 40]);
    if (pts.length < 2) continue;
    const total = Math.floor(pts.length * k);
    ctx.strokeStyle = route === 0 ? '#ffd45c' : 'rgba(255,212,92,0.55)';
    ctx.lineWidth = route === 0 ? 7 : 4;
    ctx.shadowColor = 'rgba(255,200,80,0.9)';
    ctx.shadowBlur = 18;
    ctx.beginPath();
    for (let i = 0; i <= total && i < pts.length; i++) {
      const [x, y] = pts[i];
      if (i === 0) ctx.moveTo(x, y);
      else ctx.quadraticCurveTo((pts[i - 1][0] + x) / 2, Math.min(pts[i - 1][1], y) - 90, x, y);
    }
    ctx.stroke();
    if (total > 0 && total < pts.length) {
      const [x, y] = pts[total];
      ctx.setLineDash([]);
      ctx.fillStyle = '#ffd45c';
      ctx.beginPath(); ctx.arc(x, y, 12 + Math.sin(f.t * 10) * 3, 0, Math.PI * 2); ctx.fill();
      ctx.setLineDash([18, 16]);
    }
  }
  ctx.restore();
}

export { layerXf, h1 };
