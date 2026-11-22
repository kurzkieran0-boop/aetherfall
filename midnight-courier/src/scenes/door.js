// THE DOOR — the top of the Spire Library: a humming golden door on a stone
// platform above the clouds; bells swinging in the belfries; dawn creeping in;
// Juno knocks; the door swings open by itself and light floods out.
import { W, H, css, mix, shade, clamp, h1, rng } from '../core/util.js';
import { genCityLayer, bakeLayer } from '../core/citygen.js';
import { drawSky, drawLayer, drawFog, drawShafts, layerXf } from '../core/stage.js';
import { bell, lanternField, craneFlock, petals } from '../core/sprites.js';
import { drawWindow, makeEnv } from '../core/buildings.js';
import { glowSprite, posterV, roughRect, drawCloud, brushTexture } from '../core/paint.js';
import { win, useLayer, juno } from './common.js';

export const CAM = { x0: -1500, x1: 1500, y0: -1700, y1: 1100 };
const PLAT_D = 1.6;
const FLOOR = 150;
const DOOR = { x: 0, y: FLOOR - 153, w: 180, h: 306 }; // same glyph proportions as the drawing

function bounds(d, m = 160) {
  return { x0: Math.floor(CAM.x0 / d - W / 2 - m), x1: Math.ceil(CAM.x1 / d + W / 2 + m), y0: Math.floor(CAM.y0 / d - H / 2 - m), y1: Math.ceil(CAM.y1 / d + H / 2 + m) };
}

