// Generates one depth layer of the vertical city as a baked texture.
// Layer-local coordinates: (0,0) is the screen centre when the camera sits at
// the origin. A texture only covers what the scene's camera range can reveal.
import { W, H, rng, makeCanvas, css, mix, shade, clamp, fbm1 } from './util.js';
import { makeEnv, BUILDERS, terrace, canal, bridge, laundry, drawWindow } from './buildings.js';
import { finishLayer, roughPath, posterV, glowSprite } from './paint.js';

export function layerBounds(d, cam, margin = 140) {
  return {
    x0: Math.floor(cam.x0 / d - W / 2 - margin),
    x1: Math.ceil(cam.x1 / d + W / 2 + margin),
    y0: Math.floor(cam.y0 / d - H / 2 - margin),
    y1: Math.ceil(cam.y1 / d + H / 2 + margin),
  };
}

const DEFAULT_TYPES = { tenement: 5, canalhouse: 3, pagoda: 1.2, greenhouse: 1, dome: 1 };

export function genCityLayer(seed, spec, pal, camRange) {
  const d = spec.d;
  const b = spec.bounds || layerBounds(d, camRange, spec.margin);
  const cw = b.x1 - b.x0, ch = b.y1 - b.y0;
  const canvas = makeCanvas(cw, ch);
  const ctx = canvas.getContext('2d');
  ctx.translate(-b.x0, -b.y0);
  const r = rng(seed);
  const depthT = spec.depthT !== undefined ? spec.depthT : clamp((d - 1) / 8);
  const s = spec.s || clamp(1.45 / d, 0.22, 1.25);
  const env = makeEnv(pal, s, depthT, spec.litP ?? 0.45);

  if (spec.kind === 'mountains') drawMountains(ctx, r, b, spec, env);

  const tiers = (spec.tiers || []).slice().sort((a, b2) => a.y - b2.y);
  for (const tier of tiers) {
    const rects = [];
    // landmarks behind the tier's ordinary buildings
    for (const lm of spec.landmarks || []) {
      if ((lm.tier ?? 0) !== tiers.indexOf(tier)) continue;
      const lw = lm.w * s, lh = lm.h * s;
      BUILDERS[lm.type](ctx, r, lm.x - lw / 2, tier.y + 2, lw, lh, env);
    }
    let x = b.x0 - r.range(0, 80) * s;
    const types = tier.types || DEFAULT_TYPES;
    while (x < b.x1) {
      const type = r.weighted(types);
      let bw = r.range(tier.wMin ?? 110, tier.wMax ?? 230) * s;
      let bh = r.range(tier.hMin ?? 200, tier.hMax ?? 520) * s;
      if (type === 'canalhouse') { bw *= 0.62; bh *= 1.05; }
      if (type === 'pagoda') { bw *= 1.1; bh *= 1.1; }
      if (type === 'greenhouse') { bw *= 1.25; bh *= 0.55; }
      if (type === 'dome') { bw *= 1.2; bh *= 0.95; }
      if (type === 'stalls') { bh *= 0.6; }
      const by = tier.y + r.range(-6, 6) * s;
      const topY = BUILDERS[type](ctx, r, x, by, bw, bh, env);
      rects.push([x, x + bw, by - bh, topY, type]);
      x += bw + r.range(tier.gapMin ?? 4, tier.gapMax ?? 40) * s;
    }
    // sky bridges between neighbours
    for (let i = 0; i < rects.length - 1; i++) {
      const A = rects[i], B = rects[i + 1];
      if (r.next() < (tier.bridgeP ?? 0.12) && B[0] - A[1] > 10 * s) {
        const yb = Math.max(A[2], B[2]) + r.range(40, 120) * s;
        bridge(ctx, r, A[1] - 4 * s, B[0] + 4 * s, yb, env, { archH: 18 * s });
      }
    }
    if (spec.laundry !== false) laundry(ctx, r, env, env.info.tops.filter((t) => t[2] > tier.y - 900 * s && t[2] < tier.y));
    const cd = (tier.canal || 0) * s;
    if (cd > 0) {
      canal(ctx, r, b.x0, b.x1, tier.y + 4 * s, tier.y + cd, env);
      gondolas(ctx, r, b, tier.y + 4 * s, env);
    }
    if (tier.wall !== false) terrace(ctx, r, b.x0 - 10, b.x1 + 10, tier.y + cd, b.y1 + 20, env);
  }

  for (const br of spec.bridges || []) bridge(ctx, r, br.x0, br.x1, br.y, env, { archH: br.archH });
  if (spec.tram) tramRail(ctx, r, b, spec.tram.y, env);

  const finished = finishLayer(canvas, pal, {
    rim: spec.rim !== false, rimWidth: Math.max(2, 5 * s), grain: spec.grain ?? 0.55,
    shadow: spec.shadow ?? (0.55 - depthT * 0.4), shadowBlur: 10 + 22 * s, shadowOff: [4 * s, 12 * s],
  });

  const layer = { canvas: finished, x0: b.x0, y0: b.y0, d, info: env.info, s, depthT, spec };
  if (spec.litVariant) layer.lit = bakeLit(env.info.windows, b, pal, s);
  return layer;
}

