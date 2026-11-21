// Scene renderers. Each timeline scene names one with visual.type; params come from the timeline so
// later parts can reuse these with new text/numbers. All drawing in design space (1080x1920).
import { gsap } from 'gsap';
import { C, DW, VT, MONO, rgba, clamp, lerp, smooth, rng, hash, vnoise, vnoise2, text, measure, poly, circle, stroke, panel, typed, blink, cursor } from './draw.js';
import { findWord, sentenceStart as sS, sentenceEnd as sE, countdown } from './schedule.js';

const TAU = Math.PI * 2;
const pad2 = (n) => String(n).padStart(2, '0');
const hms = (s) => `${pad2(Math.floor(s / 3600))}:${pad2(Math.floor(s / 60) % 60)}:${pad2(Math.floor(s) % 60)}`;
const parseClock = (str) => str.split(':').reduce((a, x) => a * 60 + Number(x), 0);
const sent = (sc, i) => sS(sc, i), sentEnd = (sc, i) => sE(sc, i);
function tween(build) { const tl = gsap.timeline({ paused: true }); const s = build(tl); return { tl, s, seek: (t) => { tl.seek(Math.max(0, t), true); return s; } }; }

// typed line helper with cursor while typing
function typeLine(ctx, str, x, y, lt, t0, dur, o = {}) {
  if (lt < t0) return 0;
  const [shown, done] = typed(str, lt, t0, t0 + dur);
  const w = text(ctx, shown, o.align === 'center' ? x - measure(ctx, str, o.size || 28, o.font || MONO, o.weight || 400) / 2 : x, y, { ...o, align: 'left' });
  if ((!done || o.keepCursor) && (o.cursor !== false) && (!done || blink(lt))) {
    const bx = (o.align === 'center' ? x - measure(ctx, str, o.size || 28, o.font || MONO, o.weight || 400) / 2 : x) + w;
    cursor(ctx, bx, y, o.size || 28, o.color || C.cyan, o.alpha ?? 1);
  }
  return w;
}

function ring(ctx, x, y, age, o = {}) {
  if (age < 0 || age > (o.life || 3.2)) return;
  const life = o.life || 3.2, speed = o.speed || 620;
  for (let k = 0; k < (o.n || 3); k++) {
    const a = age - k * 0.16; if (a < 0) continue;
    stroke(ctx, o.color || C.cyan, (1 - age / life) * (k ? 0.45 : 1) * (o.alpha ?? 1), (o.width || 4) - k);
    ctx.beginPath(); ctx.arc(x, y, a * speed, 0, TAU); ctx.stroke();
  }
}

// ---------------------------------------------------------------- shared signal model (spectrogram & waveforms)
// counting voice: one number word every 1.25 s, two syllables each
export function voiceEnv(tt, vs) {
  if (tt < vs) return 0;
  const u = (tt - vs) % 1.25;
  if (u > 0.78) return 0;
  const syl = Math.sin(Math.PI * ((u % 0.39) / 0.39));
  return Math.pow(Math.max(0, syl), 0.7) * (0.75 + 0.25 * Math.sin(tt * 2.1));
}
// whisper underneath: 4 short words, repeating every 2.6 s
export function voice2Env(tt, vs) {
  if (tt < vs) return 0;
  const u = (tt - vs + 0.3) % 2.6;
  if (u > 2.0) return 0;
  const w = u % 0.5;
  return w < 0.38 ? Math.pow(Math.sin(Math.PI * w / 0.38), 1.5) : 0;
}

function genSpectrogram({ t0, t1, pps, h, vs, seed = 1, layer = 'main' }) {
  const w = Math.ceil((t1 - t0) * pps);
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const g = cv.getContext('2d');
  const img = g.createImageData(w, h); const d = img.data;
  for (let x = 0; x < w; x++) {
    const tt = t0 + x / pps;
    const ve = layer === 'main' ? voiceEnv(tt, vs) : voice2Env(tt, vs);
    const f0 = 0.05 + 0.006 * Math.sin(tt * 3.1 + Math.floor((tt - vs) / 1.25));
    const spike = layer === 'main' && tt >= vs && tt < vs + 0.14 ? 1 : 0;
    for (let y = 0; y < h; y++) {
      const f = 1 - y / h;
      let b = 0, v = 0;
      if (layer === 'main') {
        const nz = vnoise2(x * 0.32, y * 0.55, seed);
        b = 0.05 + 0.2 * nz * nz * (1 - f * 0.6) + 0.06 * hash(x * 0.71 + y * 1.37 + seed);
        b += 0.38 * Math.exp(-(((f - 0.035) / 0.006) ** 2)) + 0.2 * Math.exp(-(((f - 0.072) / 0.005) ** 2));
        if (ve > 0) {
          let s = 0;
          for (let k = 1; k <= 13; k++) {
            const fk = k * f0; const dd = (f - fk) / 0.0065;
            if (dd * dd < 9) s += Math.exp(-dd * dd) * (Math.exp(-(((fk - 0.22) / 0.14) ** 2)) + 0.6 * Math.exp(-(((fk - 0.48) / 0.1) ** 2)));
          }
          v = ve * s * 1.1 + ve * 0.05 * hash(x + y * 3.1);
        }
        if (spike) v += 1.1 * Math.exp(-f * 1.4);
      } else {
        // breathy band, no harmonics, low in the spectrum
        if (ve > 0) v = ve * 0.55 * Math.exp(-(((f - 0.2) / 0.09) ** 2)) * (0.5 + vnoise2(x * 0.8, y * 0.9, seed + 3));
      }
      const a = clamp(b + v), i = (y * w + x) * 4;
      const m = a > 0 ? clamp(v / (b + v + 1e-6)) : 0;
      d[i] = lerp(25, 255, m); d[i + 1] = lerp(240, 46, m); d[i + 2] = lerp(255, 136, m); d[i + 3] = Math.round(255 * Math.min(1, a * 1.25));
    }
  }
  g.putImageData(img, 0, 0);
  return cv;
}

function spectroAxes(ctx, x, y, w, h, c0, c1, o = {}) {
  stroke(ctx, C.cyan, 0.12, 1);
  for (let k = 1; k < 4; k++) { ctx.beginPath(); ctx.moveTo(x, y + (h * k) / 4); ctx.lineTo(x + w, y + (h * k) / 4); ctx.stroke(); }
  ['4K', '2K', '1K'].forEach((l, k) => text(ctx, l, x + 10, y + (h * k) / 4 + 18, { size: 16, alpha: 0.55 }));
  if (o.ticks === false) return;
  const step = o.step || 2;
  for (let s = Math.ceil(c0 / step) * step; s <= c1; s += step) {
    const px = x + ((s - c0) / (c1 - c0)) * w;
    stroke(ctx, C.cyan, 0.4, 1.5); ctx.beginPath(); ctx.moveTo(px, y + h); ctx.lineTo(px, y + h + 10); ctx.stroke();
    if (px > x + 60 && px < x + w - 60) text(ctx, hms(s), px, y + h + 28, { size: 17, alpha: 0.6, align: 'center' });
  }
}

