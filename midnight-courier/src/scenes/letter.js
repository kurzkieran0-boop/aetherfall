// LETTER — close-ups on the envelope and the letter: no address, a drawing of
// a golden door, handwriting that writes itself in, and the envelope opening.
import { W, H, css, mix, shade, clamp, h1, makeCanvas, rng } from '../core/util.js';
import { bakeLayer } from '../core/citygen.js';
import { drawLayer } from '../core/stage.js';
import { glowSprite, roughPath, posterV, brushTexture, grainTile } from '../core/paint.js';
import { SCARF } from '../core/palettes.js';
import { win, useLayer } from './common.js';

export const CAM = { x0: -700, x1: 700, y0: -900, y1: 900 };
const PAPER_D = 1.4;
const INK = '#2a1a3a';
const GOLDINK = '#e8b23a';

export function build(pal, opts = {}, seed = 41) {
  const paper = mix('#f6ead2', pal.window, 0.08);
  // envelope (front) and letter sheet, baked with deckled edges & grain
  const env = makeCanvas(900, 640);
  {
    const g = env.getContext('2d');
    const r = rng(seed);
    roughPath(g, r, [[10, 10], [890, 10], [890, 630], [10, 630]], 3, 12);
    g.fillStyle = css(paper); g.fill();
    g.save(); g.clip();
    posterV(g, r, 0, 0, 900, 640, shade(paper, 0.06), shade(paper, -0.1), 4, 3);
    brushTexture(g, r, 0, 0, 900, 640, shade(paper, -0.25), 120, 0.08, 30, 3, true);
    g.globalAlpha = 0.45; g.fillStyle = g.createPattern(grainTile(), 'repeat'); g.fillRect(0, 0, 900, 640);
    g.restore();
    g.strokeStyle = css(shade(paper, -0.18)); g.lineWidth = 3;
    g.beginPath(); g.moveTo(14, 14); g.lineTo(450, 330); g.lineTo(886, 14); g.stroke();
  }
  const sheet = makeCanvas(860, 1180);
  {
    const g = sheet.getContext('2d');
    const r = rng(seed + 1);
    roughPath(g, r, [[8, 8], [852, 8], [852, 1172], [8, 1172]], 3.5, 10);
    g.fillStyle = css(paper); g.fill();
    g.save(); g.clip();
    posterV(g, r, 0, 0, 860, 1180, shade(paper, 0.07), shade(paper, -0.12), 5, 3);
    brushTexture(g, r, 0, 0, 860, 1180, shade(paper, -0.22), 160, 0.07, 30, 3, true);
    g.globalAlpha = 0.5; g.fillStyle = g.createPattern(grainTile(), 'repeat'); g.fillRect(0, 0, 860, 1180);
    g.globalAlpha = 1;
    // fold creases
    for (const y of [393, 786]) {
      g.fillStyle = 'rgba(80,60,80,0.10)'; g.fillRect(0, y - 4, 860, 8);
      g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(0, y + 4, 860, 2);
    }
    g.restore();
  }
  // background: night city bokeh + satchel leather
  const bgB = { x0: -1000, x1: 1000, y0: -1500, y1: 1500 };
  const bg = bakeLayer(4, bgB, pal, (ctx, r, e, b) => {
    const gr = ctx.createLinearGradient(0, b.y0, 0, b.y1);
    gr.addColorStop(0, css(shade(pal.sky[1], -0.2)));
    gr.addColorStop(1, css(shade(pal.near, 0.05)));
    ctx.fillStyle = gr; ctx.fillRect(b.x0, b.y0, b.x1 - b.x0, b.y1 - b.y0);
    for (let i = 0; i < 70; i++) {
      const x = r.range(b.x0, b.x1), y = r.range(b.y0, b.y1), rr = r.range(30, 140);
      const c = r.pick([pal.window, pal.lamp, pal.copper[1], pal.rim]);
      ctx.globalAlpha = r.range(0.12, 0.4);
      ctx.drawImage(glowSprite(c, 128, 0.9), x - rr, y - rr, rr * 2, rr * 2);
    }
    ctx.globalAlpha = 1;
  }, { finish: false });
  const bagB = { x0: -1000, x1: 1000, y0: -1400, y1: 1400 };
  const bag = bakeLayer(2.2, bagB, pal, (ctx, r, e) => {
    const leather = '#7a5230';
    ctx.fillStyle = css(leather);
    roughPath(ctx, r, [[-900, 380], [900, 330], [950, 1400], [-950, 1400]], 6, 30);
    ctx.fill();
    ctx.save(); ctx.clip();
    posterV(ctx, r, -950, 330, 1900, 900, shade(leather, 0.15), shade(leather, -0.35), 5, 6);
    brushTexture(ctx, r, -950, 330, 1900, 1000, shade(leather, -0.4), 300, 0.12, 40, 4, true);
    ctx.restore();
    ctx.strokeStyle = css(shade(leather, 0.3)); ctx.lineWidth = 5; ctx.setLineDash([16, 12]);
    ctx.beginPath(); ctx.moveTo(-900, 420); ctx.lineTo(900, 370); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#d9a441'; ctx.fillRect(-60, 360, 120, 70);
    ctx.fillStyle = '#7a5a20'; ctx.fillRect(-30, 380, 60, 30);
  }, { seed: seed + 3, s: 1, rim: true, shadow: 0.5 });
  return { env, sheet, bg, bag, pal };
}

