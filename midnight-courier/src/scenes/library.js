// SPIRE LIBRARY — climbing the vertical shaft: layered bookshelves, a central
// spiral staircase, books sliding to new shelves, a thousand pages fluttering
// like startled birds, one glowing page pointing up to the forbidden floor.
import { W, H, css, mix, shade, clamp, h1, rng, fract } from '../core/util.js';
import { bakeLayer } from '../core/citygen.js';
import { drawLayer, drawShafts, wash } from '../core/stage.js';
import { pageBird } from '../core/sprites.js';
import { drawWindow } from '../core/buildings.js';
import { glowSprite, posterV, roughRect } from '../core/paint.js';
import { win, useLayer, juno } from './common.js';

export const CAM = { x0: -700, x1: 700, y0: -7000, y1: 700 };
const BOOKS = ['#3f7f86', '#d2a246', '#6a4f86', '#e9dcc0', '#4a5f8a', '#7f8a4a', '#9a6a8a', '#c07a3a', '#2f5a5a', '#b8a0c8'];
const STAIR_D = 2.6;
const FORBIDDEN_Y = -1720; // local y at d=4.2

function bounds(d, m = 160) {
  return { x0: Math.floor(CAM.x0 / d - W / 2 - m), x1: Math.ceil(CAM.x1 / d + W / 2 + m), y0: Math.floor(CAM.y0 / d - H / 2 - m), y1: Math.ceil(CAM.y1 / d + H / 2 + m) };
}

function shelves(ctx, r, x0, x1, y0, y1, env, slots) {
  const { s, pal } = env;
  const wood = env.fade(mix('#5a3a3a', pal.near, 0.35));
  ctx.fillStyle = css(shade(wood, -0.35));
  ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  const rowH = 92 * s;
  let row = 0;
  for (let y = y0 + rowH; y < y1; y += rowH, row++) {
    // balcony every 6 rows
    if (row % 6 === 5) {
      ctx.fillStyle = css(shade(wood, 0.15));
      ctx.fillRect(x0, y - 10 * s, x1 - x0, 14 * s);
      ctx.strokeStyle = css(env.fade(mix(pal.lamp, '#c8a060', 0.5), 0.5));
      ctx.lineWidth = 2.5 * s;
      ctx.beginPath();
      for (let x = x0; x < x1; x += 16 * s) { ctx.moveTo(x, y - 10 * s); ctx.lineTo(x, y - 44 * s); }
      ctx.moveTo(x0, y - 44 * s); ctx.lineTo(x1, y - 44 * s);
      ctx.stroke();
      for (let x = x0 + r.next() * 300 * s; x < x1; x += r.range(280, 520) * s) {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        ctx.globalAlpha = 0.55;
        ctx.drawImage(glowSprite(pal.lamp), x - 70 * s, y - 120 * s, 140 * s, 140 * s);
        ctx.restore();
        ctx.fillStyle = css(mix(pal.lamp, '#fff1c0', 0.35));
        ctx.beginPath(); ctx.ellipse(x, y - 56 * s, 9 * s, 12 * s, 0, 0, Math.PI * 2); ctx.fill();
        env.info.lanterns.push([x, y - 56 * s, 10 * s]);
      }
      continue;
    }
    // books
    let x = x0 + r.next() * 10 * s;
    while (x < x1) {
      const bw = r.range(9, 24) * s, bh = r.range(48, 76) * s;
      if (r.next() < 0.06) { x += r.range(20, 50) * s; continue; }
      const c = env.fade(mix(r.pick(BOOKS), pal.near, 0.25 + r.next() * 0.2), 0.8);
      const lean = r.next() < 0.08 ? r.range(-0.3, 0.3) : 0;
      ctx.save();
      ctx.translate(x + bw / 2, y);
      ctx.rotate(lean);
      ctx.fillStyle = css(c);
      ctx.fillRect(-bw / 2, -bh, bw, bh);
      ctx.fillStyle = css(shade(c, 0.3));
      ctx.fillRect(-bw / 2, -bh * 0.8, bw, 3 * s);
      ctx.fillRect(-bw / 2, -bh * 0.25, bw, 3 * s);
      ctx.fillStyle = css(shade(c, -0.25));
      ctx.fillRect(bw / 2 - 2 * s, -bh, 2 * s, bh);
      ctx.restore();
      if (slots && r.next() < 0.03) slots.push([x, y, bw, bh, c]);
      x += bw + 1.5 * s;
    }
    ctx.fillStyle = css(shade(wood, 0.1));
    ctx.fillRect(x0, y, x1 - x0, 8 * s);
  }
  // vertical posts
  ctx.fillStyle = css(shade(wood, 0.05));
  for (let x = x0; x < x1; x += 420 * s) ctx.fillRect(x, y0, 16 * s, y1 - y0);
}