function waveform(ctx, x, y, w, amp, f, color, alpha, lw = 2.2) {
  stroke(ctx, color, alpha, lw);
  ctx.beginPath();
  for (let i = 0; i <= w; i += 2) { const v = clamp(f(i / w), -1, 1); i ? ctx.lineTo(x + i, y - v * amp) : ctx.moveTo(x + i, y - v * amp); }
  ctx.stroke();
}

// ================================================================= scene types
export const SCENES = {};

// ----------------------------------------------------------------- 0. cold open
SCENES.coldOpen = {
  frame: (lt) => ({ ambient: smooth(1.8, 4.5, lt), hud: smooth(3.0, 5.0, lt), rings: lt > 4 }),
  draw(ctx, lt, sc) {
    const age = lt - 0.35;
    if (age > -0.05) {
      ctx.fillStyle = rgba(C.cyan, Math.exp(-Math.max(0, age) * 3) * 0.9);
      ctx.beginPath(); ctx.arc(540, 760, 10, 0, TAU); ctx.fill();
    }
    ring(ctx, 540, 760, age, { life: 3.4, speed: 640, n: 3, width: 5 });
    const v = sc.visual;
    typeLine(ctx, v.heading, 540, 700, lt, 1.1, 0.8, { font: VT, size: 150, align: 'center', keepCursor: true, cursor: lt < sent(sc, 1) });
    stroke(ctx, C.cyan, 0.5, 2); poly(ctx, [[250, 780], [830, 780]], smooth(1.9, 2.6, lt));
    v.readouts.forEach((r, i) => {
      const t0 = sent(sc, Math.min(i + 1, sc.voice.sentences.length - 1));
      typeLine(ctx, `> ${r}`, 540, 850 + i * 62, lt, t0, 0.45, { size: 36, align: 'center', alpha: 0.9, weight: 500, cursor: false });
    });
  },
};

// ----------------------------------------------------------------- title card (template)
SCENES.titleCard = {
  frame: () => ({ ambient: 1, hud: 0 }),
  draw(ctx, lt, sc, st, env) {
    ring(ctx, 540, 880, lt - 0.15, { life: 3.0, speed: 700, n: 3, width: 4 });
    text(ctx, 'HADAL-9 ARCHIVE · AUDIO EVIDENCE', 540, 690, { size: 22, align: 'center', alpha: 0.7 * smooth(0.2, 0.6, lt), spacing: 4 });
    const [a, b] = env.series.title.split(/ (?=\S+$)/); // "THE SIGNAL" / "BENEATH"
    typeLine(ctx, a, 540, 810, lt, 0.35, 0.7, { font: VT, size: 150, align: 'center', cursor: lt < 1.0 });
    typeLine(ctx, b, 540, 950, lt, 1.0, 0.45, { font: VT, size: 150, align: 'center', keepCursor: true });
    stroke(ctx, C.cyan, 0.6, 2); poly(ctx, [[220, 1035], [860, 1035]], smooth(1.3, 1.9, lt));
    text(ctx, env.tl.episode.subtitle, 540, 1095, { size: 46, align: 'center', weight: 500, spacing: 18, alpha: smooth(1.6, 2.1, lt) });
  },
};

// ----------------------------------------------------------------- end card (template)
SCENES.endCard = {
  frame: () => ({ ambient: 1, hud: 0 }),
  draw(ctx, lt, sc, st, env) {
    if (lt < 0.35) return;
    ring(ctx, 540, 900, lt - 0.45, { life: 3.0, speed: 650, n: 2, width: 3 });
    text(ctx, env.series.title, 540, 720, { size: 30, align: 'center', spacing: 10, weight: 500, alpha: smooth(0.4, 0.9, lt) });
    text(ctx, `${env.tl.episode.subtitle} · END OF TRANSMISSION`, 540, 772, { size: 20, align: 'center', alpha: 0.6 * smooth(0.6, 1.1, lt), spacing: 3 });
    const full = env.tl.endCard.text; const ix = full.indexOf(':');
    const head = ix > 0 ? full.slice(0, ix + 1) : full, rest = ix > 0 ? full.slice(ix + 1).trim() : '';
    typeLine(ctx, head, 540, 905, lt, 0.6, 0.55, { font: VT, size: 170, align: 'center', cursor: lt < 1.3 });
    // wrap the rest into lines of <= 15 chars
    const lines = []; let cur = '';
    for (const w of rest.split(' ')) { if ((cur + ' ' + w).trim().length > 15) { lines.push(cur.trim()); cur = w; } else cur += ' ' + w; }
    if (cur.trim()) lines.push(cur.trim());
    let t0 = 1.3;
    lines.forEach((l, i) => { const d = l.length * 0.05; typeLine(ctx, l, 540, 1045 + i * 92, lt, t0, d, { font: VT, size: 88, align: 'center', keepCursor: i === lines.length - 1, cursor: i === lines.length - 1 || lt < t0 + d }); t0 += d + 0.1; });
  },
};