export function render(ctx, f, st) {
  const { cam, fx, pal } = f;
  drawLayer(ctx, st.bg, cam);
  // slow drifting bokeh
  useLayer(ctx, 3, cam);
  for (let i = 0; i < 26; i++) {
    const x = (h1(i, 1) - 0.5) * 1800 + Math.sin(f.pt * 0.3 + i) * 40;
    const y = (h1(i, 2) - 0.5) * 2600 - ((f.pt * 12 * (1 + h1(i, 3))) % 400);
    const r = 30 + h1(i, 4) * 90;
    ctx.globalAlpha = 0.12 + 0.12 * Math.sin(f.pt + i);
    ctx.drawImage(glowSprite(i % 2 ? pal.window : pal.copper[1], 128, 0.9), x - r, y - r, r * 2, r * 2);
  }
  ctx.globalAlpha = 1;
  if (fx.bag !== false) drawLayer(ctx, st.bag, cam);
  useLayer(ctx, PAPER_D, cam);
  const mode = fx.mode || 'envelope';
  ctx.shadowColor = 'rgba(10,5,25,0.55)';
  ctx.shadowBlur = 40;
  ctx.shadowOffsetY = 22;
  if (mode === 'envelope') envelopeFront(ctx, st, f);
  else if (mode === 'open') openEnvelope(ctx, st, f);
  else sheet(ctx, st, f);
  ctx.shadowColor = 'transparent';
  // gloved fingers holding the paper
  if (fx.hands !== false) hands(ctx, f, mode);
  // warm lamp light + dust
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.18;
  ctx.drawImage(glowSprite(pal.lamp, 256, 1.4), -300, -500, 1400, 1400);
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
  for (let i = 0; i < 40; i++) {
    const x = (h1(i, 9) * W + f.pt * 10 * (h1(i, 10) - 0.5)) % W;
    const y = (h1(i, 11) * H - f.pt * 14 * h1(i, 12) + H) % H;
    ctx.fillStyle = `rgba(255,236,190,${0.25 + 0.25 * Math.sin(f.pt * 2 + i)})`;
    ctx.fillRect(x, y, 2.5, 2.5);
  }
}

function envelopeFront(ctx, st, f) {
  const { fx } = f;
  const x0 = -450, y0 = -330;
  ctx.drawImage(st.env, x0, y0);
  ctx.shadowColor = 'transparent';
  // empty address lines
  ctx.strokeStyle = 'rgba(42,26,58,0.35)';
  ctx.lineWidth = 3;
  for (let i = 0; i < 3; i++) {
    ctx.beginPath(); ctx.moveTo(x0 + 330, y0 + 380 + i * 70); ctx.lineTo(x0 + 800, y0 + 380 + i * 70); ctx.stroke();
  }
  // question marks pop in where the address should be
  const q = fx.question ? win(f.p, fx.question[0], fx.question[1]) : 0;
  ctx.font = '120px Caveat';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'alphabetic';
  for (let i = 0; i < 3; i++) {
    const k = clamp(q * 3 - i);
    if (k <= 0) continue;
    ctx.save();
    ctx.translate(x0 + 420 + i * 150, y0 + 440 + (i % 2) * 40);
    ctx.rotate((i - 1) * 0.2);
    ctx.scale(0.4 + k * 0.6, 0.4 + k * 0.6);
    ctx.fillStyle = css(INK, 0.85 * k);
    ctx.fillText('?', 0, 0);
    ctx.restore();
  }
  // stamp: a tiny golden door
  stampDoor(ctx, x0 + 730, y0 + 110, 1, f);
  // postmark
  ctx.save();
  ctx.translate(x0 + 600, y0 + 130);
  ctx.rotate(-0.25);
  ctx.strokeStyle = 'rgba(60,40,90,0.45)';
  ctx.lineWidth = 4;
  ctx.beginPath(); ctx.arc(0, 0, 62, 0, Math.PI * 2); ctx.stroke();
  ctx.font = '34px "Lilita One"';
  ctx.fillStyle = 'rgba(60,40,90,0.5)';
  ctx.fillText('MIDNIGHT', 0, 12);
  ctx.restore();
  // gold wax seal (not red — red belongs to Juno's scarf)
  seal(ctx, x0 + 120, y0 + 520, 1);
}