export function build(pal, opts = {}, seed = 51) {
  const L = [];
  // back wall with tall moonlit windows
  L.push(bakeLayer(7, bounds(7), pal, (ctx, r, env, b) => {
    const wall = mix(pal.near, pal.sky[2], 0.35);
    posterV(ctx, r, b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0, shade(wall, 0.1), shade(wall, -0.2), 8, 6);
    for (let y = b.y0 + 200; y < b.y1; y += 700) {
      for (let x = b.x0 + 120; x < b.x1 - 100; x += 360) {
        ctx.fillStyle = css(mix(pal.sky[3], '#dfe6ff', 0.25));
        ctx.beginPath(); ctx.moveTo(x, y + 420); ctx.lineTo(x, y + 80); ctx.arc(x + 80, y + 80, 80, Math.PI, 0); ctx.lineTo(x + 160, y + 420); ctx.fill();
        ctx.strokeStyle = css(shade(wall, -0.3)); ctx.lineWidth = 6;
        ctx.beginPath(); ctx.moveTo(x + 80, y); ctx.lineTo(x + 80, y + 420); ctx.moveTo(x, y + 220); ctx.lineTo(x + 160, y + 220); ctx.stroke();
        env.info.glows.push([x + 80, y + 200, 60]);
      }
    }
  }, { seed: seed, s: 0.3, depthT: 0.6, rim: false, shadow: 0 }));
  // far ring of shelves + the forbidden floor
  L.push(bakeLayer(4.2, bounds(4.2), pal, (ctx, r, env, b) => {
    const slots = (env.info.slots = []);
    shelves(ctx, r, b.x0, b.x1, FORBIDDEN_Y + 260, b.y1, env, slots);
    // forbidden floor: dark gallery, iron gate, chains, gold light leaking
    const gy = FORBIDDEN_Y;
    ctx.fillStyle = css(shade(pal.near, -0.2));
    ctx.fillRect(b.x0, b.y0, b.x1 - b.x0, gy + 260 - b.y0);
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.85;
    ctx.drawImage(glowSprite('#ffc43d', 256, 1.3), -420, gy - 380, 840, 700);
    ctx.restore();
    ctx.fillStyle = css(mix('#ffd77a', '#fff4d0', 0.4));
    ctx.beginPath(); ctx.moveTo(-150, gy + 240); ctx.lineTo(-150, gy - 40); ctx.arc(0, gy - 40, 150, Math.PI, 0); ctx.lineTo(150, gy + 240); ctx.fill();
    ctx.strokeStyle = css(shade(pal.near, -0.3));
    ctx.lineWidth = 12;
    ctx.beginPath();
    for (let x = -140; x <= 140; x += 35) { ctx.moveTo(x, gy + 240); ctx.lineTo(x, gy - 150 + Math.abs(x) * 0.5); }
    ctx.moveTo(-150, gy + 60); ctx.lineTo(150, gy + 60);
    ctx.stroke();
    // chains
    ctx.strokeStyle = css(mix(pal.near, '#9a9ab0', 0.4));
    ctx.lineWidth = 5;
    for (let k = 0; k < 18; k++) {
      ctx.beginPath(); ctx.ellipse(-150 + k * 17, gy + 70 + Math.sin(k / 17 * Math.PI) * 40, 10, 6, 0.3, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(150 - k * 17, gy + 70 + Math.sin(k / 17 * Math.PI) * 40, 10, 6, -0.3, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.fillStyle = '#c98f2a';
    ctx.fillRect(-28, gy + 90, 56, 60);
    ctx.beginPath(); ctx.arc(0, gy + 90, 22, Math.PI, 0); ctx.lineWidth = 9; ctx.strokeStyle = '#c98f2a'; ctx.stroke();
    // carved arch
    ctx.strokeStyle = css(mix(pal.near, '#d8c8a8', 0.35)); ctx.lineWidth = 22;
    ctx.beginPath(); ctx.moveTo(-190, gy + 260); ctx.lineTo(-190, gy - 40); ctx.arc(0, gy - 40, 190, Math.PI, 0); ctx.lineTo(190, gy + 260); ctx.stroke();
    // galleries of shelves either side above
    shelves(ctx, r, b.x0, -260, b.y0, gy + 250, env, null);
    shelves(ctx, r, 260, b.x1, b.y0, gy + 250, env, null);
  }, { seed: seed + 1, s: 0.55, depthT: 0.3, rim: true, shadow: 0.3 }));
  // central spiral staircase
  L.push(bakeLayer(STAIR_D, bounds(STAIR_D), pal, (ctx, r, env, b) => {
    const stone = mix(pal.near, '#c8b8a0', 0.25);
    const R = 260, pitch = 340; // per half turn
    const yTop = b.y0, yBot = b.y1;
    const step = (y, th) => [Math.cos(th) * R, y];
    const turns = Math.ceil((yBot - yTop) / pitch);
    // back half (darker)
    const drawHalf = (front) => {
      for (let tIdx = 0; tIdx < turns * 2; tIdx++) {
        for (let k = 0; k < 14; k++) {
          const th = tIdx * Math.PI + (k / 14) * Math.PI;
          if ((Math.sin(th) > 0) !== front) continue;
          const y = yBot - (th / Math.PI) * pitch;
          const [x] = step(y, th);
          ctx.fillStyle = css(shade(stone, front ? 0.05 + Math.sin(th) * 0.12 : -0.35));
          ctx.fillRect(x - 46, y - 10, 92, 16);
          ctx.fillStyle = css(shade(stone, front ? -0.25 : -0.5));
          ctx.fillRect(x - 46, y + 6, 92, 8);
        }
      }
      // railing
      ctx.strokeStyle = css(front ? mix(pal.lamp, '#7a5a30', 0.5) : shade(stone, -0.45));
      ctx.lineWidth = front ? 5 : 3;
      ctx.beginPath();
      let started = false;
      for (let th = 0; th < turns * 2 * Math.PI; th += 0.05) {
        const y = yBot - (th / Math.PI) * pitch - 70;
        if ((Math.sin(th) > 0) !== front) { started = false; continue; }
        const x = Math.cos(th) * (R + 40);
        if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };
    drawHalf(false);
    // central column with lamps
    ctx.fillStyle = css(shade(stone, -0.15));
    ctx.fillRect(-60, yTop, 120, yBot - yTop);
    ctx.fillStyle = css(shade(stone, 0.12));
    ctx.fillRect(-60, yTop, 24, yBot - yTop);
    for (let y = yBot - 200; y > yTop; y -= 520) {
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.6;
      ctx.drawImage(glowSprite(pal.lamp), -90, y - 90, 180, 180); ctx.restore();
      ctx.fillStyle = css(mix(pal.lamp, '#fff1c0', 0.4));
      ctx.beginPath(); ctx.ellipse(0, y, 16, 22, 0, 0, Math.PI * 2); ctx.fill();
    }
    drawHalf(true);
    env.info.helix = { R, pitch, yBot };
  }, { seed: seed + 2, s: 1, depthT: 0.12, rim: true, shadow: 0.5 }));
  // near framing shelves left & right
  L.push(bakeLayer(1.6, bounds(1.6), pal, (ctx, r, env, b) => {
    shelves(ctx, r, b.x0, b.x0 + 360, b.y0, b.y1, env, null);
    shelves(ctx, r, b.x1 - 360, b.x1, b.y0, b.y1, env, null);
    // rolling ladder
    ctx.strokeStyle = css(mix('#6a4a2a', pal.near, 0.3)); ctx.lineWidth = 10;
    ctx.beginPath(); ctx.moveTo(b.x1 - 300, b.y0); ctx.lineTo(b.x1 - 220, b.y1); ctx.moveTo(b.x1 - 220, b.y0); ctx.lineTo(b.x1 - 140, b.y1); ctx.stroke();
    ctx.lineWidth = 6;
    for (let y = b.y0; y < b.y1; y += 60) { ctx.beginPath(); ctx.moveTo(b.x1 - 300 + (y - b.y0) / (b.y1 - b.y0) * 80, y); ctx.lineTo(b.x1 - 220 + (y - b.y0) / (b.y1 - b.y0) * 80, y); ctx.stroke(); }
  }, { seed: seed + 3, s: 1.1, depthT: 0.02, rim: true, shadow: 0.55 }));
  return { layers: L, pal };
}

export function render(ctx, f, st) {
  const { cam, fx, pal } = f;
  const L = st.layers;
  for (let i = 0; i < L.length; i++) {
    drawLayer(ctx, L[i], cam);
    if (i === 0) {
      // moonlight shafts through the tall windows
      drawShafts(ctx, mix(pal.rim, '#ffffff', 0.3), W * 0.2, -100, f.pt, { alpha: 0.07, n: 4, angle: Math.PI * 0.38, spread: 0.12, w1: 200 });
      wash(ctx, pal.haze, 0.18);
    }
    if (i === 1) {
      useLayer(ctx, 4.2, cam);
      slidingBooks(ctx, L[i], f);
      wash(ctx, pal.haze, 0.1);
      useLayer(ctx, 3.4, cam);
      pagesFlock(ctx, f, 70, 3.4, 18, 0.35);
    }
    if (i === 2) {
      useLayer(ctx, STAIR_D, cam);
      if (fx.juno) climbingJuno(ctx, f, L[i], fx.juno);
      useLayer(ctx, 2.1, cam);
      pagesFlock(ctx, f, fx.pages ?? 36, 2.1, 34, 1);
      if (fx.pointer) pointerPage(ctx, f, fx.pointer);
    }
  }
  // dust motes
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  for (let i = 0; i < 60; i++) {
    const x = (h1(i, 1) * W + Math.sin(f.pt * 0.4 + i) * 30 + W) % W;
    const y = ((h1(i, 2) * H - f.pt * 8 - cam.y / 4) % H + H) % H;
    ctx.fillStyle = `rgba(255,232,180,${0.25 + 0.3 * Math.sin(f.pt * 2 + i)})`;
    ctx.fillRect(x, y, 3, 3);
  }
}

function slidingBooks(ctx, L, f) {
  const slots = L.info.slots || [];
  const fast = f.fx.booksFast ? 2.2 : 1;
  for (let i = 0; i < slots.length; i++) {
    const [x, y, w, h, c] = slots[i];
    const ph = fract(f.pt * 0.16 * fast + h1(i, 3));
    if (ph > 0.6) continue;
    const k = ph / 0.6;
    const out = Math.sin(Math.min(1, k * 3) * Math.PI / 2) * (k < 0.8 ? 1 : (1 - k) / 0.2);
    const target = slots[(i + 7) % slots.length];
    const tx = x + (target[0] - x) * clamp((k - 0.25) / 0.5) * 0.3;
    const ty = y + (target[1] - y) * clamp((k - 0.25) / 0.5) * 0.3;
    // the empty gap left behind
    ctx.fillStyle = 'rgba(10,6,20,0.7)';
    ctx.fillRect(x, y - h, w, h);
    ctx.save();
    ctx.translate(tx + w / 2 + out * 20, ty - out * 30);
    ctx.rotate(out * 0.25 * (i % 2 ? 1 : -1));
    ctx.fillStyle = css(c);
    ctx.fillRect(-w / 2, -h, w, h);
    ctx.fillStyle = css(shade(c, 0.35));
    ctx.fillRect(-w / 2, -h * 0.75, w, 3);
    ctx.restore();
  }
}

function pagesFlock(ctx, f, n, d, size, alpha) {
  const { cam, fx } = f;
  const burst = fx.burst ? win(f.p, fx.burst[0], fx.burst[1]) : 0.3;
  const cy = cam.y / d, cx = cam.x / d;
  ctx.globalAlpha = alpha;
  for (let i = 0; i < n; i++) {
    const sp = 0.25 + h1(i, 21) * 0.5 + burst * 0.8;
    const ang = h1(i, 22) * Math.PI * 2 + f.pt * sp;
    const rad = 140 + h1(i, 23) * 420 + burst * 160;
    const x = cx + Math.cos(ang) * rad;
    const y = cy + 600 - fract(h1(i, 24) + f.pt * 0.05 * (1 + burst * 2)) * 1700 + Math.sin(ang) * 90;
    pageBird(ctx, x, y, size * (0.7 + h1(i, 25) * 0.6), f.pt * (1 + burst), i * 1.3, f.pal);
  }
  ctx.globalAlpha = 1;
}

function pointerPage(ctx, f, pt) {
  const { cam } = f;
  const d = 2.1;
  const k = win(f.p, pt[0], pt[1]);
  const fly = win(f.p, pt[1], 1, (x) => x * x);
  const x = cam.x / d + 0 + Math.sin(f.t * 2) * 6;
  const y = cam.y / d - 60 - fly * 1400;
  ctx.save();
  ctx.translate(x, y);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.6 + 0.4 * k;
  ctx.drawImage(glowSprite('#ffd36a', 256, 1.4), -240, -240, 480, 480);
  ctx.restore();
  // a page folded into an arrow, pointing up
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate((1 - k) * 1.4);
  ctx.scale(1.4, 1.4);
  ctx.fillStyle = '#fff3d0';
  ctx.beginPath();
  ctx.moveTo(0, -90); ctx.lineTo(55, -20); ctx.lineTo(20, -20); ctx.lineTo(20, 70); ctx.lineTo(-20, 70); ctx.lineTo(-20, -20); ctx.lineTo(-55, -20);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = 'rgba(120,80,40,0.45)';
  ctx.lineWidth = 2;
  for (let l = 0; l < 5; l++) { ctx.beginPath(); ctx.moveTo(-14, -6 + l * 14); ctx.lineTo(14, -6 + l * 14); ctx.stroke(); }
  ctx.strokeStyle = '#ffc43d'; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(0, -90); ctx.lineTo(0, 70); ctx.stroke();
  ctx.restore();
}

function climbingJuno(ctx, f, L, j) {
  const hx = L.info.helix;
  const th = (j.th0 ?? 0.3) + ((j.th1 ?? 2.8) - (j.th0 ?? 0.3)) * win(f.p, 0, 1, (x) => x);
  const y = hx.yBot - (th / Math.PI) * hx.pitch - 10 + (j.dy ?? 0);
  const x = Math.cos(th) * hx.R;
  const facing = -Math.sin(th) >= 0 ? 1 : -1;
  juno(ctx, x, y, j.h || 120, f, { mode: 'climb', phase: th * 9, facing, vx: 1.4 * (j.h || 120), wind: 0.3 });
}

export { roughRect, drawWindow };