// ----------------------------------------------------------------- 1. the station (cross-section)
SCENES.station = {
  init(sc) {
    const R = rng(7);
    const jag = (pts, amt) => pts.map(([x, y], i) => (i && i < pts.length - 1 ? [x + (R() - 0.5) * amt, y + (R() - 0.5) * amt] : [x, y]));
    const lerpPts = (a, b, n) => Array.from({ length: n + 1 }, (_, i) => [lerp(a[0], b[0], i / n), lerp(a[1], b[1], i / n)]);
    const L = jag([...lerpPts([60, 880], [300, 960], 6), ...lerpPts([300, 960], [450, 1100], 5).slice(1)], 26);
    const Rw = jag([...lerpPts([1020, 860], [790, 950], 6), ...lerpPts([790, 950], [630, 1100], 5).slice(1)], 26);
    const pods = [];
    for (let i = 0; i < 6; i++) { const left = i < 3; pods.push({ x: left ? 215 : 865, y: 445 + (i % 3) * 125, i }); }
    const tw = tween((tl) => { const s = { draw: 0, cap: 0 }; tl.to(s, { draw: 1, duration: 2.6, ease: 'power2.inOut' }, 0); return s; });
    return { L, Rw, pods, tw };
  },
  draw(ctx, lt, sc, st) {
    const s = st.tw.seek(lt), p = s.draw;
    const s0 = sent(sc, 0), s1 = sent(sc, 1), s2 = sent(sc, 2), s3 = sent(sc, 3);
    // trench walls + depth hatching
    stroke(ctx, C.cyan, 0.85, 3); poly(ctx, st.L, p); poly(ctx, st.Rw, p);
    for (let k = 1; k <= 3; k++) {
      stroke(ctx, C.cyan, 0.32 / k, 1.5);
      poly(ctx, st.L.map(([x, y]) => [x, y + k * 22]), p); poly(ctx, st.Rw.map(([x, y]) => [x, y + k * 22]), p);
    }
    stroke(ctx, C.cyan, 0.5, 2); ctx.setLineDash([6, 10]); poly(ctx, [[450, 1100], [630, 1100]], p); ctx.setLineDash([]);
    text(ctx, 'HADAL TRENCH', 540, 1070, { size: 20, align: 'center', alpha: 0.7 * p, spacing: 4 });
    ['10,600 M', '10,800 M', '11,000 M'].forEach((l, i) => text(ctx, l, 1000, 900 + i * 80, { size: 16, align: 'right', alpha: 0.45 * p }));
    // tether
    stroke(ctx, C.cyan, 0.8, 2.5); poly(ctx, [[540, 290], [540, 515]], p);
    for (let y = 300; y < 510; y += 26) { stroke(ctx, C.cyan, 0.35 * p, 1.5); ctx.beginPath(); ctx.moveTo(533, y); ctx.lineTo(547, y); ctx.stroke(); }
    // hub
    stroke(ctx, C.cyan, 0.95, 3); ctx.beginPath(); ctx.roundRect(380, 515, 320, 100, 40);
    ctx.save(); ctx.setLineDash([1100 * p, 1100]); ctx.stroke(); ctx.restore();
    stroke(ctx, C.cyan, 0.35 * p, 1.5);
    for (let x = 420; x <= 660; x += 40) { ctx.beginPath(); ctx.moveTo(x, 522); ctx.lineTo(x, 608); ctx.stroke(); }
    for (let k = 0; k < 5; k++) circle(ctx, 450 + k * 45, 565, 9, p);
    text(ctx, `${sc.visual.name} · CREW 1/${sc.visual.pods}`, 522, 470, { size: 21, weight: 500, align: 'right', alpha: smooth(1.4, 2.2, lt) });
    // pods
    for (const pd of st.pods) {
      const left = pd.x < 540, hx = left ? 380 : 700, ey = clamp(pd.y, 535, 595);
      stroke(ctx, C.cyan, 0.7, 2.5); poly(ctx, [[pd.x + (left ? 52 : -52), pd.y], [left ? 330 : 750, pd.y], [hx, ey]], p);
      let on = sc.visual.lit.includes(pd.i) ? 1 : 0;
      if (!on) { // census flash on "built for six", then the others go dark one by one
        const tOn = s0 + 0.2 + pd.i * 0.22, tOff = s1 + 0.25 + pd.i * 0.28;
        on = smooth(tOn, tOn + 0.15, lt) * (1 - smooth(tOff, tOff + 0.25, lt)) * 0.85;
      }
      const flick = sc.visual.lit.includes(pd.i) ? 0.85 + 0.15 * vnoise(lt * 6, pd.i) : 1;
      if (on > 0.01) {
        const g = ctx.createRadialGradient(pd.x, pd.y, 4, pd.x, pd.y, 56);
        g.addColorStop(0, rgba(C.cyan, 0.9 * on * flick)); g.addColorStop(0.55, rgba(C.cyan, 0.35 * on * flick)); g.addColorStop(1, rgba(C.cyan, 0));
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(pd.x, pd.y, 56, 0, TAU); ctx.fill();
      }
      stroke(ctx, C.cyan, 0.4 + 0.6 * Math.max(on, 0), 3); circle(ctx, pd.x, pd.y, 52, p);
      stroke(ctx, C.cyan, 0.3 + 0.5 * on, 1.5); circle(ctx, pd.x, pd.y, 30, p);
      text(ctx, `P${pd.i + 1}`, pd.x, pd.y + 78, { size: 20, align: 'center', alpha: 0.75 * p, weight: 500 });
      if (!sc.visual.lit.includes(pd.i) && lt > s1 + 0.6 + pd.i * 0.28) text(ctx, 'VACANT', pd.x, pd.y + 102, { size: 15, align: 'center', alpha: 0.45 });
    }
    // ascent capsule rising on day 30
    const u = clamp((lt - s1 - 0.2) / 3.0);
    if (u > 0 && u < 1) {
      const y = lerp(500, 280, gsap.parseEase('power1.in')(u)), a = 1 - smooth(0.75, 1, u);
      stroke(ctx, C.cyan, a, 2.5); ctx.beginPath(); ctx.roundRect(522, y - 28, 36, 56, 14); ctx.stroke();
      ctx.fillStyle = rgba(C.cyan, 0.35 * a); ctx.fill();
    }
    typeLine(ctx, 'DAY 30 · 5 CREW TOPSIDE', 560, 380, lt, s1 + 0.3, 0.6, { size: 22, weight: 500, cursor: false, alpha: 0.9 });
    // pressure on "the pressure was getting to me"
    if (lt > s2) {
      const fl = 0.6 + 0.4 * (hash(Math.floor(lt * 14)) > 0.25 ? 1 : 0.2);
      text(ctx, 'PRESSURE 1,086 BAR ▲', 540, 665, { size: 24, align: 'center', weight: 500, alpha: fl * smooth(s2, s2 + 0.3, lt) * (1 - smooth(s3 - 0.4, s3 - 0.1, lt)) });
      stroke(ctx, C.cyan, 0.7, 1.5);
      for (const yy of [515, 615]) { ctx.beginPath(); for (let x = 400; x <= 680; x += 10) { const j = (hash(x + Math.floor(lt * 20)) - 0.5) * 8 * smooth(s2, s2 + 0.5, lt); x === 400 ? ctx.moveTo(x, yy + j) : ctx.lineTo(x, yy + j); } ctx.stroke(); }
    }
    // hydrophones on "nobody hears anything down here"
    if (lt > s3 - 0.2) {
      const a = smooth(s3 - 0.2, s3 + 0.3, lt);
      [[440, 760], [540, 790], [640, 760]].forEach(([x, y], k) => {
        stroke(ctx, C.cyan, 0.5 * a, 1.5); ctx.beginPath(); ctx.moveTo(x, 615); ctx.lineTo(x, y - 14); ctx.stroke();
        stroke(ctx, C.cyan, a, 2.5); ctx.beginPath(); ctx.moveTo(x - 12, y - 14); ctx.lineTo(x + 12, y - 14); ctx.lineTo(x, y + 8); ctx.closePath(); ctx.stroke();
        for (let r = 0; r < 3; r++) {
          const ag = ((lt - s3 + k * 0.3 + r * 0.6) % 1.8) / 1.8;
          stroke(ctx, C.cyan, a * (1 - ag) * 0.6, 1.5); ctx.beginPath(); ctx.arc(x, y + 8, 10 + ag * 70, 0.25 * Math.PI, 0.75 * Math.PI); ctx.stroke();
        }
      });
      text(ctx, 'HYDROPHONES 3/3 ACTIVE', 540, 850, { size: 22, align: 'center', weight: 500, alpha: a });
    }
  },
};