function bakeLit(windows, b, pal, s) {
  const c = makeCanvas(b.x1 - b.x0, b.y1 - b.y0);
  const g = c.getContext('2d');
  g.translate(-b.x0, -b.y0);
  const wc = mix(pal.window, '#fff4d0', 0.35);
  for (const [x, y, w, h] of windows) {
    g.fillStyle = css(wc);
    g.fillRect(x, y, w, h);
  }
  g.globalCompositeOperation = 'lighter';
  g.globalAlpha = 0.35;
  const spr = glowSprite(pal.window);
  for (const [x, y, w, h] of windows) {
    const R = Math.max(w, h) * 2.6;
    g.drawImage(spr, x + w / 2 - R / 2, y + h / 2 - R / 2, R, R);
  }
  return c;
}

function gondolas(ctx, r, b, y, env) {
  const { s, pal } = env;
  for (let x = b.x0 + r.next() * 400 * s; x < b.x1; x += r.range(300, 700) * s) {
    const gw = r.range(60, 90) * s;
    ctx.fillStyle = css(env.fade(shade(pal.near, -0.1)));
    ctx.beginPath();
    ctx.moveTo(x, y + 6 * s);
    ctx.quadraticCurveTo(x + gw / 2, y + 22 * s, x + gw, y + 6 * s);
    ctx.lineTo(x + gw + 6 * s, y - 6 * s);
    ctx.lineTo(x + gw * 0.9, y + 6 * s);
    ctx.fill();
    ctx.fillRect(x + gw * 0.75, y - 22 * s, 2 * s, 24 * s);
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.6;
    ctx.drawImage(glowSprite(pal.lamp), x + gw * 0.2, y - 16 * s, 28 * s, 28 * s);
    ctx.restore();
  }
}

function tramRail(ctx, r, b, y, env) {
  const { s, pal } = env;
  const iron = env.fade(shade(pal.near, 0.12));
  ctx.strokeStyle = css(iron);
  ctx.lineWidth = 5 * s;
  ctx.beginPath(); ctx.moveTo(b.x0, y); ctx.lineTo(b.x1, y); ctx.stroke();
  ctx.lineWidth = 2 * s;
  ctx.beginPath(); ctx.moveTo(b.x0, y + 9 * s); ctx.lineTo(b.x1, y + 9 * s); ctx.stroke();
  ctx.beginPath();
  for (let x = b.x0; x < b.x1; x += 14 * s) { ctx.moveTo(x, y); ctx.lineTo(x + 7 * s, y + 9 * s); }
  ctx.stroke();
  // pylons
  for (let x = b.x0 + 100 * s; x < b.x1; x += 320 * s) {
    ctx.lineWidth = 4 * s;
    ctx.beginPath();
    ctx.moveTo(x, y + 9 * s); ctx.lineTo(x - 30 * s, y + 420 * s);
    ctx.moveTo(x, y + 9 * s); ctx.lineTo(x + 30 * s, y + 420 * s);
    ctx.stroke();
    ctx.lineWidth = 1.5 * s;
    ctx.beginPath();
    for (let k = 1; k < 8; k++) { ctx.moveTo(x - 30 * s * (k / 8), y + 9 * s + 411 * s * (k / 8)); ctx.lineTo(x + 30 * s * ((k + 1) / 8), y + 9 * s + 411 * s * ((k + 1) / 8)); }
    ctx.stroke();
  }
  env.info.tram = { y, x0: b.x0, x1: b.x1 };
}

