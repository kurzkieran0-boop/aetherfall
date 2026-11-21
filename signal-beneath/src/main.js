// THE SIGNAL BENEATH — series player / deterministic frame renderer.
// URL: ?ep=part1&w=1080&h=1920&export=1&t=12
import '@fontsource/vt323/400.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import { gsap } from 'gsap';
import { C, DW, DH, rgba, stroke, resetTexts, getTexts, SAFE } from './draw.js';
import { drawAmbient, drawHUD } from './ambient.js';
import { drawCaptions } from './captions.js';
import { SCENES } from './scenes.js';
import { pings, heartbeats, makeJellyClock } from './schedule.js';
import { createPost } from './post.js';
import { renderMix, toWav } from './audio.js';

const Q = new URLSearchParams(location.search);
const EP = Q.get('ep') || 'part1';
const W = Number(Q.get('w') || 1080), H = Number(Q.get('h') || 1920), S = W / DW;
const EXPORT = Q.has('export');
const TW = 1.2; // sonar-ping wipe length

async function boot() {
  const [series, tl] = await Promise.all([fetch('/series.json').then((r) => r.json()), fetch(`/episodes/${EP}/timeline.json`).then((r) => r.json())]);
  if (!tl.total) throw new Error('timeline.json has no measured durations — run `npm run timeline`');
  tl.__ep = EP;
  await Promise.all(['400 70px VT323', '400 24px "IBM Plex Mono"', '500 24px "IBM Plex Mono"'].map((f) => document.fonts.load(f)));
  await document.fonts.ready;

  const env = { series, tl, S, pings: pings(tl), beats: heartbeats(tl), jelly: makeJellyClock(tl), snowClock: (t) => t };
  // segments: cold open, title card, scenes 1..n, end card
  const segs = [];
  tl.scenes.forEach((sc, i) => {
    segs.push({ id: sc.id, type: sc.visual.type, start: sc.start, duration: sc.duration, sc, trans: 'ripple' });
    if (i === (series.template.titleCard.after ?? 0)) segs.push({ id: 'title_card', type: 'titleCard', start: tl.titleCard.start, duration: tl.titleCard.duration, sc: { id: 'title_card', visual: {}, duration: tl.titleCard.duration }, trans: 'ripple' });
  });
  segs.push({ id: 'end_card', type: 'endCard', start: tl.endCard.start, duration: tl.endCard.duration, sc: { id: 'end_card', visual: {}, duration: tl.endCard.duration }, trans: 'glitch' });
  for (const g of segs) g.state = SCENES[g.type].init?.(g.sc, env) || {};

  const mk = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const comp = mk(W, H), cA = mk(W, H), cB = mk(W, H);
  const b1 = mk(Math.round(W / 4), Math.round(H / 4)), b2 = mk(Math.round(W / 8), Math.round(H / 8));
  const out = document.getElementById('view'); out.width = W; out.height = H;
  if (EXPORT) { out.style.width = `${W}px`; out.style.height = `${H}px`; }
  const post = createPost(out, W, H);
  const ctxOf = (c) => { const x = c.getContext('2d'); x.setTransform(S, 0, 0, S, 0, 0); x.__scale = S; return x; };

  function drawSeg(c, g, t, ltOverride) {
    const ctx = ctxOf(c), def = SCENES[g.type];
    const lt = ltOverride ?? t - g.start;
    const fo = def.frame?.(lt, g.sc, g.state, env) || {};
    drawAmbient(ctx, t, env, { alpha: fo.ambient ?? 1, rings: fo.rings });
    const r = def.draw(ctx, lt, g.sc, g.state, env) || {};
    if (g.sc.voice) drawCaptions(ctx, lt, g.sc, { fadeOutAt: fo.captionsFade });
    if (g.type !== 'titleCard' && g.type !== 'endCard') drawHUD(ctx, t, env, { alpha: fo.hud ?? 1 });
    return r;
  }

  function frame(t) {
    resetTexts();
    let i = segs.findIndex((g) => t >= g.start && t < g.start + g.duration);
    if (i < 0) i = t < 0 ? 0 : segs.length - 1;
    const g = segs[i];
    let from = null, to = null, p = 0;
    if (i > 0 && g.trans === 'ripple' && t - g.start < TW / 2) { from = segs[i - 1]; to = g; p = 0.5 + (t - g.start) / TW; }
    else if (i < segs.length - 1 && segs[i + 1].trans === 'ripple' && g.start + g.duration - t < TW / 2) { from = g; to = segs[i + 1]; p = 0.5 - (g.start + g.duration - t) / TW; }
    const cx = comp.getContext('2d'); cx.setTransform(1, 0, 0, 1, 0, 0);
    let fx = {}, ringR = 0;
    if (from) {
      const fa = drawSeg(cA, from, t), fb = drawSeg(cB, to, t);
      fx = { pulse: Math.max(fa.pulse || 0, fb.pulse || 0) };
      const e = gsap.parseEase('power2.inOut')(p), R = e * (Math.hypot(DW / 2, DH / 2) + 60);
      cx.drawImage(cA, 0, 0);
      cx.save(); cx.beginPath(); cx.arc((DW / 2) * S, (DH / 2) * S, R * S, 0, Math.PI * 2); cx.clip(); cx.drawImage(cB, 0, 0); cx.restore();
      const rc = ctxOf(comp);
      for (let k = 0; k < 3; k++) { stroke(rc, C.cyan, (k ? 0.35 : 0.95) * Math.sin(Math.PI * p), 5 - k * 1.5); rc.beginPath(); rc.arc(DW / 2, DH / 2, Math.max(0, R - k * 26), 0, Math.PI * 2); rc.stroke(); }
      ringR = R * S;
    } else if (g.type === 'endCard' && t - g.start < 1 / 30 + 1e-4) {
      // one glitch frame between the cut to black and the end card
      const prev = segs[i - 1];
      fx = drawSeg(comp, prev, t, prev.duration - 1.1); fx.glitch = 1;
    } else {
      fx = drawSeg(comp, g, t);
    }
    const g1 = b1.getContext('2d'); g1.filter = 'blur(3px)'; g1.clearRect(0, 0, b1.width, b1.height); g1.drawImage(comp, 0, 0, b1.width, b1.height);
    const g2 = b2.getContext('2d'); g2.filter = 'blur(5px)'; g2.clearRect(0, 0, b2.width, b2.height); g2.drawImage(b1, 0, 0, b2.width, b2.height);
    post(comp, b1, b2, { time: t, ring: ringR, glitch: fx.glitch || 0, pulse: fx.pulse || 0, cx: W / 2, cy: H / 2 });
    return { seg: g.id, texts: getTexts() };
  }

  let audio = null;
  window.__sb = {
    info: () => ({ duration: tl.total, fps: tl.fps || 30, safe: SAFE, segments: segs.map((g) => ({ id: g.id, type: g.type, start: g.start, duration: g.duration })) }),
    frame: (t) => { const r = frame(t); return { seg: r.seg, texts: r.texts.length }; },
    texts: (t) => frame(t).texts,
    async renderAudio() { const r = await renderMix(tl, series); audio = { wav: toWav(r.buffer), meta: r }; return audio.wav.length; },
    audioChunk(off, len) { const a = audio.wav.subarray(off, off + len); let s = ''; for (let i = 0; i < a.length; i += 32768) s += String.fromCharCode.apply(null, a.subarray(i, i + 32768)); return btoa(s); },
    audioMeta: () => ({ duck: audio.meta.duckSpans, silence: audio.meta.silence }),
  };
  frame(Number(Q.get('t') || 0));
  window.__sbReady = true;

  if (!EXPORT) {
    const btn = document.getElementById('play'); btn.hidden = false;
    btn.onclick = async () => {
      btn.textContent = 'RENDERING SCORE…';
      const r = await renderMix(tl, series);
      const ac = new AudioContext(); const src = ac.createBufferSource(); src.buffer = r.buffer; src.connect(ac.destination);
      const off = Number(Q.get('t') || 0); const t0 = ac.currentTime + 0.1; src.start(t0, off); btn.hidden = true;
      const loop = () => { const t = ac.currentTime - t0 + off; frame(Math.max(0, t)); if (t < tl.total) requestAnimationFrame(loop); };
      loop();
    };
  }
}
boot().catch((e) => { console.error(e); window.__sbError = String(e.stack || e); });