// ----------------------------------------------------------------- 2. the sound (waveform + spectrogram)
SCENES.spectrum = {
  init(sc) {
    const w = findWord(sc, sc.visual.spikeWord);
    const tSpike = (w ? w.t0 : 2) + 0.12;
    const base = parseClock(sc.visual.clockAt);
    const pps = 94, c0 = base - tSpike - 11, c1 = base + sc.duration - tSpike + 2;
    return { tSpike, base, pps, c0, spec: genSpectrogram({ t0: c0, t1: c1, pps, h: 380, vs: base, seed: 3 }) };
  },
  draw(ctx, lt, sc, st) {
    const c = st.base + (lt - st.tSpike), win = 10, a0 = c - win;
    const X = 70, W = 940;
    // waveform
    panel(ctx, X, 330, W, 280, 'CH-01  HYDROPHONE ARRAY', { right: `${hms(c)}.${Math.floor((c % 1) * 10)}` });
    stroke(ctx, C.cyan, 0.12, 1); ctx.beginPath(); ctx.moveTo(X, 470); ctx.lineTo(X + W, 470); ctx.stroke();
    waveform(ctx, X, 470, W, 105, (u) => { const tt = a0 + u * win; const sp = tt >= st.base && tt < st.base + 0.15 ? 1 : 0; return (0.12 + 0.06 * vnoise(tt * 3)) * (vnoise(tt * 95) - 0.5) * 2 + sp * (vnoise(tt * 300) - 0.5) * 2; }, C.cyan, 0.9);
    waveform(ctx, X, 470, W, 105, (u) => { const tt = a0 + u * win; return voiceEnv(tt, st.base) * 0.75 * (vnoise(tt * 140, 5) - 0.5) * 2; }, C.mag, 0.95, 2.4);
    // spectrogram
    panel(ctx, X, 650, W, 380, 'SPECTROGRAM  0-4 KHZ');
    const sx = (a0 - st.c0) * st.pps;
    ctx.drawImage(st.spec, sx, 0, win * st.pps, 380, X, 650, W, 380);
    spectroAxes(ctx, X, 650, W, 380, a0, c);
    // spike marker
    const xs = X + ((st.base - a0) / win) * W;
    if (xs >= X && xs <= X + W) {
      stroke(ctx, C.mag, 0.9, 2); ctx.setLineDash([10, 8]); ctx.beginPath(); ctx.moveTo(xs, 340); ctx.lineTo(xs, 1030); ctx.stroke(); ctx.setLineDash([]);
      const lx = clamp(xs, X + 120, X + W - 120);
      text(ctx, `▼ ${hms(st.base)}`, lx, 632, { size: 22, align: 'center', color: C.mag, weight: 500 });
    }
    // classification chips
    sc.visual.tags.forEach(([label, si], i) => {
      const t0 = sent(sc, si); if (lt < t0) return;
      const danger = i === sc.visual.tags.length - 1, col = danger ? C.mag : C.cyan;
      const x = X + i * 320, a = smooth(t0, t0 + 0.2, lt);
      stroke(ctx, col, 0.8 * a, 2); ctx.strokeRect(x, 1092, 300, 46);
      typeLine(ctx, label, x + 150, 1115, lt, t0, 0.4, { size: 21, align: 'center', color: col, weight: 500, cursor: false });
    });
  },
};

// ----------------------------------------------------------------- 3. the count
SCENES.countdown = {
  init(sc) { const R = rng(33); return { ev: countdown(sc), blips: Array.from({ length: 7 }, () => ({ a: R() * TAU, r: 80 + R() * 290 })) }; },
  draw(ctx, lt, sc, st) {
    const cx = 540, cy = 705, Rr = 390;
    // PPI sonar grid
    for (let k = 1; k <= 4; k++) { stroke(ctx, C.cyan, k === 4 ? 0.55 : 0.25, k === 4 ? 2.5 : 1.5); circle(ctx, cx, cy, (Rr * k) / 4); }
    for (let k = 1; k <= 4; k++) text(ctx, `${k} KM`, cx + (Rr * k) / 4 * 0.707 + 6, cy - (Rr * k) / 4 * 0.707 - 6, { size: 15, alpha: 0.5 });
    for (let k = 0; k < 12; k++) { const a = (k / 12) * TAU; stroke(ctx, C.cyan, 0.14, 1); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(a) * Rr, cy + Math.sin(a) * Rr); ctx.stroke(); }
    for (let k = 0; k < 72; k++) { const a = (k / 72) * TAU, l = k % 6 ? 8 : 16; stroke(ctx, C.cyan, 0.5, 1.5); ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * Rr, cy + Math.sin(a) * Rr); ctx.lineTo(cx + Math.cos(a) * (Rr + l), cy + Math.sin(a) * (Rr + l)); ctx.stroke(); }
    const sw = lt * 1.25 - Math.PI / 2;
    for (let k = 0; k < 28; k++) {
      ctx.fillStyle = rgba(C.cyan, 0.2 * (1 - k / 28));
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, Rr, sw - (k + 1) * 0.03, sw - k * 0.03); ctx.closePath(); ctx.fill();
    }
    stroke(ctx, C.cyan, 0.95, 2.5); ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(sw) * Rr, cy + Math.sin(sw) * Rr); ctx.stroke();
    for (const b of st.blips) { const d = ((sw - b.a) % TAU + TAU) % TAU, br = Math.exp(-d * 1.4); ctx.fillStyle = rgba(C.cyan, 0.15 + 0.8 * br); ctx.beginPath(); ctx.arc(cx + Math.cos(b.a) * b.r, cy + Math.sin(b.a) * b.r, 5, 0, TAU); ctx.fill(); }
    // number
    let cur = null; for (const e of st.ev) if (e.t <= lt) cur = e;
    text(ctx, 'COUNT', cx, 450, { size: 26, align: 'center', alpha: 0.75, spacing: 10, weight: 500 });
    text(ctx, 'NIGHTLY · 02:14', cx, 965, { size: 22, align: 'center', alpha: 0.6, spacing: 4 });
    if (!cur) { text(ctx, '--', cx, cy, { font: VT, size: 360, align: 'center', alpha: 0.25 }); return {}; }
    const dt = lt - cur.t, pop = 1 + 0.12 * Math.exp(-dt * 14), str = String(cur.n);
    ctx.save(); ctx.translate(cx, cy); ctx.scale(pop, pop);
    if (dt < 0.12) { text(ctx, str, -9, 0, { font: VT, size: 400, align: 'center', color: C.cyan, alpha: 0.45 }); text(ctx, str, 9, 0, { font: VT, size: 400, align: 'center', color: C.mag, alpha: 0.45 }); }
    text(ctx, str, 0, 0, { font: VT, size: 400, align: 'center', color: C.mag });
    ctx.restore();
    const last = st.ev[st.ev.length - 1];
    if (cur === last) ring(ctx, cx, cy, dt, { color: C.mag, life: 2.2, speed: 420, n: 2, width: 3, alpha: 0.8 });
    return { glitch: dt < 0.06 ? 0.25 : 0 };
  },
};