function seal(ctx, x, y, s) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = '#c98f2a';
  ctx.beginPath();
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2, r = (i % 2 ? 56 : 62) * s;
    if (i === 0) ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r); else ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  ctx.fill();
  ctx.fillStyle = '#e8b54a';
  ctx.beginPath(); ctx.arc(0, 0, 42 * s, 0, Math.PI * 2); ctx.fill();
  doorGlyph(ctx, 0, 6 * s, 26 * s, '#9a6a1a', null, 1);
  ctx.restore();
}

function stampDoor(ctx, x, y, s, f) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = '#efe2c8';
  ctx.fillRect(-60, -75, 120, 150);
  ctx.strokeStyle = 'rgba(60,40,90,0.4)';
  ctx.setLineDash([6, 6]);
  ctx.lineWidth = 3;
  ctx.strokeRect(-56, -71, 112, 142);
  ctx.setLineDash([]);
  ctx.fillStyle = mixCss(f.pal.sky[1], 0);
  ctx.fillRect(-48, -63, 96, 126);
  doorGlyph(ctx, 0, 20, 38, '#ffc43d', '#ffe9a0', 1);
  ctx.restore();
}
const mixCss = (c) => css(c);

// Arched door glyph; progress k draws the ink outline, then the gold fills in.
function doorGlyph(ctx, x, y, s, ink, gold, k = 1, gk = 1) {
  ctx.save();
  ctx.translate(x, y);
  const w = s, h = s * 1.7;
  const path = () => {
    ctx.beginPath();
    ctx.moveTo(-w, h * 0.5);
    ctx.lineTo(-w, -h * 0.2);
    ctx.arc(0, -h * 0.2, w, Math.PI, 0);
    ctx.lineTo(w, h * 0.5);
    ctx.closePath();
  };
  if (gold && gk > 0) {
    path();
    ctx.fillStyle = css(gold, gk);
    ctx.fill();
  }
  ctx.strokeStyle = ink;
  ctx.lineWidth = Math.max(2, s * 0.08);
  ctx.lineCap = 'round';
  const perim = 2 * h * 0.7 + Math.PI * w + 2 * w;
  ctx.setLineDash([perim * k, perim]);
  path();
  ctx.stroke();
  ctx.setLineDash([]);
  if (k > 0.8) {
    ctx.globalAlpha = (k - 0.8) / 0.2;
    ctx.beginPath(); ctx.moveTo(0, -h * 0.2 - w); ctx.lineTo(0, h * 0.5); ctx.stroke();
    ctx.beginPath(); ctx.arc(w * 0.35, h * 0.12, s * 0.09, 0, Math.PI * 2); ctx.fillStyle = ink; ctx.fill();
    ctx.beginPath(); ctx.arc(0, -h * 0.2, w * 0.55, Math.PI, 0); ctx.stroke();
  }
  ctx.restore();
}

// Letter sheet with optional door drawing + handwriting lines (fx.text).
function sheet(ctx, st, f) {
  const { fx } = f;
  const x0 = -430, y0 = -590;
  ctx.save();
  ctx.rotate(fx.tilt ?? -0.03);
  ctx.drawImage(st.sheet, x0, y0);
  ctx.shadowColor = 'transparent';
  if (fx.drawing) {
    const k = win(f.p, fx.drawing[0], fx.drawing[1]);
    const gk = win(f.p, fx.drawing[1], Math.min(1, fx.drawing[1] + 0.25));
    // gold leaf glow
    if (gk > 0) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = gk * (0.55 + 0.25 * Math.sin(f.t * 5));
      ctx.drawImage(glowSprite('#ffc43d', 256, 1.5), -330, -560, 660, 760);
      ctx.restore();
    }
    doorGlyph(ctx, 0, -200, 150, INK, GOLDINK, k, gk);
    if (gk > 0.2) sparkles(ctx, 0, -230, 260, f.t, gk);
  }
  for (const line of fx.text || []) {
    const k = line.at ? win(f.p, line.at[0], line.at[1], (x) => x) : 1;
    if (k <= 0) continue;
    writeLine(ctx, line.t, line.x ?? 0, line.y, line.size ?? 78, line.color || INK, k, f, line.underline);
  }
  ctx.restore();
}

