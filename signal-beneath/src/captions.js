// Word-synced terminal captions: each word types out letter by letter across its spoken span,
// with a blinking block cursor. Layout is computed from the full sentence so lines never reflow.
import { C, VT, rgba, text, measure, blink, cursor, clamp } from './draw.js';

const SIZE = 70, LH = 80, MAXW = 900, CY = 1330;

function layout(ctx, words) {
  const lines = [[]]; let w = 0;
  const sp = measure(ctx, ' ', SIZE, VT);
  for (const wd of words) {
    const ww = measure(ctx, wd.w, SIZE, VT);
    if (lines[lines.length - 1].length && w + sp + ww > MAXW) { lines.push([]); w = 0; }
    w += (lines[lines.length - 1].length ? sp : 0) + ww;
    lines[lines.length - 1].push(wd);
  }
  return lines.map((ws) => ({ ws, width: measure(ctx, ws.map((x) => x.w).join(' '), SIZE, VT) }));
}

export function drawCaptions(ctx, lt, scene, o = {}) {
  const sents = scene.voice?.sentences || [];
  let idx = -1;
  for (let i = 0; i < sents.length; i++) if (lt >= sents[i].start - 0.02) idx = i;
  if (idx < 0) return;
  const s = sents[idx];
  const next = sents[idx + 1];
  // hide during a silence window before the next (final) line
  if (next && next.silenceBefore && lt > next.start - next.silenceBefore + 0.25) return;
  const fade = o.fadeOutAt != null ? clamp((o.fadeOutAt + 0.4 - lt) / 0.4) : 1;
  if (fade <= 0) return;
  const color = s.voice ? C.mag : C.cyan;
  const lines = layout(ctx, s.words);
  const y0 = CY - ((lines.length - 1) * LH) / 2;
  // faint backing so captions read over busy scenes
  ctx.fillStyle = rgba(C.bg, 0.55 * fade);
  ctx.fillRect(70, y0 - LH * 0.75, 940, lines.length * LH + LH * 0.5 - 4);
  const sp = measure(ctx, ' ', SIZE, VT);
  let curX = null, curY = null, typing = false;
  lines.forEach((ln, li) => {
    let x = 540 - ln.width / 2; const y = y0 + li * LH;
    for (const wd of ln.ws) {
      const span = Math.max(0.06, (wd.t1 - wd.t0) * 0.85);
      const n = Math.floor(wd.w.length * clamp((lt - wd.t0) / span));
      if (n > 0) {
        const str = wd.w.slice(0, n);
        const w = text(ctx, str, x, y, { font: VT, size: SIZE, color, alpha: fade });
        curX = x + w; curY = y;
        if (n < wd.w.length) typing = true;
      }
      x += measure(ctx, wd.w, SIZE, VT) + sp;
    }
  });
  if (curX != null && (typing || blink(lt))) cursor(ctx, curX, curY, SIZE, color, 0.9 * fade);
}