function drawMountains(ctx, r, b, spec, env) {
  const { pal } = env;
  const base = spec.y ?? 200;
  // two ridge bands
  for (let band = 0; band < 2; band++) {
    const c = mix(pal.far, pal.haze, 0.45 + band * 0.25 - 0.1);
    ctx.fillStyle = css(mix(c, pal.sky[3], 0.2 - band * 0.1));
    ctx.beginPath();
    ctx.moveTo(b.x0, b.y1);
    for (let x = b.x0; x <= b.x1; x += 12) {
      const n = fbm1(x * 0.0025 + band * 9, 11 + band, 4);
      const spike = Math.pow(fbm1(x * 0.011 + band * 3, 3, 2), 3) * 220;
      ctx.lineTo(x, base - band * -120 - n * 420 - spike + 60);
    }
    ctx.lineTo(b.x1, b.y1);
    ctx.closePath();
    ctx.fill();
  }
  // far needle spires on the ridge
  for (let i = 0; i < 14; i++) {
    const x = b.x0 + r.next() * (b.x1 - b.x0);
    const hh = r.range(90, 320), ww = r.range(10, 26);
    const yb = base + 80 - fbm1(x * 0.0025, 11, 4) * 420;
    ctx.fillStyle = css(mix(pal.far, pal.haze, 0.35));
    ctx.beginPath();
    ctx.moveTo(x - ww, yb);
    ctx.lineTo(x - ww * 0.6, yb - hh * 0.8);
    ctx.lineTo(x, yb - hh);
    ctx.lineTo(x + ww * 0.6, yb - hh * 0.8);
    ctx.lineTo(x + ww, yb);
    ctx.fill();
    if (r.next() < 0.6) {
      ctx.fillStyle = css(pal.window, 0.7);
      for (let k = 0; k < 4; k++) ctx.fillRect(x - 2, yb - hh * (0.2 + k * 0.15), 3, 5);
    }
  }
  // floating islands with tiny houses and waterfalls
  for (let i = 0; i < (spec.islands ?? 5); i++) {
    const x = b.x0 + 200 + r.next() * (b.x1 - b.x0 - 400);
    const y = base - r.range(500, 1300);
    const iw = r.range(90, 200);
    const rockC = mix(pal.far, pal.near, 0.2);
    ctx.fillStyle = css(rockC);
    ctx.beginPath();
    ctx.moveTo(x - iw / 2, y);
    ctx.quadraticCurveTo(x - iw * 0.2, y + iw * 0.25, x, y + iw * 0.7);
    ctx.quadraticCurveTo(x + iw * 0.25, y + iw * 0.3, x + iw / 2, y);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = css(mix(pal.copper[2], pal.far, 0.4));
    ctx.fillRect(x - iw / 2, y - 6, iw, 8);
    for (let k = 0; k < 3; k++) {
      const hx = x - iw * 0.35 + k * iw * 0.28, hw = iw * 0.18, hh = r.range(18, 40);
      ctx.fillStyle = css(mix(r.pick(pal.paints), pal.haze, 0.35));
      ctx.fillRect(hx, y - 6 - hh, hw, hh);
      ctx.fillStyle = css(mix(r.pick(pal.roof), pal.haze, 0.3));
      ctx.beginPath(); ctx.moveTo(hx - 3, y - 6 - hh); ctx.lineTo(hx + hw / 2, y - 18 - hh); ctx.lineTo(hx + hw + 3, y - 6 - hh); ctx.fill();
      ctx.fillStyle = css(pal.window, 0.85);
      ctx.fillRect(hx + hw * 0.35, y - hh * 0.6, hw * 0.3, hh * 0.3);
    }
    if (r.next() < 0.7) {
      const g = ctx.createLinearGradient(0, y, 0, y + 260);
      g.addColorStop(0, css(mix(pal.water, '#ffffff', 0.4), 0.7));
      g.addColorStop(1, css(mix(pal.water, '#ffffff', 0.4), 0));
      ctx.fillStyle = g;
      ctx.fillRect(x + iw * 0.12, y, 10, 260);
    }
  }
}

// --- simple helpers for hand-built layers ---------------------------------
export function bakeLayer(d, bounds, pal, draw, opts = {}) {
  const canvas = makeCanvas(bounds.x1 - bounds.x0, bounds.y1 - bounds.y0);
  const ctx = canvas.getContext('2d');
  ctx.translate(-bounds.x0, -bounds.y0);
  const s = opts.s || clamp(1.45 / d, 0.22, 1.25);
  const env = makeEnv(pal, s, opts.depthT ?? clamp((d - 1) / 8), opts.litP ?? 0.5);
  const r = rng(opts.seed ?? 1);
  draw(ctx, r, env, bounds);
  const finished = opts.finish === false ? canvas : finishLayer(canvas, pal, {
    rim: opts.rim !== false, rimWidth: Math.max(2, 5 * s), grain: opts.grain ?? 0.5,
    shadow: opts.shadow ?? 0.5, shadowBlur: 10 + 20 * s, shadowOff: [4 * s, 12 * s],
  });
  return { canvas: finished, x0: bounds.x0, y0: bounds.y0, d, info: env.info, s, depthT: env.depthT, env };
}

export { drawWindow, roughPath, posterV };