// ----------------------------------------------------------------- 4. triangulation (bathymetric contour map)
const MAP = { x: 70, y: 330, w: 940, h: 740 };
function depthAt(u, v, seed) {
  const cx = 0.30 + 0.35 * v + 0.06 * Math.sin(v * 5);
  const d = u - cx;
  return 10150 + 1150 * Math.exp(-((d / 0.16) ** 2)) + 300 * (vnoise2(u * 6, v * 6, seed) - 0.5) + 140 * v;
}
function contourCanvas(S, seed) {
  const cv = document.createElement('canvas'); cv.width = Math.round(MAP.w * S); cv.height = Math.round(MAP.h * S);
  const g = cv.getContext('2d'); g.scale(S, S); g.lineCap = 'round';
  const nx = 118, ny = 93, dx = MAP.w / nx, dy = MAP.h / ny;
  const F = []; for (let j = 0; j <= ny; j++) { F.push([]); for (let i = 0; i <= nx; i++) F[j].push(depthAt(i / nx, j / ny, seed)); }
  for (let L = 10000, k = 0; L <= 11400; L += 50, k++) {
    const major = k % 4 === 0;
    g.strokeStyle = rgba(C.cyan, major ? 0.62 : 0.26); g.lineWidth = major ? 2 : 1.2; g.beginPath();
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const a = F[j][i], b = F[j][i + 1], c = F[j + 1][i + 1], d = F[j + 1][i];
      const pts = [];
      const e = (p, q, x0, y0, x1, y1) => { if ((p < L) !== (q < L)) { const t = (L - p) / (q - p); pts.push([lerp(x0, x1, t), lerp(y0, y1, t)]); } };
      const X0 = i * dx, Y0 = j * dy;
      e(a, b, X0, Y0, X0 + dx, Y0); e(b, c, X0 + dx, Y0, X0 + dx, Y0 + dy); e(d, c, X0, Y0 + dy, X0 + dx, Y0 + dy); e(a, d, X0, Y0, X0, Y0 + dy);
      for (let q = 0; q + 1 < pts.length; q += 2) { g.moveTo(pts[q][0], pts[q][1]); g.lineTo(pts[q + 1][0], pts[q + 1][1]); }
    }
    g.stroke();
  }
  return cv;
}
SCENES.triangulation = {
  init(sc, env) {
    const P = (u, v) => [MAP.x + u * MAP.w, MAP.y + v * MAP.h];
    const S = P(...sc.visual.source), ST = P(0.47, 0.30);
    const H = [P(0.18, 0.16), P(0.84, 0.22), P(0.20, 0.86)];
    const bearings = H.map((h, i) => {
      const a = Math.atan2(S[1] - h[1], S[0] - h[0]);
      const brg = ((Math.atan2(S[0] - h[0], -(S[1] - h[1])) * 180) / Math.PI + 360) % 360;
      return { h, a, brg: Math.round(brg), off: i % 2 ? 0.9 : -0.85 };
    });
    const t1 = sent(sc, 1);
    const tw = tween((tl) => {
      const s = { reveal: 0, b: [0, 0, 0] };
      tl.to(s, { reveal: 1, duration: 2.3, ease: 'power2.out' }, 0.1);
      bearings.forEach((_, i) => tl.to(s.b, { [i]: 1, duration: 1.1, ease: 'power3.out' }, t1 + i * 0.5));
      return s;
    });
    return { S, ST, bearings, tw, map: contourCanvas(env.S, sc.visual.seed || 1) };
  },
  draw(ctx, lt, sc, st) {
    const s = st.tw.seek(lt);
    panel(ctx, MAP.x, MAP.y, MAP.w, MAP.h, 'BATHYMETRY  ·  CONTOUR 50 M', { right: 'GRID 4 KM' });
    // sonar reveal of the contour map from the station
    const rr = s.reveal * 1300;
    ctx.save(); ctx.beginPath(); ctx.rect(MAP.x, MAP.y, MAP.w, MAP.h); ctx.clip();
    ctx.save(); ctx.beginPath(); ctx.arc(st.ST[0], st.ST[1], rr, 0, TAU); ctx.clip();
    ctx.drawImage(st.map, MAP.x, MAP.y, MAP.w, MAP.h); ctx.restore();
    if (s.reveal < 1) { stroke(ctx, C.cyan, 0.9, 3); circle(ctx, st.ST[0], st.ST[1], rr); }
    // bearing lines
    st.bearings.forEach((b, i) => {
      const k = s.b[i]; if (k <= 0) return;
      const a = b.a + b.off * (1 - k);
      stroke(ctx, C.cyan, 0.95, 3); ctx.beginPath(); ctx.moveTo(b.h[0], b.h[1]); ctx.lineTo(b.h[0] + Math.cos(a) * 1500, b.h[1] + Math.sin(a) * 1500); ctx.stroke();
      stroke(ctx, C.cyan, 0.25, 10); ctx.beginPath(); ctx.moveTo(b.h[0], b.h[1]); ctx.lineTo(b.h[0] + Math.cos(a) * 1500, b.h[1] + Math.sin(a) * 1500); ctx.stroke();
    });
    ctx.restore();
    st.bearings.forEach((b, i) => {
      stroke(ctx, C.cyan, 1, 2.5); ctx.beginPath(); ctx.moveTo(b.h[0], b.h[1] - 14); ctx.lineTo(b.h[0] + 12, b.h[1] + 8); ctx.lineTo(b.h[0] - 12, b.h[1] + 8); ctx.closePath(); ctx.stroke();
      circle(ctx, b.h[0], b.h[1], 22 + 4 * Math.sin(lt * 3 + i), 1);
      const lbl = s.b[i] > 0.05 ? `H${i + 1} · BRG ${String(b.brg).padStart(3, '0')}°` : `H${i + 1}`;
      text(ctx, lbl, b.h[0] + (b.h[0] > 540 ? -32 : 32), b.h[1] - 34, { size: 21, weight: 500, align: b.h[0] > 540 ? 'right' : 'left' });
    });
    // station marker
    stroke(ctx, C.cyan, 1, 2.5); ctx.strokeRect(st.ST[0] - 11, st.ST[1] - 11, 22, 22);
    text(ctx, 'HADAL-9', st.ST[0] + 22, st.ST[1] + 2, { size: 20, weight: 500 });
    if (lt > sent(sc, 3)) text(ctx, 'NOT ABOVE', st.ST[0] + 22, st.ST[1] + 28, { size: 18, color: C.cyan, alpha: 0.75 });
    // intersection (danger, magenta)
    const t2 = sent(sc, 2);
    if (lt > t2) {
      const a = smooth(t2, t2 + 0.25, lt), [x, y] = st.S;
      stroke(ctx, C.mag, a, 3); circle(ctx, x, y, 26 + 5 * Math.sin(lt * 6));
      ctx.beginPath(); ctx.moveTo(x - 44, y); ctx.lineTo(x - 14, y); ctx.moveTo(x + 14, y); ctx.lineTo(x + 44, y); ctx.moveTo(x, y - 44); ctx.lineTo(x, y - 14); ctx.moveTo(x, y + 14); ctx.lineTo(x, y + 44); ctx.stroke();
      ring(ctx, x, y, (lt - t2) % 2.2, { color: C.mag, life: 2.2, speed: 140, n: 1, width: 2, alpha: 0.8 });
      text(ctx, 'CROSS · 1 POINT', x, y - 64, { size: 22, align: 'center', color: C.mag, weight: 500, alpha: a });
    }
    // profile inset: below the trench floor
    const t4 = sent(sc, 4);
    if (lt > t4 - 0.1) {
      const a = smooth(t4 - 0.1, t4 + 0.3, lt), X = 600, Y = 905, W = 390, Hh = 150;
      ctx.fillStyle = rgba(C.bg, 0.85 * a); ctx.fillRect(X, Y, W, Hh);
      panel(ctx, X, Y, W, Hh, 'PROFILE A-A\'', { alpha: a });
      stroke(ctx, C.cyan, 0.9 * a, 2.5); ctx.beginPath();
      for (let i = 0; i <= 38; i++) { const xx = X + 10 + i * 10, yy = Y + 92 - 24 * Math.exp(-(((i - 19) / 9) ** 2)) * -1 + (hash(i * 3.3) - 0.5) * 6; i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); }
      ctx.stroke();
      stroke(ctx, C.mag, a, 2); ctx.setLineDash([5, 6]); ctx.beginPath(); ctx.moveTo(X + 200, Y + 40); ctx.lineTo(X + 200, Y + 128); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = rgba(C.mag, a); ctx.beginPath(); ctx.arc(X + 200, Y + 132, 7, 0, TAU); ctx.fill();
      text(ctx, '-340 M', X + 216, Y + 128, { size: 20, color: C.mag, weight: 500, alpha: a });
      typeLine(ctx, sc.visual.sourceLabel, st.S[0], st.S[1] + 70, lt, t4, 0.6, { size: 22, align: 'center', color: C.mag, weight: 500, cursor: false });
    }
  },
};

