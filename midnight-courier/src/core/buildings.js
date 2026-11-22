// Procedural building generator. Every function paints one building with its
// base at (x, by), width w and body height h into a 2D context, in a
// posterised gouache style, and records windows / chimneys / lantern anchors /
// clock faces into env.info so the scene can animate them.
import { css, mix, shade, clamp } from './util.js';
import { roughPath, roughRect, posterV, brushTexture, glowSprite } from './paint.js';

export function makeEnv(pal, s, depthT, litP = 0.45) {
  return {
    pal, s, depthT, litP,
    info: { windows: [], chimneys: [], lanterns: [], clocks: [], glows: [], tops: [], roofs: [] },
    fade(c, k = 0.75) { return mix(c, pal.haze, clamp(depthT * k)); },
    body(r) {
      const paint = r.pick(pal.paints);
      return this.fade(mix(pal.near, paint, 0.35 + r.next() * 0.35));
    },
    roof(r) { return this.fade(mix(r.pick(pal.roof), pal.near, 0.2)); },
  };
}

// ---------------------------------------------------------------- windows
export function drawWindow(ctx, r, x, y, ww, wh, env, body, opt = {}) {
  const { s, pal } = env;
  const lit = opt.lit !== undefined ? opt.lit : r.next() < env.litP;
  const arched = opt.arched;
  const shapePath = () => {
    ctx.beginPath();
    if (arched) {
      ctx.moveTo(x, y + wh);
      ctx.lineTo(x, y + ww / 2);
      ctx.arc(x + ww / 2, y + ww / 2, ww / 2, Math.PI, 0);
      ctx.lineTo(x + ww, y + wh);
      ctx.closePath();
    } else ctx.rect(x, y, ww, wh);
  };
  if (lit) {
    const wc = env.fade(mix(pal.window, '#fff6dc', r.next() * 0.35), 0.35);
    shapePath();
    ctx.fillStyle = css(wc);
    ctx.fill();
    // warm inner gradient (posterised: two bands)
    ctx.fillStyle = css(shade(wc, -0.18), 0.8);
    ctx.fillRect(x, y + wh * 0.62, ww, wh * 0.38);
    if (s > 0.3 && !opt.noGlow) {
      const g = ww * 3.2;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.28;
      ctx.drawImage(glowSprite(pal.window), x + ww / 2 - g / 2, y + wh / 2 - g / 2, g, g);
      ctx.restore();
    }
  } else {
    shapePath();
    ctx.fillStyle = css(shade(body, -0.38));
    ctx.fill();
    if (s > 0.5) {
      ctx.fillStyle = css(env.fade(pal.rim), 0.12);
      ctx.fillRect(x + ww * 0.55, y + 2, ww * 0.25, wh * 0.5);
    }
  }
  if (s > 0.45) {
    ctx.strokeStyle = css(shade(body, 0.28), 0.9);
    ctx.lineWidth = Math.max(1, 1.6 * s);
    ctx.beginPath();
    ctx.moveTo(x + ww / 2, y + (arched ? ww / 2 : 0));
    ctx.lineTo(x + ww / 2, y + wh);
    ctx.moveTo(x, y + wh * 0.45);
    ctx.lineTo(x + ww, y + wh * 0.45);
    ctx.stroke();
    // sill
    ctx.fillStyle = css(shade(body, 0.22));
    ctx.fillRect(x - 2 * s, y + wh, ww + 4 * s, 3 * s + 1);
  }
  env.info.windows.push([x, y, ww, wh, lit ? 1 : 0]);
  return lit;
}

function windowGrid(ctx, r, env, body, x0, y0, w, h, colW, rowH, lean = 0, baseY = 0, opt = {}) {
  const cols = Math.max(1, Math.floor(w / colW));
  const rows = Math.max(1, Math.floor(h / rowH));
  const padX = (w - cols * colW) / 2;
  const ww = colW * (opt.wf || 0.52), wh = rowH * (opt.hf || 0.56);
  for (let ry = 0; ry < rows; ry++) {
    const wy = y0 + ry * rowH + (rowH - wh) * 0.35;
    const shift = lean ? (lean * (baseY - wy)) / (baseY - y0 + 1e-3) : 0;
    for (let cx = 0; cx < cols; cx++) {
      const wx = x0 + padX + cx * colW + (colW - ww) / 2 + shift;
      drawWindow(ctx, r, wx, wy, ww, wh, env, body, opt);
      if (opt.shutters && env.s > 0.6 && r.next() < 0.25) {
        ctx.fillStyle = css(env.fade(shade(r.pick(env.pal.paints), 0.1)));
        ctx.fillRect(wx - ww * 0.32, wy, ww * 0.28, wh);
        ctx.fillRect(wx + ww * 1.04, wy, ww * 0.28, wh);
      }
    }
  }
}

function chimney(ctx, r, env, cx, top, body) {
  const s = env.s;
  const ch = r.range(24, 58) * s, cw = r.range(12, 22) * s;
  ctx.fillStyle = css(shade(body, -0.12));
  roughRect(ctx, r, cx - cw / 2, top - ch, cw, ch + 2, 0.6);
  ctx.fill();
  ctx.fillStyle = css(shade(body, 0.15));
  ctx.fillRect(cx - cw / 2 - 2 * s, top - ch - 4 * s, cw + 4 * s, 5 * s);
  ctx.fillStyle = css(shade(body, -0.3));
  ctx.fillRect(cx - cw * 0.25, top - ch - 9 * s, cw * 0.22, 6 * s);
  ctx.fillRect(cx + cw * 0.06, top - ch - 7 * s, cw * 0.22, 4 * s);
  env.info.chimneys.push([cx, top - ch - 8 * s, s]);
}

