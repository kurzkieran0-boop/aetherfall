// Hand-lettered captions: 2–4 words at a time, each word bounces in when it is
// spoken, key words in gold. Everything stays inside the safe area
// (top 10% and bottom 20% are never touched).
import { W, H, clamp } from './util.js';

export const SAFE = { top: Math.round(H * 0.1), bottom: Math.round(H * 0.8), side: 70 };
const FONT = '"Lilita One", "Arial Black", sans-serif';
const CREAM = '#fff3dc';
const GOLD = '#ffc43d';
const INK = '#1b1033';
const CAP_SIZE = 104;
const CAP_Y = 1330;
const MAX_W = W - SAFE.side * 2 - 40;

const backOut = (x, s = 2.6) => { x = clamp(x); const c = x - 1; return 1 + (s + 1) * c * c * c + s * c * c; };

export class Captions {
  constructor(tl, ctx) {
    this.tl = tl;
    this.groups = [];
    ctx.font = `${CAP_SIZE}px ${FONT}`;
    this.space = ctx.measureText(' ').width + CAP_SIZE * 0.22;
    for (const line of tl.lines) this.groupLine(line, ctx);
    this.overlays = tl.overlays || [];
  }

  groupLine(line, ctx) {
    const words = line.words.map((w) => ({ ...w, width: ctx.measureText(w.w).width }));
    const groups = [];
    let cur = [];
    const width = (arr) => arr.reduce((a, w) => a + w.width, 0) + this.space * (arr.length - 1);
    for (let i = 0; i < words.length; i++) {
      const w = words[i];
      if (cur.length && (cur.length >= 4 || width([...cur, w]) > MAX_W * 1.85)) { groups.push(cur); cur = []; }
      cur.push(w);
      const punct = /[,.;:!?…—]$/.test(w.w);
      if (punct && cur.length >= 2) { groups.push(cur); cur = []; }
    }
    if (cur.length) {
      if (cur.length === 1 && groups.length && groups[groups.length - 1].length < 4 && width([...groups[groups.length - 1], cur[0]]) < MAX_W * 1.85) groups[groups.length - 1].push(cur[0]);
      else groups.push(cur);
    }
    groups.forEach((g, i) => {
      const start = g[0].s - 0.06;
      const next = groups[i + 1];
      const end = next ? next[0].s - 0.06 : Math.min(line.end + 0.45, (line.nextStart ?? 1e9) - 0.05);
      this.groups.push({ words: g, start, end, rows: this.layout(g) });
    });
  }

  layout(g) {
    // one row if it fits, else split into two balanced rows
    const width = (arr) => arr.reduce((a, w) => a + w.width, 0) + this.space * (arr.length - 1);
    let rows = [g];
    if (width(g) > MAX_W && g.length > 1) {
      let best = null;
      for (let k = 1; k < g.length; k++) {
        const a = g.slice(0, k), b = g.slice(k);
        const m = Math.max(width(a), width(b));
        if (!best || m < best.m) best = { m, rows: [a, b] };
      }
      rows = best.rows;
    }
    const scale = Math.min(1, ...rows.map((r) => MAX_W / width(r)));
    const lh = CAP_SIZE * 1.08 * scale;
    const y0 = CAP_Y - ((rows.length - 1) * lh) / 2;
    const out = [];
    rows.forEach((r, ri) => {
      let x = W / 2 - (width(r) * scale) / 2;
      for (const w of r) {
        out.push({ w, cx: x + (w.width * scale) / 2, cy: y0 + ri * lh, scale });
        x += (w.width + this.space) * scale;
      }
    });
    return out;
  }

  draw(ctx, t, beatPhase = 0) {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round';
    for (const g of this.groups) {
      if (t < g.start || t >= g.end) continue;
      const fadeOut = clamp((g.end - t) / 0.08);
      for (const p of g.rows) {
        const age = t - p.w.s;
        if (age < -0.02) continue;
        const k = backOut(age / 0.2);
        const active = t >= p.w.s && t < p.w.e + 0.05;
        const sc = p.scale * (0.35 + 0.65 * k) * (active ? 1.08 : 1) * (0.9 + 0.1 * fadeOut);
        const dy = (1 - clamp(age / 0.2)) * 34 - (active ? 6 : 0);
        word(ctx, p.w.w, p.cx, p.cy + dy, CAP_SIZE * sc, p.w.key ? GOLD : CREAM, Math.max(0, fadeOut), (1 - k) * (p.w.key ? -0.06 : 0.05));
      }
    }
    for (const o of this.overlays) if (t >= o.start && t < o.end) this.drawOverlay(ctx, o, t, beatPhase);
    ctx.restore();
  }