// ----------------------------------------------------------------- 5. the second voice (slowdown)
SCENES.slowdown = {
  init(sc) {
    const sp = sc.visual.speeds;
    const s0 = sent(sc, 0), e0 = sentEnd(sc, 0), s1 = sent(sc, 1), e1 = sentEnd(sc, 1);
    const keys = [[0, sp[0]], [s0 + 0.3, sp[0]], [e0 + 0.2, sp[1]], [s1, sp[1]], [e1 + 0.4, sp[2]], [sc.duration + 2, sp[2]]];
    const speed = (t) => { for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) { const [a, va] = keys[i - 1], [b, vb] = keys[i]; return lerp(va, vb, (t - a) / (b - a)); } return sp[2]; };
    const pos = (t) => { let acc = 0; for (let i = 1; i < keys.length; i++) { const [a, va] = keys[i - 1], [b] = keys[i]; const e = Math.min(t, b); if (e <= a) break; acc += (va + speed(e)) / 2 * (e - a); } return acc; };
    const base = 8040, start = base + 6, pps = 94;
    const c0 = start - 12, c1 = start + pos(sc.duration + 1) + 2;
    return {
      speed, pos, start, pps, c0, base,
      spec: genSpectrogram({ t0: c0, t1: c1, pps, h: 380, vs: base, seed: 5 }),
      spec2: genSpectrogram({ t0: c0, t1: c1, pps, h: 380, vs: base, seed: 9, layer: 'whisper' }),
    };
  },
  draw(ctx, lt, sc, st) {
    const v = st.speed(lt), c = st.start + st.pos(lt), win = Math.max(0.8, 10 * v), a0 = c - win;
    const X = 70, W = 940, t2 = sent(sc, 2), k2 = smooth(t2 - 0.2, t2 + 1.2, lt);
    text(ctx, 'SLOWED', X, 296, { font: VT, size: 54, alpha: 0.85 });
    text(ctx, `PLAYBACK ×${v.toFixed(2)}`, X + W, 296, { font: VT, size: 54, align: 'right', color: C.cyan });
    panel(ctx, X, 340, W, 220, 'LAYER 1  ·  COUNT', { right: `${hms(c)}.${String(Math.floor((c % 1) * 100)).padStart(2, '0')}` });
    waveform(ctx, X, 450, W, 85, (u) => { const tt = a0 + u * win; const e = 0.14 + 0.7 * voiceEnv(tt, st.base); return e * (0.55 * Math.sin(TAU * 6.1 * tt) + 0.4 * Math.sin(TAU * 17.3 * tt + 1) * vnoise(tt * 2) + 0.4 * (vnoise(tt * 55) - 0.5)); }, C.cyan, 0.9);
    panel(ctx, X, 590, W, 170, 'LAYER 2  ·  UNDER THE NUMBERS', { alpha: 0.35 + 0.65 * k2, right: k2 > 0.5 ? 'WHISPER' : '', rightColor: C.mag });
    stroke(ctx, C.cyan, 0.1, 1); ctx.beginPath(); ctx.moveTo(X, 675); ctx.lineTo(X + W, 675); ctx.stroke();
    if (k2 > 0) waveform(ctx, X, 675, W, 60, (u) => { const tt = a0 + u * win; return voice2Env(tt, st.base) * (0.55 * Math.sin(TAU * 3.2 * tt + 2) + 0.45 * (vnoise(tt * 30, 7) - 0.5)); }, C.mag, 0.7 * k2, 2);
    panel(ctx, X, 790, W, 290, 'SPECTROGRAM  ·  TIME-STRETCHED');
    const sx = (a0 - st.c0) * st.pps, sw = win * st.pps;
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(st.spec, sx, 0, sw, 380, X, 790, W, 290);
    if (k2 > 0) { ctx.globalAlpha = k2; ctx.drawImage(st.spec2, sx, 0, sw, 380, X, 790, W, 290); ctx.globalAlpha = 1; }
    spectroAxes(ctx, X, 790, W, 290, a0, c, { step: win > 4 ? 2 : win > 1.6 ? 0.5 : 0.25, ticks: win > 1.6 });
    if (lt > sent(sc, 3)) typeLine(ctx, '4 WORDS · LOOPING', X + W - 210, 640, lt, sent(sc, 3), 0.5, { size: 18, color: C.mag, weight: 500, cursor: false });
  },
};