function lanternAt(ctx, env, x, y, size) {
  const { pal } = env;
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.5;
  const g = size * 5;
  ctx.drawImage(glowSprite(pal.lamp), x - g / 2, y - g / 2, g, g);
  ctx.restore();
  ctx.fillStyle = css(mix(pal.lamp, '#fff2c0', 0.3));
  ctx.beginPath();
  ctx.ellipse(x, y, size * 0.55, size * 0.75, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = css(shade(pal.lamp, -0.45));
  ctx.fillRect(x - size * 0.4, y - size * 0.85, size * 0.8, size * 0.2);
  ctx.fillRect(x - size * 0.4, y + size * 0.65, size * 0.8, size * 0.2);
  env.info.lanterns.push([x, y, size]);
}

// ---------------------------------------------------------------- types
export function tenement(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const lean = r.range(-0.07, 0.07) * w;
  const body = env.body(r);
  const top = by - h;
  ctx.save();
  roughPath(ctx, r, [[x, by], [x + w, by], [x + w + lean, top], [x + lean, top]], 1 * s + 0.4);
  ctx.fillStyle = css(body);
  ctx.fill();
  ctx.save();
  ctx.clip();
  posterV(ctx, r, x - 20, top, w + 40, h, shade(body, 0.14), shade(body, -0.22), 4, 3 * s);
  if (s > 0.4) brushTexture(ctx, r, x, top, w, h, shade(body, -0.3), Math.floor((w * h) / (900 * s * s)), 0.18, 9 * s, 2 * s, true);
  if (s > 0.4) brushTexture(ctx, r, x, top, w, h, shade(body, 0.3), Math.floor((w * h) / (1600 * s * s)), 0.12, 8 * s, 2 * s, true);
  windowGrid(ctx, r, env, body, x + 6 * s, top + 22 * s, w - 12 * s, h - 60 * s, 44 * s, 62 * s, lean, by, { shutters: true });
  // shop front
  if (s > 0.55) {
    const aw = shade(r.pick(pal.paints), 0.25);
    ctx.fillStyle = css(env.fade(shade(body, -0.35)));
    ctx.fillRect(x, by - 40 * s, w, 40 * s);
    ctx.fillStyle = css(env.fade(pal.window), 0.9);
    ctx.fillRect(x + w * 0.15, by - 34 * s, w * 0.3, 30 * s);
    ctx.fillStyle = css(env.fade(aw));
    for (let i = 0; i < Math.floor(w / (14 * s)); i++) {
      ctx.fillStyle = css(env.fade(i % 2 ? aw : mix(aw, '#fff1d6', 0.6)));
      ctx.beginPath();
      ctx.moveTo(x + i * 14 * s, by - 52 * s);
      ctx.lineTo(x + (i + 1) * 14 * s, by - 52 * s);
      ctx.lineTo(x + (i + 1) * 14 * s, by - 40 * s);
      ctx.arc(x + (i + 0.5) * 14 * s, by - 40 * s, 7 * s, 0, Math.PI);
      ctx.fill();
    }
  }
  ctx.restore();
  // cornice
  ctx.fillStyle = css(shade(body, 0.2));
  roughRect(ctx, r, x + lean - 5 * s, top - 4 * s, w + 10 * s, 9 * s, 0.5);
  ctx.fill();
  // fire escape
  if (s > 0.55 && r.next() < 0.4) {
    const fx = x + lean * 0.5 + (r.next() < 0.5 ? w * 0.08 : w * 0.55), fw = w * 0.36;
    ctx.strokeStyle = css(shade(body, -0.5));
    ctx.lineWidth = 2 * s;
    for (let y = top + 70 * s; y < by - 70 * s; y += 62 * s) {
      ctx.strokeRect(fx, y, fw, 12 * s);
      ctx.beginPath();
      ctx.moveTo(fx + fw * 0.1, y + 12 * s);
      ctx.lineTo(fx + fw * 0.9, y + 62 * s);
      ctx.stroke();
    }
  }
  const nch = r.int(1, 3);
  for (let i = 0; i < nch; i++) chimney(ctx, r, env, x + lean + r.range(0.12, 0.88) * w, top - 3 * s, body);
  if (r.next() < 0.22) waterTower(ctx, r, env, x + lean + r.range(0.25, 0.7) * w, top - 4 * s, body);
  ctx.restore();
  env.info.tops.push([x + lean, x + w + lean, top]);
  env.info.roofs.push([x + Math.max(0, lean) + 8 * s, x + w + Math.min(0, lean) - 8 * s, top - 4 * s]);
  return top;
}

function waterTower(ctx, r, env, cx, top, body) {
  const s = env.s;
  const tw = r.range(34, 50) * s, th = tw * 0.9, legs = 26 * s;
  ctx.strokeStyle = css(shade(body, -0.4));
  ctx.lineWidth = 2.5 * s;
  ctx.beginPath();
  ctx.moveTo(cx - tw * 0.4, top); ctx.lineTo(cx - tw * 0.35, top - legs);
  ctx.moveTo(cx + tw * 0.4, top); ctx.lineTo(cx + tw * 0.35, top - legs);
  ctx.moveTo(cx - tw * 0.4, top); ctx.lineTo(cx + tw * 0.35, top - legs);
  ctx.stroke();
  const wood = env.fade(mix('#7a5a48', env.pal.near, 0.3));
  ctx.fillStyle = css(wood);
  roughRect(ctx, r, cx - tw / 2, top - legs - th, tw, th, 0.5);
  ctx.fill();
  ctx.fillStyle = css(shade(wood, 0.2));
  ctx.fillRect(cx - tw / 2, top - legs - th * 0.35, tw, 3 * s);
  ctx.fillRect(cx - tw / 2, top - legs - th * 0.7, tw, 3 * s);
  ctx.fillStyle = css(env.roof(r));
  ctx.beginPath();
  ctx.moveTo(cx - tw * 0.58, top - legs - th);
  ctx.lineTo(cx, top - legs - th - tw * 0.5);
  ctx.lineTo(cx + tw * 0.58, top - legs - th);
  ctx.fill();
}

// Narrow canal house with a stepped / bell gable.
export function canalhouse(ctx, r, x, by, w, h, env) {
  const { s } = env;
  const body = env.body(r);
  const top = by - h;
  const gh = w * r.range(0.45, 0.8);
  const stepped = r.next() < 0.55;
  const pts = [[x, by], [x + w, by], [x + w, top]];
  if (stepped) {
    const n = 3;
    for (let i = 1; i <= n; i++) {
      const xx = x + w - (w * 0.5 * i) / (n + 0.5);
      pts.push([x + w - (w * 0.5 * (i - 1)) / (n + 0.5), top - (gh * i) / (n + 1)]);
      pts.push([xx, top - (gh * i) / (n + 1)]);
    }
    pts.push([x + w * 0.62, top - gh]);
    pts.push([x + w * 0.38, top - gh]);
    for (let i = n; i >= 1; i--) {
      const xx = x + (w * 0.5 * i) / (n + 0.5);
      pts.push([xx, top - (gh * i) / (n + 1)]);
      pts.push([x + (w * 0.5 * (i - 1)) / (n + 0.5), top - (gh * i) / (n + 1)]);
    }
  } else {
    pts.push([x + w * 0.78, top - gh * 0.55]);
    pts.push([x + w * 0.6, top - gh]);
    pts.push([x + w * 0.4, top - gh]);
    pts.push([x + w * 0.22, top - gh * 0.55]);
  }
  pts.push([x, top]);
  ctx.save();
  roughPath(ctx, r, pts, 0.8 * s + 0.3, 10);
  ctx.fillStyle = css(body);
  ctx.fill();
  ctx.save();
  ctx.clip();
  posterV(ctx, r, x - 4, top - gh, w + 8, h + gh, shade(body, 0.18), shade(body, -0.2), 4, 2 * s);
  if (s > 0.4) brushTexture(ctx, r, x, top - gh, w, h + gh, shade(body, -0.25), Math.floor((w * h) / (1200 * s * s)), 0.15, 8 * s, 2 * s, true);
  windowGrid(ctx, r, env, body, x + 4 * s, top + 16 * s, w - 8 * s, h - 40 * s, 36 * s, 70 * s, 0, by, { hf: 0.62, arched: r.next() < 0.4 });
  // gable window + hoist beam
  drawWindow(ctx, r, x + w / 2 - 8 * s, top - gh * 0.55, 16 * s, 22 * s, env, body, { arched: true });
  ctx.restore();
  ctx.fillStyle = css(shade(body, -0.45));
  ctx.fillRect(x + w / 2 - 2 * s, top - gh - 2 * s, 4 * s, 12 * s);
  ctx.fillStyle = css(shade(body, -0.35));
  ctx.fillRect(x - 2 * s, by - 34 * s, w + 4 * s, 4 * s);
  ctx.restore();
  env.info.tops.push([x, x + w, top - gh * 0.6]);
  return top - gh;
}

// Tiered pagoda with up-turned eaves and gold-trimmed roofs.
export function pagoda(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const tiers = r.int(3, 5);
  const body = env.fade(mix(pal.near, r.pick(pal.paints), 0.5));
  const roofC = env.roof(r);
  const trim = env.fade(mix(pal.lamp, '#ffe8a0', 0.3), 0.6);
  const th = h / tiers;
  let y = by;
  let top = by;
  for (let i = 0; i < tiers; i++) {
    const tw = w * (1 - i * 0.14);
    const tx = x + (w - tw) / 2;
    const bh = th * 0.62;
    // body with lit paper screens
    ctx.fillStyle = css(shade(body, -0.1 + i * 0.04));
    roughRect(ctx, r, tx + tw * 0.1, y - bh, tw * 0.8, bh, 0.5);
    ctx.fill();
    const scr = Math.max(2, Math.floor((tw * 0.8) / (20 * s)));
    for (let k = 0; k < scr; k++) {
      const sx = tx + tw * 0.1 + (k + 0.15) * ((tw * 0.8) / scr);
      const sw = ((tw * 0.8) / scr) * 0.7;
      const lit = r.next() < env.litP + 0.25;
      ctx.fillStyle = lit ? css(env.fade(mix(pal.window, '#fff1d0', 0.25), 0.35)) : css(shade(body, -0.35));
      ctx.fillRect(sx, y - bh * 0.85, sw, bh * 0.7);
      if (lit && s > 0.35) {
        ctx.strokeStyle = css(shade(pal.window, -0.35), 0.6);
        ctx.lineWidth = 1;
        ctx.strokeRect(sx + sw * 0.5, y - bh * 0.85, 0.1, bh * 0.7);
        ctx.strokeRect(sx, y - bh * 0.5, sw, 0.1);
      }
      env.info.windows.push([sx, y - bh * 0.85, sw, bh * 0.7, lit ? 1 : 0]);
    }
    // roof with up-turned eaves
    const ry = y - bh;
    const ov = tw * 0.16;
    const rh = th * 0.42;
    ctx.fillStyle = css(roofC);
    ctx.beginPath();
    ctx.moveTo(tx - ov, ry - rh * 0.55);
    ctx.quadraticCurveTo(tx + tw * 0.08, ry - rh * 0.05, tx + tw * 0.22, ry - rh * 0.55);
    ctx.lineTo(tx + tw * 0.32, ry - rh);
    ctx.lineTo(tx + tw * 0.68, ry - rh);
    ctx.lineTo(tx + tw * 0.78, ry - rh * 0.55);
    ctx.quadraticCurveTo(tx + tw * 0.92, ry - rh * 0.05, tx + tw + ov, ry - rh * 0.55);
    ctx.quadraticCurveTo(tx + tw * 0.9, ry + rh * 0.12, tx + tw * 0.5, ry + rh * 0.05);
    ctx.quadraticCurveTo(tx + tw * 0.1, ry + rh * 0.12, tx - ov, ry - rh * 0.55);
    ctx.fill();
    ctx.fillStyle = css(shade(roofC, 0.18));
    ctx.fillRect(tx + tw * 0.32, ry - rh, tw * 0.36, rh * 0.18);
    ctx.strokeStyle = css(trim);
    ctx.lineWidth = Math.max(1, 2.2 * s);
    ctx.beginPath();
    ctx.moveTo(tx - ov, ry - rh * 0.55);
    ctx.quadraticCurveTo(tx + tw * 0.1, ry + rh * 0.12, tx + tw * 0.5, ry + rh * 0.05);
    ctx.quadraticCurveTo(tx + tw * 0.9, ry + rh * 0.12, tx + tw + ov, ry - rh * 0.55);
    ctx.stroke();
    if (s > 0.3) {
      lanternAt(ctx, env, tx - ov + 4 * s, ry - rh * 0.55 + 14 * s, 7 * s);
      lanternAt(ctx, env, tx + tw + ov - 4 * s, ry - rh * 0.55 + 14 * s, 7 * s);
    }
    y = ry - rh * 0.7;
    top = ry - rh;
  }
  // finial
  ctx.strokeStyle = css(trim);
  ctx.lineWidth = 3 * s;
  ctx.beginPath();
  ctx.moveTo(x + w / 2, top);
  ctx.lineTo(x + w / 2, top - th * 0.6);
  ctx.stroke();
  for (let k = 0; k < 4; k++) {
    ctx.fillStyle = css(trim);
    ctx.beginPath();
    ctx.ellipse(x + w / 2, top - th * 0.12 - k * th * 0.11, (8 - k) * s, 2.5 * s, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  env.info.tops.push([x, x + w, by - h * 0.3]);
  return top - th * 0.6;
}

// Glass greenhouse with barrel vault, mullions and plants glowing inside.
export function greenhouse(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const baseH = h * 0.18;
  const bodyH = h * 0.42;
  const vault = w * 0.45;
  const top = by - baseH - bodyH;
  const brick = env.body(r);
  ctx.fillStyle = css(brick);
  roughRect(ctx, r, x, by - baseH, w, baseH, 0.6);
  ctx.fill();
  const glass = env.fade(mix(mix(r.pick(pal.copper), pal.near, 0.35), '#bfe8de', 0.15));
  ctx.save();
  ctx.beginPath();
  ctx.rect(x + 4 * s, top, w - 8 * s, bodyH);
  ctx.ellipse(x + w / 2, top + 1, w / 2 - 4 * s, vault, 0, Math.PI, 0);
  ctx.fillStyle = css(glass, 0.92);
  ctx.fill();
  ctx.clip();
  posterV(ctx, r, x, top - vault, w, bodyH + vault, shade(glass, 0.25), shade(glass, -0.15), 4, 2);
  // warm interior glow
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.45;
  const g = w * 1.2;
  ctx.drawImage(glowSprite(pal.window), x + w / 2 - g / 2, by - baseH - g * 0.45, g, g * 0.8);
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  // plants
  const leaf = env.fade(mix('#2f6a4a', pal.near, 0.35));
  for (let i = 0; i < Math.floor(w / (14 * s)); i++) {
    const px = x + r.next() * w, ph = r.range(0.3, 1.05) * (bodyH + vault * 0.6);
    ctx.fillStyle = css(shade(leaf, r.range(-0.15, 0.2)));
    ctx.beginPath();
    ctx.ellipse(px, by - baseH - ph * 0.5, r.range(8, 22) * s, ph * 0.5, r.range(-0.3, 0.3), 0, Math.PI * 2);
    ctx.fill();
  }
  // mullions
  ctx.strokeStyle = css(env.fade(mix(pal.near, '#c8e0d8', 0.35)));
  ctx.lineWidth = Math.max(1, 2 * s);
  const cols = Math.max(3, Math.floor(w / (22 * s)));
  ctx.beginPath();
  for (let i = 0; i <= cols; i++) {
    const xx = x + (w * i) / cols;
    ctx.moveTo(xx, by - baseH);
    const dx = (xx - (x + w / 2)) / (w / 2);
    ctx.lineTo(xx, top - Math.sqrt(Math.max(0, 1 - dx * dx)) * vault);
  }
  for (let j = 1; j < 4; j++) {
    const yy = top + (bodyH * j) / 4;
    ctx.moveTo(x, yy);
    ctx.lineTo(x + w, yy);
  }
  for (let j = 1; j < 3; j++) ctx.ellipse(x + w / 2, top, (w / 2) * (1 - j * 0.0), vault * (1 - j * 0.33), 0, Math.PI, 0);
  ctx.stroke();
  // specular streaks
  ctx.strokeStyle = 'rgba(255,255,255,0.22)';
  ctx.lineWidth = 6 * s;
  ctx.beginPath();
  ctx.moveTo(x + w * 0.2, by - baseH);
  ctx.lineTo(x + w * 0.42, top - vault * 0.8);
  ctx.stroke();
  ctx.restore();
  env.info.windows.push([x + w * 0.2, top, w * 0.6, bodyH, 1]);
  env.info.tops.push([x, x + w, top - vault * 0.5]);
  return top - vault;
}

// Copper dome on a columned drum.
export function dome(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const body = env.fade(mix(env.body(r), '#d8c8b8', 0.12));
  const baseH = h * 0.45, drumH = h * 0.2, domeH = h * 0.3;
  const top = by - baseH;
  ctx.fillStyle = css(body);
  roughRect(ctx, r, x, top, w, baseH, 0.6);
  ctx.fill();
  ctx.save();
  ctx.beginPath(); ctx.rect(x, top, w, baseH); ctx.clip();
  posterV(ctx, r, x, top, w, baseH, shade(body, 0.15), shade(body, -0.2), 3, 2);
  windowGrid(ctx, r, env, body, x + 8 * s, top + 20 * s, w - 16 * s, baseH - 30 * s, 40 * s, 72 * s, 0, by, { arched: true, hf: 0.7 });
  ctx.restore();
  // pediment
  ctx.fillStyle = css(shade(body, 0.12));
  ctx.beginPath();
  ctx.moveTo(x - 6 * s, top);
  ctx.lineTo(x + w / 2, top - w * 0.12);
  ctx.lineTo(x + w + 6 * s, top);
  ctx.fill();
  // drum
  const dw = w * 0.62, dx = x + (w - dw) / 2, dy = top - w * 0.08 - drumH;
  ctx.fillStyle = css(shade(body, -0.05));
  ctx.fillRect(dx, dy, dw, drumH + w * 0.08);
  const nc = Math.max(4, Math.floor(dw / (16 * s)));
  for (let i = 0; i < nc; i++) {
    const cx = dx + ((i + 0.5) * dw) / nc;
    ctx.fillStyle = css(shade(body, 0.25));
    ctx.fillRect(cx - 2.5 * s, dy, 5 * s, drumH);
    if (i < nc - 1) drawWindow(ctx, r, cx + 4 * s, dy + drumH * 0.2, dw / nc - 8 * s, drumH * 0.6, env, body, { arched: true, noGlow: s < 0.5 });
  }
  // dome with posterised copper/verdigris bands
  const cu = pal.copper.map((c) => env.fade(c));
  const dcx = dx + dw / 2, dcy = dy;
  for (let b = 0; b < 4; b++) {
    const k = 1 - b * 0.2;
    ctx.fillStyle = css(mix(cu[2], cu[1], b / 3));
    ctx.beginPath();
    ctx.ellipse(dcx + b * dw * 0.04, dcy, (dw / 2 + 4 * s) * k, domeH * (0.4 + 0.6 * k), 0, Math.PI, 0);
    ctx.fill();
  }
  ctx.strokeStyle = css(shade(cu[2], -0.3), 0.7);
  ctx.lineWidth = 1.5 * s;
  for (let i = 1; i < 6; i++) {
    const t = i / 6;
    ctx.beginPath();
    ctx.ellipse(dcx, dcy, (dw / 2 + 4 * s) * Math.abs(Math.cos(t * Math.PI)), domeH, 0, Math.PI, 0);
    ctx.stroke();
  }
  // lantern cupola + finial
  const ly = dcy - domeH;
  ctx.fillStyle = css(shade(body, 0.1));
  ctx.fillRect(dcx - dw * 0.08, ly - domeH * 0.3, dw * 0.16, domeH * 0.32);
  ctx.fillStyle = css(env.fade(pal.window, 0.3));
  ctx.fillRect(dcx - dw * 0.04, ly - domeH * 0.24, dw * 0.08, domeH * 0.2);
  ctx.fillStyle = css(cu[1]);
  ctx.beginPath();
  ctx.ellipse(dcx, ly - domeH * 0.3, dw * 0.1, domeH * 0.14, 0, Math.PI, 0);
  ctx.fill();
  ctx.strokeStyle = css(env.fade(pal.lamp, 0.4));
  ctx.lineWidth = 2.5 * s;
  ctx.beginPath();
  ctx.moveTo(dcx, ly - domeH * 0.42);
  ctx.lineTo(dcx, ly - domeH * 0.75);
  ctx.stroke();
  env.info.glows.push([dcx, ly - domeH * 0.78, 10 * s]);
  env.info.tops.push([x, x + w, top]);
  return ly - domeH * 0.75;
}

// Giant clock tower. The face is baked; hands are animated by the scene.
export function clocktower(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const stone = env.fade(mix(env.body(r), '#c9b8a6', 0.15));
  const shaftTop = by - h * 0.78;
  ctx.fillStyle = css(stone);
  roughRect(ctx, r, x, shaftTop, w, h * 0.78, 0.8);
  ctx.fill();
  ctx.save();
  ctx.beginPath(); ctx.rect(x, shaftTop, w, h * 0.78); ctx.clip();
  posterV(ctx, r, x, shaftTop, w, h * 0.78, shade(stone, 0.12), shade(stone, -0.28), 5, 2);
  // stone courses
  ctx.strokeStyle = css(shade(stone, -0.3), 0.35);
  ctx.lineWidth = 1.2 * s;
  for (let y = shaftTop; y < by; y += 22 * s) {
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w, y); ctx.stroke();
  }
  // pilasters
  ctx.fillStyle = css(shade(stone, 0.18));
  ctx.fillRect(x, shaftTop, w * 0.08, h);
  ctx.fillRect(x + w * 0.92, shaftTop, w * 0.08, h);
  // slit windows
  for (let y = shaftTop + h * 0.25; y < by - 40 * s; y += 90 * s) drawWindow(ctx, r, x + w / 2 - 7 * s, y, 14 * s, 40 * s, env, stone, { arched: true });
  ctx.restore();
  // clock stage
  const cy = shaftTop + w * 0.62;
  const cr = w * 0.42;
  ctx.fillStyle = css(shade(stone, 0.08));
  ctx.fillRect(x - w * 0.06, shaftTop - 6 * s, w * 1.12, 14 * s);
  ctx.fillStyle = css(shade(stone, -0.35));
  ctx.beginPath(); ctx.arc(x + w / 2, cy, cr + 7 * s, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = css(env.fade(mix('#fff3d6', pal.window, 0.35), 0.3));
  ctx.beginPath(); ctx.arc(x + w / 2, cy, cr, 0, Math.PI * 2); ctx.fill();
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.35;
  ctx.drawImage(glowSprite(pal.window), x + w / 2 - cr * 2.2, cy - cr * 2.2, cr * 4.4, cr * 4.4);
  ctx.restore();
  ctx.strokeStyle = css(shade(stone, -0.5));
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    ctx.lineWidth = (i % 3 === 0 ? 4 : 2) * s;
    ctx.beginPath();
    ctx.moveTo(x + w / 2 + Math.cos(a) * cr * 0.8, cy + Math.sin(a) * cr * 0.8);
    ctx.lineTo(x + w / 2 + Math.cos(a) * cr * 0.95, cy + Math.sin(a) * cr * 0.95);
    ctx.stroke();
  }
  env.info.clocks.push([x + w / 2, cy, cr, s]);
  // belfry
  const belT = shaftTop - h * 0.1;
  ctx.fillStyle = css(shade(stone, -0.05));
  ctx.fillRect(x + w * 0.04, belT, w * 0.92, h * 0.1);
  for (let i = 0; i < 3; i++) {
    const ax = x + w * (0.14 + i * 0.27);
    ctx.fillStyle = css(shade(stone, -0.55));
    ctx.beginPath();
    ctx.moveTo(ax, shaftTop - 8 * s);
    ctx.lineTo(ax, belT + w * 0.16);
    ctx.arc(ax + w * 0.09, belT + w * 0.16, w * 0.09, Math.PI, 0);
    ctx.lineTo(ax + w * 0.18, shaftTop - 8 * s);
    ctx.fill();
    ctx.fillStyle = css(env.fade(pal.lamp, 0.4), 0.85);
    ctx.beginPath();
    ctx.arc(ax + w * 0.09, belT + w * 0.25, w * 0.05, Math.PI, 0);
    ctx.lineTo(ax + w * 0.15, belT + w * 0.3);
    ctx.lineTo(ax + w * 0.03, belT + w * 0.3);
    ctx.fill();
  }
  // spire roof
  const roofC = env.fade(pal.copper[0]);
  ctx.fillStyle = css(roofC);
  ctx.beginPath();
  ctx.moveTo(x - w * 0.08, belT);
  ctx.lineTo(x + w / 2, belT - h * 0.14);
  ctx.lineTo(x + w * 1.08, belT);
  ctx.fill();
  ctx.fillStyle = css(shade(roofC, 0.2));
  ctx.beginPath();
  ctx.moveTo(x + w / 2, belT - h * 0.14);
  ctx.lineTo(x + w * 1.08, belT);
  ctx.lineTo(x + w * 0.62, belT);
  ctx.fill();
  ctx.strokeStyle = css(env.fade(pal.lamp, 0.4));
  ctx.lineWidth = 3 * s;
  ctx.beginPath();
  ctx.moveTo(x + w / 2, belT - h * 0.14);
  ctx.lineTo(x + w / 2, belT - h * 0.17);
  ctx.stroke();
  env.info.tops.push([x, x + w, shaftTop]);
  return belT - h * 0.17;
}

// The towering Spire Library: tapering stacked halls of lit arched windows,
// balustraded ledges, an exterior spiral staircase and a glowing needle.
export function spireLibrary(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const cx = x + w / 2;
  const stone = env.fade(mix(mix(pal.near, '#d9c7a8', 0.28), r.pick(pal.paints), 0.2));
  const secs = 7;
  const secH = (h * 0.86) / secs;
  let y = by;
  const helix = [];
  for (let i = 0; i < secs; i++) {
    const sw = w * (1 - i * 0.1);
    const sx = cx - sw / 2;
    const c = shade(stone, 0.05 * (i % 2) - 0.05);
    ctx.fillStyle = css(c);
    roughRect(ctx, r, sx, y - secH, sw, secH, 0.6);
    ctx.fill();
    ctx.save();
    ctx.beginPath(); ctx.rect(sx, y - secH, sw, secH); ctx.clip();
    posterV(ctx, r, sx, y - secH, sw, secH, shade(c, 0.15), shade(c, -0.2), 3, 2);
    // buttresses
    ctx.fillStyle = css(shade(c, 0.2));
    ctx.fillRect(sx, y - secH, sw * 0.05, secH);
    ctx.fillRect(sx + sw * 0.95, y - secH, sw * 0.05, secH);
    const colW = Math.max(18 * s, sw / Math.max(3, Math.floor(sw / (34 * s))));
    windowGrid(ctx, r, { ...env, litP: 0.85, info: env.info }, c, sx + sw * 0.06, y - secH + 8 * s, sw * 0.88, secH - 14 * s, colW, secH - 14 * s, 0, y, { arched: true, hf: 0.78, wf: 0.5 });
    ctx.restore();
    // ledge + balusters
    const ly = y - secH;
    ctx.fillStyle = css(shade(stone, 0.25));
    ctx.fillRect(sx - 10 * s, ly - 6 * s, sw + 20 * s, 9 * s);
    ctx.strokeStyle = css(shade(stone, 0.12));
    ctx.lineWidth = 2 * s;
    ctx.beginPath();
    for (let b = sx - 8 * s; b < sx + sw + 8 * s; b += 9 * s) { ctx.moveTo(b, ly - 6 * s); ctx.lineTo(b, ly - 18 * s); }
    ctx.moveTo(sx - 10 * s, ly - 18 * s); ctx.lineTo(sx + sw + 10 * s, ly - 18 * s);
    ctx.stroke();
    if (i >= 1 && i <= 5) helix.push([y, ly, sw]);
    if (s > 0.3) {
      lanternAt(ctx, env, sx - 6 * s, ly + 14 * s, 6 * s);
      lanternAt(ctx, env, sx + sw + 6 * s, ly + 14 * s, 6 * s);
    }
    y = ly - 10 * s;
  }
  // exterior spiral staircase (front half drawn over the body)
  ctx.strokeStyle = css(shade(stone, -0.45));
  ctx.lineWidth = 3 * s;
  for (const [y0, y1, sw] of helix) {
    const R = sw * 0.6;
    const steps = 40;
    ctx.beginPath();
    for (let k = 0; k <= steps; k++) {
      const a = (k / steps) * Math.PI;
      const xx = cx + Math.cos(a + Math.PI) * R * -1;
      const yy = y0 - (y0 - y1) * (k / steps);
      if (k === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
    }
    ctx.stroke();
    ctx.lineWidth = 1.5 * s;
    ctx.beginPath();
    for (let k = 0; k <= steps; k += 2) {
      const a = (k / steps) * Math.PI;
      const xx = cx - Math.cos(a) * R;
      const yy = y0 - (y0 - y1) * (k / steps);
      ctx.moveTo(xx, yy);
      ctx.lineTo(xx, yy - 14 * s);
    }
    ctx.stroke();
    ctx.lineWidth = 3 * s;
  }
  // crown + needle spire
  const cw = w * 0.32;
  ctx.fillStyle = css(env.fade(pal.copper[0]));
  ctx.beginPath();
  ctx.moveTo(cx - cw / 2, y);
  ctx.quadraticCurveTo(cx - cw * 0.2, y - h * 0.05, cx, y - h * 0.14);
  ctx.quadraticCurveTo(cx + cw * 0.2, y - h * 0.05, cx + cw / 2, y);
  ctx.fill();
  ctx.strokeStyle = css(env.fade(mix(pal.lamp, '#fff0b0', 0.4), 0.3));
  ctx.lineWidth = 3 * s;
  ctx.beginPath();
  ctx.moveTo(cx, y - h * 0.14);
  ctx.lineTo(cx, y - h * 0.2);
  ctx.stroke();
  env.info.glows.push([cx, y - h * 0.2, 30 * s]);
  env.info.library = [cx, y - h * 0.2, w, by];
  env.info.tops.push([x, x + w, by - h * 0.5]);
  return y - h * 0.2;
}

// Stacked market stalls on scaffolding.
export function stalls(ctx, r, x, by, w, h, env) {
  const { s, pal } = env;
  const rows = Math.max(1, Math.round(h / (110 * s)));
  const rh = h / rows;
  for (let i = 0; i < rows; i++) {
    const y = by - i * rh;
    let sx = x;
    while (sx < x + w - 30 * s) {
      const sw = Math.min(x + w - sx, r.range(70, 120) * s);
      stall(ctx, r, sx, y, sw, rh, env);
      sx += sw + 4 * s;
    }
    // scaffold poles
    ctx.strokeStyle = css(env.fade(shade(pal.near, 0.1)));
    ctx.lineWidth = 3 * s;
    ctx.beginPath();
    ctx.moveTo(x, y); ctx.lineTo(x, y - rh);
    ctx.moveTo(x + w, y); ctx.lineTo(x + w, y - rh);
    ctx.moveTo(x, y - rh); ctx.lineTo(x + w, y - rh);
    ctx.stroke();
  }
  env.info.tops.push([x, x + w, by - h]);
  return by - h;
}

const AWNING = ['#3f9a8e', '#e2b04a', '#6a5aa8', '#4a7ab0', '#d98a4a', '#7aa860'];
export function stall(ctx, r, x, by, w, h, env, opts = {}) {
  const { s, pal } = env;
  const box = env.fade(mix(pal.near, r.pick(pal.paints), 0.45));
  const aw = env.fade(mix(opts.awning || r.pick(AWNING), pal.near, 0.25), 0.6);
  const bh = h * 0.72;
  // body
  ctx.fillStyle = css(box);
  roughRect(ctx, r, x, by - bh, w, bh, 0.5);
  ctx.fill();
  // warm interior
  ctx.fillStyle = css(env.fade(mix(pal.window, '#ffe9b8', 0.2), 0.4));
  ctx.fillRect(x + w * 0.08, by - bh * 0.85, w * 0.84, bh * 0.5);
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.35;
  ctx.drawImage(glowSprite(pal.window), x - w * 0.2, by - bh * 1.2, w * 1.4, bh * 1.2);
  ctx.restore();
  // goods: jars, loaves, fruit, books
  for (let i = 0; i < Math.floor(w / (11 * s)); i++) {
    const gx = x + w * 0.1 + i * 11 * s + r.next() * 3;
    const gc = env.fade(mix(r.pick(['#e8c07a', '#a8c870', '#c8a0e0', '#f0d8a0', '#80b8c8']), pal.near, 0.3), 0.5);
    ctx.fillStyle = css(gc);
    ctx.beginPath();
    ctx.ellipse(gx, by - bh * 0.42, 4.5 * s, 5.5 * s, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  // counter
  ctx.fillStyle = css(shade(box, -0.3));
  ctx.fillRect(x - 2 * s, by - bh * 0.35, w + 4 * s, bh * 0.35);
  ctx.fillStyle = css(shade(box, 0.2));
  ctx.fillRect(x - 3 * s, by - bh * 0.36, w + 6 * s, 4 * s);
  // striped scalloped awning
  const ay = by - bh;
  const stripes = Math.max(3, Math.floor(w / (13 * s)));
  const sw = (w + 12 * s) / stripes;
  for (let i = 0; i < stripes; i++) {
    ctx.fillStyle = css(i % 2 ? aw : mix(aw, '#fff3dc', 0.7));
    ctx.beginPath();
    ctx.moveTo(x - 6 * s + i * sw + 4 * s, ay - h * 0.2);
    ctx.lineTo(x - 6 * s + (i + 1) * sw + 4 * s, ay - h * 0.2);
    ctx.lineTo(x - 6 * s + (i + 1) * sw, ay + 6 * s);
    ctx.arc(x - 6 * s + (i + 0.5) * sw, ay + 6 * s, sw / 2, 0, Math.PI);
    ctx.closePath();
    ctx.fill();
  }
  if (s > 0.3) lanternAt(ctx, env, x + w * 0.5, ay + 22 * s, 7 * s);
  return ay - h * 0.2;
}

// Iron truss arch bridge with lamp posts.
export function bridge(ctx, r, x0, x1, y, env, opts = {}) {
  const { s, pal } = env;
  const iron = env.fade(shade(pal.near, 0.06));
  const span = x1 - x0;
  const archH = opts.archH || span * 0.22;
  ctx.strokeStyle = css(iron);
  ctx.lineWidth = 6 * s;
  ctx.beginPath();
  ctx.moveTo(x0, y + archH);
  ctx.quadraticCurveTo((x0 + x1) / 2, y - archH * 0.2, x1, y + archH);
  ctx.stroke();
  ctx.lineWidth = 3 * s;
  ctx.beginPath();
  ctx.moveTo(x0, y + archH * 1.15);
  ctx.quadraticCurveTo((x0 + x1) / 2, y + archH * 0.1, x1, y + archH * 1.15);
  ctx.stroke();
  // lattice
  const n = Math.max(6, Math.floor(span / (26 * s)));
  ctx.lineWidth = 2 * s;
  ctx.beginPath();
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const xx = x0 + span * t;
    const ay = y + archH - (archH * 1.2) * 4 * t * (1 - t) * 0.9;
    ctx.moveTo(xx, y);
    ctx.lineTo(xx, ay);
    if (i < n) {
      const t2 = (i + 1) / n;
      const ay2 = y + archH - (archH * 1.2) * 4 * t2 * (1 - t2) * 0.9;
      ctx.moveTo(xx, y);
      ctx.lineTo(x0 + span * t2, ay2);
    }
  }
  ctx.stroke();
  // deck
  ctx.fillStyle = css(iron);
  ctx.fillRect(x0 - 6 * s, y - 4 * s, span + 12 * s, 10 * s);
  // railing
  ctx.lineWidth = 1.5 * s;
  ctx.beginPath();
  ctx.moveTo(x0, y - 20 * s); ctx.lineTo(x1, y - 20 * s);
  for (let xx = x0; xx <= x1; xx += 10 * s) { ctx.moveTo(xx, y - 4 * s); ctx.lineTo(xx, y - 20 * s); }
  ctx.stroke();
  // lamps
  for (let xx = x0 + span * 0.1; xx < x1; xx += span * 0.27) {
    ctx.lineWidth = 2.5 * s;
    ctx.beginPath(); ctx.moveTo(xx, y - 4 * s); ctx.lineTo(xx, y - 46 * s); ctx.stroke();
    lanternAt(ctx, env, xx, y - 50 * s, 6 * s);
  }
}

// Stone terrace / retaining wall: a cliff of dwellings — rows of lit arches,
// balconies, stairs and drain spouts so walls never read as empty.
export function terrace(ctx, r, x0, x1, y0, y1, env) {
  const { s, pal } = env;
  const st = env.fade(mix(pal.near, '#8a7a8a', 0.18));
  ctx.fillStyle = css(st);
  roughRect(ctx, r, x0, y0, x1 - x0, y1 - y0, 1.2);
  ctx.fill();
  ctx.save();
  ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip();
  const rowH = r.range(120, 170) * s;
  const rows = Math.min(10, Math.ceil((y1 - y0) / rowH));
  for (let row = 0; row < rows; row++) {
    const ry = y0 + row * rowH;
    const c = shade(st, (row % 2 ? -0.06 : 0.04) - row * 0.025);
    posterV(ctx, r, x0, ry, x1 - x0, rowH, shade(c, 0.1), shade(c, -0.14), 2, 2);
    ctx.strokeStyle = css(shade(st, -0.3), 0.28);
    ctx.lineWidth = 1.2 * s;
    for (let y = ry + 14 * s; y < ry + rowH; y += 18 * s) { ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke(); }
    // ledge
    ctx.fillStyle = css(shade(c, 0.22));
    ctx.fillRect(x0, ry - 3 * s, x1 - x0, 6 * s);
    const aw = r.range(40, 70) * s;
    const ah = rowH * r.range(0.5, 0.7);
    let x = x0 + r.next() * aw * 2;
    while (x < x1 - aw) {
      const kind = r.next();
      const ay = ry + rowH - ah - 8 * s;
      ctx.fillStyle = css(shade(c, -0.48));
      ctx.beginPath();
      ctx.moveTo(x, ay + ah);
      ctx.lineTo(x, ay + aw / 2);
      ctx.arc(x + aw / 2, ay + aw / 2, aw / 2, Math.PI, 0);
      ctx.lineTo(x + aw, ay + ah);
      ctx.fill();
      if (kind < 0.55) {
        const lc = env.fade(mix(pal.window, '#fff0c8', r.next() * 0.3), 0.4);
        ctx.fillStyle = css(lc, 0.92);
        ctx.beginPath();
        ctx.moveTo(x + aw * 0.18, ay + ah);
        ctx.lineTo(x + aw * 0.18, ay + aw * 0.55);
        ctx.arc(x + aw / 2, ay + aw * 0.55, aw * 0.32, Math.PI, 0);
        ctx.lineTo(x + aw * 0.82, ay + ah);
        ctx.fill();
        env.info.windows.push([x + aw * 0.18, ay + aw * 0.3, aw * 0.64, ah - aw * 0.3, 1]);
        if (s > 0.3) {
          ctx.save();
          ctx.globalCompositeOperation = 'lighter';
          ctx.globalAlpha = 0.3;
          ctx.drawImage(glowSprite(pal.window), x - aw, ay - aw * 0.5, aw * 3, aw * 3);
          ctx.restore();
        }
      }
      // balcony with rail
      if (kind > 0.7 && s > 0.3) {
        ctx.fillStyle = css(shade(c, 0.18));
        ctx.fillRect(x - 6 * s, ay + ah * 0.55, aw + 12 * s, 5 * s);
        ctx.strokeStyle = css(shade(c, 0.12));
        ctx.lineWidth = 1.5 * s;
        ctx.beginPath();
        for (let b = x - 4 * s; b <= x + aw + 4 * s; b += 7 * s) { ctx.moveTo(b, ay + ah * 0.55); ctx.lineTo(b, ay + ah * 0.55 - 12 * s); }
        ctx.stroke();
      }
      x += aw * r.range(1.4, 2.6);
    }
    // stair zig-zag between rows
    if (r.next() < 0.7 && row < rows - 1) {
      const sx = x0 + r.next() * (x1 - x0);
      ctx.strokeStyle = css(shade(c, 0.2));
      ctx.lineWidth = 3 * s;
      ctx.beginPath();
      for (let k = 0; k < 6; k++) {
        ctx.moveTo(sx + k * 10 * s, ry + rowH - k * (rowH / 6));
        ctx.lineTo(sx + (k + 1) * 10 * s, ry + rowH - k * (rowH / 6));
        ctx.lineTo(sx + (k + 1) * 10 * s, ry + rowH - (k + 1) * (rowH / 6));
      }
      ctx.stroke();
    }
    // drain spouts / thin waterfalls
    if (r.next() < 0.5) {
      const wx = x0 + r.next() * (x1 - x0);
      const g = ctx.createLinearGradient(0, ry, 0, ry + rowH * 1.6);
      g.addColorStop(0, css(mix(pal.water, '#e8f4ff', 0.45), 0.7));
      g.addColorStop(1, css(mix(pal.water, '#e8f4ff', 0.45), 0));
      ctx.fillStyle = g;
      ctx.fillRect(wx, ry + 4 * s, 6 * s, rowH * 1.6);
    }
  }
  ctx.restore();
  ctx.fillStyle = css(shade(st, 0.22));
  ctx.fillRect(x0, y0 - 3 * s, x1 - x0, 7 * s);
}

// Canal: posterised water with streaky reflections of the lights above.
export function canal(ctx, r, x0, x1, y0, y1, env) {
  const { s, pal } = env;
  const wc = env.fade(pal.water);
  ctx.save();
  ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip();
  posterV(ctx, r, x0, y0, x1 - x0, y1 - y0, shade(wc, 0.18), shade(wc, -0.3), 4, 2);
  // reflections
  for (const [wx, wy, ww, wh, lit] of env.info.windows) {
    if (!lit || wx < x0 || wx > x1 || wy > y0 || wy < y0 - 700 * s) continue;
    if (r.next() < 0.5) continue;
    const d = y0 - wy;
    const ry = y0 + d * 0.25;
    ctx.fillStyle = css(env.fade(pal.window, 0.4), 0.35);
    for (let k = 0; k < 4; k++) ctx.fillRect(wx + (r.next() - 0.5) * 6 * s, ry + k * 7 * s, ww * r.range(0.5, 1.2), 2.5 * s);
  }
  ctx.strokeStyle = css(shade(wc, 0.4), 0.35);
  ctx.lineWidth = 2 * s;
  for (let i = 0; i < (x1 - x0) / (30 * s); i++) {
    const xx = x0 + r.next() * (x1 - x0), yy = y0 + r.next() * (y1 - y0);
    ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + r.range(10, 30) * s, yy); ctx.stroke();
  }
  ctx.restore();
  // embankment lip
  ctx.fillStyle = css(env.fade(mix(pal.near, '#9a8a9a', 0.25)));
  ctx.fillRect(x0, y0 - 6 * s, x1 - x0, 8 * s);
}

// Laundry lines strung between neighbouring rooftops.
export function laundry(ctx, r, env, tops) {
  const { s, pal } = env;
  const cloth = ['#f2e6d0', '#a8c8d8', '#e8d08a', '#b8a8d8', '#9ad0b8', '#f0c8a8'];
  for (let i = 0; i < tops.length - 1; i++) {
    if (r.next() > 0.55) continue;
    const a = tops[i], b = tops[i + 1];
    if (b[0] - a[1] > 160 * s || b[0] - a[1] < 0) continue;
    const xA = a[1] - 4 * s, yA = a[2] + r.range(20, 120) * s;
    const xB = b[0] + 4 * s, yB = b[2] + r.range(20, 120) * s;
    const sag = r.range(14, 36) * s;
    ctx.strokeStyle = css(env.fade(shade(pal.near, 0.3)), 0.8);
    ctx.lineWidth = 1.2 * s;
    ctx.beginPath();
    ctx.moveTo(xA, yA);
    ctx.quadraticCurveTo((xA + xB) / 2, (yA + yB) / 2 + sag * 2, xB, yB);
    ctx.stroke();
    const n = Math.floor((xB - xA) / (16 * s));
    for (let k = 1; k < n; k++) {
      if (r.next() < 0.3) continue;
      const t = k / n;
      const px = xA + (xB - xA) * t;
      const py = (1 - t) * (1 - t) * yA + 2 * (1 - t) * t * ((yA + yB) / 2 + sag * 2) + t * t * yB;
      const cw = r.range(8, 14) * s, chh = r.range(10, 22) * s;
      ctx.fillStyle = css(env.fade(mix(r.pick(cloth), pal.near, 0.25), 0.7));
      roughRect(ctx, r, px - cw / 2, py, cw, chh, 0.6);
      ctx.fill();
    }
  }
}

export const BUILDERS = { tenement, canalhouse, pagoda, greenhouse, dome, clocktower, spireLibrary, stalls };