export function build(pal, opts = {}, seed = 61) {
  const L = [];
  L.push(genCityLayer(seed + 1, { d: 9, kind: 'mountains', y: 760, islands: 6, rim: false, shadow: 0.1, laundry: false, grain: 0.3 }, pal, CAM));
  L.push(genCityLayer(seed + 2, {
    d: 6, litP: 0.55, litVariant: !!opts.lit,
    tiers: [{ y: 820, hMin: 200, hMax: 560, wMin: 90, wMax: 200, gapMax: 12, types: { tenement: 3, dome: 2, pagoda: 2, canalhouse: 2, greenhouse: 1 } }, { y: 1060, canal: 60, hMin: 200, hMax: 500 }],
    landmarks: [{ type: 'clocktower', x: -520, w: 260, h: 2000, tier: 0 }],
  }, pal, CAM));
  // cloud bank below the platform
  L.push(bakeLayer(4, bounds(4), pal, (ctx, r, env, b) => {
    for (let i = 0; i < 26; i++) {
      const x = r.range(b.x0, b.x1), y = r.range(560, 900), w = r.range(360, 760);
      drawCloud(ctx, r, x, y, w, w * 0.32, mix(pal.cloud, pal.sky[3], r.next() * 0.4), 0.92);
    }
  }, { seed: seed + 3, rim: true, shadow: 0.2, s: 0.5 }));
  // belfries left and right
  L.push(bakeLayer(2.6, bounds(2.6), pal, (ctx, r, env, b) => {
    for (const side of [-1, 1]) {
      const cx = side * 560;
      const stone = mix(pal.near, '#c8b8a0', 0.25);
      ctx.fillStyle = css(stone);
      roughRect(ctx, r, cx - 170, -700, 340, 2000, 1);
      ctx.fill();
      ctx.save(); ctx.beginPath(); ctx.rect(cx - 170, -700, 340, 2000); ctx.clip();
      posterV(ctx, r, cx - 170, -700, 340, 1600, shade(stone, 0.15), shade(stone, -0.3), 6, 3);
      brushTexture(ctx, r, cx - 170, -700, 340, 1600, shade(stone, -0.3), 120, 0.15, 14, 3, true);
      for (let y = -200; y < 1300; y += 130) drawWindow(ctx, r, cx - 20, y, 40, 70, env, stone, { arched: true });
      ctx.restore();
      // belfry opening
      ctx.fillStyle = css(shade(stone, -0.6));
      ctx.beginPath(); ctx.moveTo(cx - 110, -380); ctx.lineTo(cx - 110, -560); ctx.arc(cx, -560, 110, Math.PI, 0); ctx.lineTo(cx + 110, -380); ctx.fill();
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.35;
      ctx.drawImage(glowSprite(pal.lamp), cx - 160, -660, 320, 320); ctx.restore();
      // copper cap
      ctx.fillStyle = css(pal.copper[0]);
      ctx.beginPath(); ctx.moveTo(cx - 200, -700); ctx.lineTo(cx, -1050); ctx.lineTo(cx + 200, -700); ctx.fill();
      ctx.fillStyle = css(pal.copper[1]);
      ctx.beginPath(); ctx.moveTo(cx, -1050); ctx.lineTo(cx + 200, -700); ctx.lineTo(cx + 60, -700); ctx.fill();
      env.info.glows.push([cx, -1060, 14]);
    }
  }, { seed: seed + 4, s: 0.9, depthT: 0.1, rim: true, shadow: 0.45 }));
  // the platform + doorway
  L.push(bakeLayer(PLAT_D, bounds(PLAT_D), pal, (ctx, r, env, b) => {
    const stone = mix(pal.near, '#d8c8b0', 0.3);
    // spire body below the platform (tapering, lit windows)
    ctx.fillStyle = css(shade(stone, -0.12));
    ctx.beginPath(); ctx.moveTo(-480, FLOOR); ctx.lineTo(480, FLOOR); ctx.lineTo(620, b.y1); ctx.lineTo(-620, b.y1); ctx.fill();
    ctx.save(); ctx.clip();
    posterV(ctx, r, -620, FLOOR, 1240, b.y1 - FLOOR, shade(stone, 0.05), shade(stone, -0.35), 6, 3);
    for (let y = FLOOR + 120; y < b.y1; y += 150) for (let x = -380; x <= 380; x += 95) drawWindow(ctx, r, x - 18, y, 36, 70, { ...env, litP: 0.8 }, stone, { arched: true });
    ctx.restore();
    // platform slab + balustrade
    ctx.fillStyle = css(shade(stone, 0.15));
    roughRect(ctx, r, -560, FLOOR, 1120, 46, 1.2); ctx.fill();
    ctx.fillStyle = css(shade(stone, -0.2));
    ctx.fillRect(-560, FLOOR + 40, 1120, 14);
    ctx.strokeStyle = css(shade(stone, 0.05));
    ctx.lineWidth = 9;
    ctx.beginPath();
    for (let x = -540; x <= 540; x += 30) { if (Math.abs(x) < 260) continue; ctx.moveTo(x, FLOOR); ctx.lineTo(x, FLOOR - 70); }
    ctx.moveTo(-560, FLOOR - 72); ctx.lineTo(-260, FLOOR - 72); ctx.moveTo(260, FLOOR - 72); ctx.lineTo(560, FLOOR - 72);
    ctx.stroke();
    // doorway: carved arch around the door
    const { x, y, w, h } = DOOR;
    ctx.fillStyle = css(shade(stone, 0.05));
    ctx.beginPath();
    ctx.moveTo(x - w - 70, FLOOR); ctx.lineTo(x - w - 70, y - h * 0.2); ctx.arc(x, y - h * 0.2, w + 70, Math.PI, 0); ctx.lineTo(x + w + 70, FLOOR);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = css(shade(stone, -0.4));
    ctx.beginPath();
    ctx.moveTo(x - w - 12, FLOOR); ctx.lineTo(x - w - 12, y - h * 0.2); ctx.arc(x, y - h * 0.2, w + 12, Math.PI, 0); ctx.lineTo(x + w + 12, FLOOR);
    ctx.closePath(); ctx.fill();
    // voussoirs
    ctx.strokeStyle = css(shade(stone, -0.2)); ctx.lineWidth = 3;
    for (let k = 0; k <= 12; k++) {
      const a = Math.PI + (k / 12) * Math.PI;
      ctx.beginPath();
      ctx.moveTo(x + Math.cos(a) * (w + 14), y - h * 0.2 + Math.sin(a) * (w + 14));
      ctx.lineTo(x + Math.cos(a) * (w + 68), y - h * 0.2 + Math.sin(a) * (w + 68));
      ctx.stroke();
    }
    // keystone with a little door glyph
    ctx.fillStyle = css(shade(stone, 0.2));
    ctx.fillRect(x - 30, y - h * 0.2 - w - 74, 60, 70);
    // pillars with lanterns
    for (const side of [-1, 1]) {
      ctx.fillStyle = css(shade(stone, 0.1));
      ctx.fillRect(side * 400 - 26, FLOOR - 330, 52, 330);
      ctx.fillStyle = css(shade(stone, 0.25));
      ctx.fillRect(side * 400 - 36, FLOOR - 344, 72, 20);
      env.info.lanterns.push([side * 400, FLOOR - 380, 16]);
    }
  }, { seed: seed + 5, s: 1, depthT: 0.02, rim: true, shadow: 0.55 }));
  return { layers: L, pal };
}