  drawOverlay(ctx, o, t, beatPhase) {
    const age = t - o.start, left = o.end - t;
    const out = clamp(left / 0.15);
    if (o.style === 'hook') {
      // Fully visible on the very first frame; pumps on the beat.
      const pulse = 1 + 0.045 * Math.exp(-beatPhase * 7);
      const rows = o.text;
      const sizes = [150, 168, 200];
      const fitted = rows.map((row, i) => fit(ctx, row, sizes[i % sizes.length], MAX_W));
      let y = 300 + fitted[0] / 2;
      rows.forEach((row, i) => {
        const size = fitted[i];
        const wob = Math.sin(t * 9 + i * 1.3) * 0.025;
        word(ctx, row, W / 2 + Math.sin(t * 6 + i) * 4, y, size * pulse, i === rows.length - 1 ? GOLD : CREAM, out, wob);
        if (i < rows.length - 1) y += (size + fitted[i + 1]) * 0.5 * 0.92;
      });
    } else if (o.style === 'tease') {
      const k = backOut(age / 0.25, 3);
      const size = fit(ctx, o.text, 96, MAX_W) * (0.3 + 0.7 * k);
      word(ctx, o.text, W / 2, 400 + Math.sin(t * 7) * 6, size, GOLD, out, Math.sin(t * 11) * 0.05 * (1 - clamp(age)));
    } else if (o.style === 'title') {
      const k = backOut(age / 0.3);
      const a = out;
      word(ctx, 'THE MIDNIGHT COURIER', W / 2, 300, fit(ctx, 'THE MIDNIGHT COURIER', 84, MAX_W) * (0.5 + 0.5 * k), CREAM, a, 0);
      word(ctx, o.text || 'PART 1', W / 2, 395, 70 * (0.5 + 0.5 * k), GOLD, a, -0.04);
    } else if (o.style === 'end') {
      const k = backOut(age / 0.35, 3);
      word(ctx, 'THE MIDNIGHT COURIER', W / 2, 520, fit(ctx, 'THE MIDNIGHT COURIER', 78, MAX_W) * clamp(k), CREAM, out, 0);
      const pulse = 1 + 0.04 * Math.exp(-beatPhase * 6);
      word(ctx, o.text[0], W / 2, 720, fit(ctx, o.text[0], 230, MAX_W) * k * pulse, GOLD, out, Math.sin(t * 5) * 0.03);
      const k2 = backOut((age - 0.35) / 0.35, 2.4);
      if (age > 0.35) {
        word(ctx, o.text[1], W / 2, 930, fit(ctx, o.text[1], 104, MAX_W) * k2, CREAM, out, 0);
        word(ctx, o.text[2], W / 2, 1050, fit(ctx, o.text[2], 104, MAX_W) * k2, CREAM, out, 0);
      }
    }
  }
}

function fit(ctx, text, size, maxW) {
  ctx.font = `${size}px ${FONT}`;
  const w = ctx.measureText(text).width;
  return w > maxW ? (size * maxW) / w : size;
}

function word(ctx, text, x, y, size, fill, alpha = 1, rot = 0) {
  if (size < 2 || alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(x, y);
  ctx.rotate(rot);
  ctx.font = `${size}px ${FONT}`;
  // drop shadow (cut paper)
  ctx.fillStyle = 'rgba(10,5,25,0.55)';
  ctx.strokeStyle = 'rgba(10,5,25,0.55)';
  ctx.lineWidth = size * 0.19;
  ctx.strokeText(text, size * 0.03, size * 0.09);
  ctx.strokeStyle = INK;
  ctx.lineWidth = size * 0.17;
  ctx.strokeText(text, 0, 0);
  ctx.fillStyle = fill;
  ctx.fillText(text, 0, 0);
  // painted highlight on the upper half
  ctx.save();
  ctx.beginPath();
  ctx.rect(-W, -size, W * 2, size * 0.42);
  ctx.clip();
  ctx.fillStyle = 'rgba(255,255,255,0.22)';
  ctx.fillText(text, 0, 0);
  ctx.restore();
  ctx.restore();
}