function writeLine(ctx, text, x, y, size, color, k, f, underline) {
  ctx.font = `${size}px Caveat`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'alphabetic';
  const w = ctx.measureText(text).width;
  const left = x - w / 2;
  ctx.save();
  ctx.beginPath();
  ctx.rect(left - 20, y - size * 1.2, (w + 40) * k, size * 1.6);
  ctx.clip();
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
  if (underline) {
    ctx.strokeStyle = color; ctx.lineWidth = 4; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(left, y + 14); ctx.quadraticCurveTo(x, y + 26, left + w, y + 10); ctx.stroke();
  }
  ctx.restore();
  if (k > 0 && k < 1) {
    // glowing pen point
    const px = left + w * k, py = y - size * 0.25;
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.8;
    ctx.drawImage(glowSprite('#ffd36a'), px - 30, py - 30, 60, 60);
    ctx.restore();
  }
}

function sparkles(ctx, x, y, r, t, a) {
  for (let i = 0; i < 18; i++) {
    const ang = h1(i, 5) * Math.PI * 2 + t * 0.4;
    const d = r * (0.4 + h1(i, 6) * 0.7);
    const tw = Math.max(0, Math.sin(t * 6 + i * 2.3));
    const sx = x + Math.cos(ang) * d, sy = y + Math.sin(ang) * d * 1.3;
    const s = (6 + h1(i, 7) * 10) * tw * a;
    ctx.fillStyle = `rgba(255,236,170,${tw * a})`;
    ctx.beginPath();
    ctx.moveTo(sx, sy - s); ctx.lineTo(sx + s * 0.25, sy); ctx.lineTo(sx, sy + s); ctx.lineTo(sx - s * 0.25, sy); ctx.closePath();
    ctx.moveTo(sx - s, sy); ctx.lineTo(sx, sy + s * 0.25); ctx.lineTo(sx + s, sy); ctx.lineTo(sx, sy - s * 0.25); ctx.closePath();
    ctx.fill();
  }
}

function openEnvelope(ctx, st, f) {
  const k = win(f.p, 0.05, 0.45);
  const slide = win(f.p, 0.4, 0.95);
  const x0 = -450, y0 = -80;
  // letter sliding out (behind the envelope front)
  ctx.save();
  ctx.beginPath();
  ctx.rect(-470, -1400, 940, 1400 + y0 + 330);
  ctx.clip();
  ctx.drawImage(st.sheet, -400, y0 + 40 - slide * 720, 800, 1100);
  ctx.restore();
  // envelope back
  ctx.drawImage(st.env, x0, y0);
  ctx.shadowColor = 'transparent';
  // flap rotating open (scaleY from 1 to -1 around the top edge)
  ctx.save();
  ctx.translate(0, y0 + 12);
  ctx.scale(1, Math.cos(k * Math.PI));
  ctx.fillStyle = css(shade('#f2e4c8', k > 0.5 ? -0.12 : 0.02));
  ctx.beginPath(); ctx.moveTo(-444, 0); ctx.lineTo(0, 330); ctx.lineTo(444, 0); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = 'rgba(80,60,80,0.25)'; ctx.lineWidth = 3; ctx.stroke();
  if (k < 0.5) seal(ctx, 0, 300, 0.9);
  ctx.restore();
}

function hands(ctx, f, mode) {
  const glove = '#1d1832';
  const sh = Math.sin(f.t * 1.3) * 4;
  const spots = mode === 'envelope' ? [[-470, 120], [470, 140]] : mode === 'open' ? [[-470, 420], [470, 440]] : [[-450, 380], [450, 400]];
  for (const [x, y] of spots) {
    const side = x < 0 ? -1 : 1;
    ctx.save();
    ctx.translate(x, y + sh);
    ctx.scale(side, 1);
    ctx.fillStyle = glove;
    ctx.beginPath();
    ctx.ellipse(40, 120, 90, 160, -0.3, 0, Math.PI * 2);
    ctx.fill();
    // thumb over the paper edge
    ctx.beginPath();
    ctx.ellipse(-10, -10, 26, 58, 0.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(160,170,255,0.35)';
    ctx.lineWidth = 4;
    ctx.beginPath(); ctx.ellipse(40, 120, 90, 160, -0.3, -2.4, -1.2); ctx.stroke();
    // a sliver of red scarf at the cuff edge — the film's only red
    if (side < 0) {
      ctx.fillStyle = SCARF.main;
      ctx.beginPath();
      ctx.moveTo(60, 240); ctx.quadraticCurveTo(140, 220 + Math.sin(f.t * 4) * 10, 170, 300); ctx.lineTo(90, 320);
      ctx.fill();
    }
    ctx.restore();
  }
}