function doorPath(ctx, inset = 0) {
  const { x, y, w, h } = DOOR;
  ctx.beginPath();
  ctx.moveTo(x - w + inset, FLOOR);
  ctx.lineTo(x - w + inset, y - h * 0.2);
  ctx.arc(x, y - h * 0.2, w - inset, Math.PI, 0);
  ctx.lineTo(x + w - inset, FLOOR);
  ctx.closePath();
}

export function render(ctx, f, st) {
  const { cam, fx, pal } = f;
  const sp = f.skyPal || pal;
  const L = st.layers;
  drawSky(ctx, sp, cam, f.pt, { parallax: 40 });
  const s = sp.sun;
  drawShafts(ctx, s.glow, s.x * W, s.y * H, f.pt, { alpha: 0.07 + (fx.dawn ? 0.06 * win(f.p, fx.dawn[0], fx.dawn[1]) : 0), n: 7, angle: -Math.PI / 2, spread: 0.32, len: 2200 });
  const open = fx.doorOpen ? win(f.p, fx.doorOpen[0], fx.doorOpen[1], (x) => 1 - Math.pow(1 - x, 3)) : 0;
  const litAmt = fx.lit ? (f.p >= fx.lit[0] ? 1 : 0) : 0;
  for (let i = 0; i < L.length; i++) {
    const { visible } = drawLayer(ctx, L[i], cam, { lit: litAmt });
    if (!visible) continue;
    useLayer(ctx, L[i].d, cam);
    if (i === 1) {
      drawFog(ctx, sp, cam, f.pt, { d: 6, y: 820, h: 500, alpha: 0.4 });
      useLayer(ctx, 5, cam);
      if (!fx.freezeCranes) craneFlock(ctx, f.pt, pal, { n: 10, x0: -700, x1: 700, y: 300, spread: 500, speed: 70, size: 30 });
    }
    if (i === 3) {
      // swinging bells in both belfries
      const ring = fx.bells ? win(f.p, fx.bells[0], fx.bells[0] + 0.1) : 0.15;
      for (const side of [-1, 1]) {
        const a = Math.sin(f.pt * 2.6 + side) * 0.55 * ring;
        bell(ctx, side * 560, -560, 150, a, pal);
      }
      useLayer(ctx, 3.2, cam);
      lanternField(ctx, f.pt, pal, { n: 22, x0: -900, x1: 900, y0: -1200, y1: 900, size: 16, speed: 22 });
    }
    if (i === 4) {
      useLayer(ctx, PLAT_D, cam);
      drawDoor(ctx, f, open);
      for (const [lx, ly, ls] of L[i].info.lanterns) {
        ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = 0.7;
        ctx.drawImage(glowSprite(pal.lamp), lx - ls * 5, ly - ls * 5, ls * 10, ls * 10); ctx.restore();
        ctx.fillStyle = css(mix(pal.lamp, '#fff2c8', 0.4));
        ctx.beginPath(); ctx.ellipse(lx, ly, ls * 0.7, ls, 0, 0, Math.PI * 2); ctx.fill();
      }
      if (fx.juno) {
        const j = fx.juno;
        const knocking = fx.knock ? f.p > fx.knock[0] && f.p < fx.knock[1] : false;
        const jx = j.x0 !== undefined ? j.x0 + (j.x1 - j.x0) * win(f.p, j.a ?? 0, j.b ?? 0.6) : (j.x ?? -90);
        const walking = j.x0 !== undefined && f.p > (j.a ?? 0) && f.p < (j.b ?? 0.6);
        juno(ctx, jx, FLOOR + 2, j.h || 140, f, {
          mode: walking ? 'run' : j.mode || 'stand', facing: j.facing ?? 1, knocking,
          phase: jx / (140 * 0.9) * Math.PI * 2, vx: walking ? 150 : 0, wind: 1.5, letter: j.letter,
        });
      }
    }
  }
  if (open > 0) {
    // light floods out of the doorway
    const [sx, sy] = proj(cam, PLAT_D, DOOR.x, DOOR.y);
    drawShafts(ctx, '#fff0c0', sx, sy, f.pt, { alpha: 0.22 * open, n: 9, angle: Math.PI / 2, spread: 0.5, w0: 60, w1: 420, len: 1800 });
    drawShafts(ctx, '#ffd36a', sx, sy, f.pt, { alpha: 0.12 * open, n: 7, angle: -Math.PI / 2, spread: 0.6, w0: 60, w1: 360, len: 1500 });
  }
  if (!fx.noPetals) {
    useLayer(ctx, 0.95, cam);
    petals(ctx, f.pt, { n: 22, x0: cam.x / 0.95 - 800, x1: cam.x / 0.95 + 800, y0: cam.y / 0.95 - 1200, y1: cam.y / 0.95 + 1200, size: 10, wind: 90 });
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function proj(cam, d, lx, ly) {
  const xf = layerXf(d, cam);
  return [xf.ox + lx * xf.k, xf.oy + ly * xf.k];
}

function drawDoor(ctx, f, open) {
  const { x, y, w, h } = DOOR;
  const hum = 0.5 + 0.5 * Math.sin(f.pt * 9);
  const vib = f.fx.hum ? Math.sin(f.pt * 60) * 1.4 : 0;
  // glow behind/around the door
  ctx.save();
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.45 + 0.25 * hum + open * 0.5;
  ctx.drawImage(glowSprite('#ffc43d', 256, 1.4), x - w * 3, y - h * 2.3, w * 6, h * 4.2);
  ctx.restore();
  // interior: blinding light when open
  if (open > 0) {
    doorPath(ctx, 6);
    const g = ctx.createRadialGradient(x, y, 10, x, y, h * 1.2);
    g.addColorStop(0, '#ffffff');
    g.addColorStop(0.5, '#fff1c4');
    g.addColorStop(1, '#ffc65a');
    ctx.fillStyle = g;
    ctx.fill();
  }
  // the door leaf, hinged on the left, swinging inward
  ctx.save();
  doorPath(ctx, 6);
  ctx.clip();
  ctx.translate(x - w + vib, 0);
  const sx = Math.cos(open * Math.PI * 0.46);
  ctx.scale(sx, 1);
  ctx.translate(-(x - w), 0);
  const gold = mix('#e8a92e', '#ffd56a', hum * 0.4);
  doorPath(ctx, 6);
  ctx.fillStyle = css(shade(gold, -open * 0.35));
  ctx.fill();
  // painted panels
  ctx.strokeStyle = css(shade(gold, -0.35));
  ctx.lineWidth = 6;
  ctx.strokeRect(x - w * 0.72, y - h * 0.1, w * 0.6, h * 0.52);
  ctx.strokeRect(x + w * 0.12, y - h * 0.1, w * 0.6, h * 0.52);
  ctx.beginPath(); ctx.arc(x, y - h * 0.2, w * 0.62, Math.PI, 0); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x, y - h * 0.2 - w); ctx.lineTo(x, FLOOR); ctx.stroke();
  // highlight band
  ctx.fillStyle = 'rgba(255,250,220,0.35)';
  ctx.fillRect(x - w * 0.9, y - h * 0.2 - w, w * 0.18, h * 1.4);
  // knob
  ctx.fillStyle = '#fff1b0';
  ctx.beginPath(); ctx.arc(x + w * 0.35, y + h * 0.12, 12, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
  // hum rings
  if (f.fx.hum || f.fx.knock) {
    for (let k = 0; k < 4; k++) {
      const a = (f.pt * 0.9 + k / 4) % 1;
      ctx.strokeStyle = `rgba(255,214,110,${(1 - a) * 0.5})`;
      ctx.lineWidth = 5 * (1 - a) + 1;
      ctx.beginPath();
      ctx.arc(x, y - h * 0.05, w * (1.1 + a * 1.6), Math.PI * 1.05, Math.PI * 1.95);
      ctx.stroke();
    }
  }
  // knock ripples
  if (f.fx.knock && f.p > f.fx.knock[0] && f.p < f.fx.knock[1] + 0.1) {
    const kp = Math.max(0, Math.sin(f.pt * 16));
    ctx.strokeStyle = `rgba(255,240,200,${kp * 0.8})`;
    ctx.lineWidth = 4;
    for (let k = 1; k <= 3; k++) { ctx.beginPath(); ctx.arc(x - w * 0.45, y + h * 0.1, 14 * k * (1 + kp), 0, Math.PI * 2); ctx.stroke(); }
  }
}

export { rng, h1, clamp, makeEnv };