// ----------------------------------------------------------------- 6. the words (glitch assembly)
const GLYPHS = '#%&@$?!<>/\\|01ΔΣΞ=+*0123456789ABCDEFX';
SCENES.glitchWords = {
  init(sc) {
    const R = rng(66);
    const rain = Array.from({ length: 16 }, (_, i) => ({ x: 92 + i * 58, v: 30 + R() * 50, off: R() * 900, s: Array.from({ length: 24 }, () => '0123456789ABCDEF'[Math.floor(R() * 16)]).join('') }));
    return { rain };
  },
  draw(ctx, lt, sc, st) {
    // dim hex rain, clipped inside the safe panel
    ctx.save(); ctx.beginPath(); ctx.rect(70, 330, 940, 760); ctx.clip();
    ctx.font = `400 26px ${MONO}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.letterSpacing = '0px';
    for (const r of st.rain) for (let k = 0; k < r.s.length; k++) {
      const y = 330 + ((k * 34 + r.off + lt * r.v) % 800);
      ctx.fillStyle = rgba(C.cyan, 0.06 + 0.06 * hash(k + r.x)); ctx.fillText(r.s[k], r.x, y);
    }
    ctx.restore();
    panel(ctx, 70, 330, 940, 760, 'LAYER 2  ·  DECODE', { right: 'SLOW ×0.08' });
    const lines = sc.visual.lines, size = 190, adv = measure(ctx, 'M', size, VT);
    let idx = 0; const total = lines.join('').replace(/ /g, '').length;
    const tStart = 0.5, tEnd = Math.max(2.6, sent(sc, 0) + 1.0);
    let resolving = false;
    const gl = Math.floor(lt / 1.4), inGlitch = lt > tEnd + 0.3 && (lt % 1.4) < 0.1 && hash(gl) > 0.3;
    lines.forEach((ln, li) => {
      const y = 620 + li * 230, x0 = 540 - (adv * ln.length) / 2;
      const jx = inGlitch ? (hash(gl * 7 + li) - 0.5) * 60 : 0;
      for (let ci = 0; ci < ln.length; ci++) {
        const ch = ln[ci]; if (ch === ' ') continue;
        const tr = tStart + (idx / total) * (tEnd - tStart - 0.6) + hash(idx * 3.7) * 0.6; idx++;
        const x = x0 + ci * adv + adv / 2 + jx;
        if (lt < tr) {
          resolving = true;
          const g = GLYPHS[Math.floor(hash(ci * 13 + li * 7 + Math.floor(lt * 18)) * GLYPHS.length)];
          const alt = hash(ci + Math.floor(lt * 9)) > 0.5;
          text(ctx, g, x + (hash(ci + lt) - 0.5) * 6, y + (hash(ci * 2 + lt) - 0.5) * 14, { font: VT, size, align: 'center', color: alt ? C.mag : C.cyan, alpha: lt < tr - 1.6 ? 0.25 : 0.6 });
        } else {
          const fresh = lt - tr < 0.1;
          if (fresh) text(ctx, ch, x - 8, y, { font: VT, size, align: 'center', color: C.cyan, alpha: 0.5 });
          text(ctx, ch, x, y, { font: VT, size, align: 'center', color: C.mag });
        }
      }
    });
    if (lt > tEnd) {
      typeLine(ctx, 'DECODED · 4 WORDS · LOOPING', 540, 430, lt, tEnd, 0.6, { size: 24, align: 'center', color: C.mag, weight: 500, cursor: false });
      text(ctx, `REPETITIONS ${(1180 + Math.floor((lt - tEnd) * 3.4)).toLocaleString('en-US')}`, 540, 1020, { size: 22, align: 'center', alpha: 0.7 });
    }
    return { glitch: inGlitch ? 0.7 : resolving ? 0.12 * (hash(Math.floor(lt * 30)) > 0.7 ? 1 : 0) : 0 };
  },
};

// ----------------------------------------------------------------- 7. the log (terminal scroll)
function fillerLog(n, seed) {
  const R = rng(seed), sys = [['HULL STRAIN GAUGE', 'NOMINAL'], ['CO2 SCRUBBER A', 'NOMINAL'], ['BALLAST TRIM', '+0.1%'], ['ACOUSTIC EVENT', 'LOGGED'], ['THERMAL LOOP', '1.9 C'], ['O2 PARTIAL', '21.0%'], ['TETHER LOAD', '412 KN'], ['HYDROPHONE ARRAY', 'NOMINAL']];
  const out = [];
  for (let i = 0; i < n; i++) {
    const day = 30 + Math.floor((i / n) * 5), hh = Math.floor(R() * 24), mm = Math.floor(R() * 60);
    const [a, b] = i === 1 ? ['ASCENT CAPSULE', 'DEPARTED'] : i === 2 ? ['CREW COUNT', '1'] : sys[Math.floor(R() * sys.length)];
    const time = a === 'ACOUSTIC EVENT' ? '02:14' : `${pad2(hh)}:${pad2(mm)}`;
    out.push(`D${day} ${time}  ${a} ${'.'.repeat(Math.max(2, 22 - a.length))} ${b}`);
  }
  return out;
}
SCENES.terminalLog = {
  init(sc) {
    const filler = fillerLog(22, 37);
    const lines = [...filler, ...sc.visual.lines];
    const hi = filler.length + sc.visual.highlight;
    const tStop = sent(sc, sc.visual.highlightSentence) - 0.05;
    const LH = 44, CY = 705, y0 = 440;
    const tw = tween((tl) => { const s = { off: 0 }; tl.to(s, { off: (hi * LH + y0) - CY, duration: tStop - 0.8, ease: 'power2.inOut' }, 0.8); return s; });
    return { lines, hi, tStop, LH, CY, y0, tw };
  },
  draw(ctx, lt, sc, st) {
    const s = st.tw.seek(lt);
    panel(ctx, 60, 320, 960, 780, 'HADAL-9 :: /var/log/station.log', { right: `${st.lines.length} ENTRIES` });
    typeLine(ctx, '> scan station.log --since D30', 84, 380, lt, 0.2, 0.9, { size: 25, weight: 500, cursor: lt < 1.4 });
    ctx.save(); ctx.beginPath(); ctx.rect(60, 405, 960, 600); ctx.clip();
    st.lines.forEach((ln, i) => {
      const y = st.y0 + i * st.LH - s.off; if (y < 380 || y > 1030) return;
      const hiOn = i === st.hi && lt >= st.tStop;
      if (hiOn) {
        const fl = lt - st.tStop < 0.35 ? (hash(Math.floor(lt * 30)) > 0.4 ? 1 : 0.3) : 0.9;
        ctx.fillStyle = rgba(C.mag, fl); ctx.fillRect(72, y - 21, 936, 42);
        text(ctx, ln, 90, y, { size: 25, color: C.bg, weight: 500 });
      } else {
        const evt = ln.includes('02:14');
        text(ctx, ln, 90, y, { size: 25, alpha: evt ? 0.85 : 0.55, weight: evt ? 500 : 400 });
      }
    });
    ctx.restore();
    stroke(ctx, C.cyan, 0.25, 1); ctx.beginPath(); ctx.moveTo(72, 1012); ctx.lineTo(1008, 1012); ctx.stroke();
    const t3 = sent(sc, 3), t4 = sent(sc, 4);
    typeLine(ctx, '◆ ORIGIN: CONSOLE 1 (THIS TERMINAL)', 90, 1040, lt, t3, 0.6, { size: 22, color: C.mag, weight: 500, cursor: false });
    typeLine(ctx, '◆ D37 = FOUR NIGHTS AGO', 90, 1074, lt, t4, 0.5, { size: 22, color: C.mag, weight: 500, cursor: false });
    return { glitch: lt >= st.tStop && lt - st.tStop < 0.08 ? 0.35 : 0 };
  },
};

// ----------------------------------------------------------------- 8. the question (zoom on the line)
SCENES.logZoom = {
  frame: () => ({ hud: 0.55 }),
  draw(ctx, lt, sc) {
    const z = 1 + 0.1 * gsap.parseEase('sine.inOut')(clamp(lt / sc.duration));
    ctx.save(); ctx.translate(540, 680); ctx.scale(z, z); ctx.translate(-540, -680);
    for (let k = -5; k <= 7; k++) { if (k > -2 && k < 4) continue; text(ctx, 'D3' + (6 + (k & 1)) + ' 02:14  ACOUSTIC EVENT ......... LOGGED', 540, 680 + k * 54, { size: 24, align: 'center', alpha: 0.12 }); }
    const [d, rest] = sc.visual.line.split(/ {2,}/);
    const fl = 0.86 + 0.08 * Math.sin(lt * 3) + (hash(Math.floor(lt * 24)) > 0.94 ? -0.3 : 0);
    ctx.fillStyle = rgba(C.mag, fl); ctx.fillRect(90, 560, 900, 200);
    text(ctx, d, 540, 612, { font: VT, size: 84, align: 'center', color: C.bg });
    text(ctx, rest, 540, 700, { font: VT, size: 84, align: 'center', color: C.bg });
    ctx.restore();
    sc.visual.meta.forEach((m, i) => {
      const last = i === sc.visual.meta.length - 1;
      typeLine(ctx, m, 150, 850 + i * 54, lt, 0.7 + i * 0.85, 0.45, { size: 30, color: last ? C.mag : C.cyan, weight: 500, cursor: last && lt > 0.7 + i * 0.85, keepCursor: last });
    });
    const g = ctx.createRadialGradient(540, 760, 300, 540, 760, 1100);
    g.addColorStop(0, rgba(C.bg, 0)); g.addColorStop(1, rgba(C.bg, 0.85 * smooth(0, 3, lt)));
    ctx.fillStyle = g; ctx.fillRect(0, 0, DW, 1920);
  },
};

// ----------------------------------------------------------------- 9. cliffhanger
function qrs(d) {
  return 0.12 * Math.exp(-(((d + 0.17) / 0.035) ** 2)) - 0.18 * Math.exp(-(((d + 0.025) / 0.01) ** 2)) + 1.0 * Math.exp(-((d / 0.012) ** 2)) - 0.32 * Math.exp(-(((d - 0.03) / 0.012) ** 2)) + 0.22 * Math.exp(-(((d - 0.24) / 0.05) ** 2));
}
SCENES.cliffhanger = {
  init(sc, env) {
    const w = findWord(sc, sc.visual.clockWord); const tw = (w ? w.t0 : 2) + 0.05;
    const fin = sc.voice.sentences.find((s) => s.final) || sc.voice.sentences[sc.voice.sentences.length - 1];
    const sb = fin.start, sa = sb - (fin.silenceBefore || 0), fe = fin.start + fin.duration;
    const beats = env.beats.filter((b) => b.t >= sc.start && b.t < sc.start + sc.duration).map((b) => b.t - sc.start);
    return { tw, sa, sb, fe, beats, base: parseClock(sc.visual.clockAt) };
  },
  frame(lt, sc, st) {
    const black = smooth(sc.duration - 0.6, sc.duration - 0.2, lt);
    return { hud: (1 - 0.6 * smooth(st.sa, st.sa + 0.3, lt)) * (1 - black), ambient: 1 - black, rings: lt < st.sa - 0.6, captionsFade: sc.duration - 0.6 };
  },
  draw(ctx, lt, sc, st) {
    const dim = 1 - 0.65 * smooth(st.sa, st.sa + 0.3, lt);
    ctx.save(); ctx.globalAlpha = dim;
    const secs = st.base + Math.floor(lt - st.tw + 1e-6), hit = lt >= st.tw, dh = lt - st.tw;
    const pop = hit ? 1 + 0.1 * Math.exp(-dh * 10) : 1;
    ctx.save(); ctx.translate(540, 520); ctx.scale(pop, pop);
    if (hit && dh < 0.1) text(ctx, hms(secs), -8, 0, { font: VT, size: 220, align: 'center', color: C.cyan, alpha: 0.5 });
    text(ctx, hms(secs), 0, 0, { font: VT, size: 220, align: 'center', color: hit ? C.mag : C.cyan });
    ctx.restore();
    text(ctx, hit ? 'SIGNAL WINDOW OPEN' : 'LOCAL TIME · D41', 540, 650, { size: 26, align: 'center', color: hit ? C.mag : C.cyan, weight: 500, spacing: 6, alpha: 0.9 });
    // ECG
    let lastBeat = -9, hr = '--';
    for (let i = 0; i < st.beats.length; i++) if (st.beats[i] <= lt) { lastBeat = st.beats[i]; if (i) hr = String(Math.round(60 / (st.beats[i] - st.beats[i - 1]))); }
    const flat = lt >= st.sa;
    panel(ctx, 70, 730, 940, 240, 'ECG · OPERATOR-01', { right: `HR ${flat ? '--' : hr} BPM` });
    stroke(ctx, C.cyan, 0.95, 2.5); ctx.beginPath();
    let lx = 0, ly = 0;
    for (let x = 0; x <= 940; x += 2) {
      const tau = lt - (940 - x) / 235;
      let v = 0;
      if (tau < st.sa) for (const b of st.beats) { const dd = tau - b; if (dd > -0.3 && dd < 0.4) v += qrs(dd); }
      v += (hash(x * 0.37 + Math.floor(lt * 30)) - 0.5) * 0.03;
      const y = 880 - v * 110;
      x ? ctx.lineTo(70 + x, y) : ctx.moveTo(70 + x, y); lx = 70 + x; ly = y;
    }
    ctx.stroke();
    ctx.fillStyle = rgba(C.cyan, 1); ctx.beginPath(); ctx.arc(lx, ly, 6, 0, TAU); ctx.fill();
    ctx.restore();
    // the first magenta sonar ripple, with the final line
    const ra = lt - st.sb;
    if (ra >= 0) {
      for (let k = 0; k < 4; k++) {
        const a = ra - k * 0.45; if (a < 0) continue;
        stroke(ctx, C.mag, Math.max(0, 1 - a / 4) * (k ? 0.5 : 0.95), 5 - k);
        ctx.beginPath(); ctx.arc(540, 760, a * 430, 0, TAU); ctx.stroke();
      }
      ctx.fillStyle = rgba(C.mag, Math.exp(-ra * 2)); ctx.beginPath(); ctx.arc(540, 760, 12, 0, TAU); ctx.fill();
    }
    // cut to black
    const black = smooth(sc.duration - 0.6, sc.duration - 0.2, lt);
    if (black > 0) { ctx.fillStyle = rgba('#000000', black); ctx.fillRect(0, 0, DW, 1920); }
    const pulse = flat ? 0 : 0.1 * Math.exp(-(lt - lastBeat) * 8);
    return { pulse, glitch: hit && dh < 0.07 ? 0.4 : 0 };
  },
};
