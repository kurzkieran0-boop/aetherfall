// Procedural Web Audio score (~110 BPM): plucked arpeggio melody, soft
// kick/clap/hat loop, warm bass, pads, a riser into the cliffhanger and a
// dramatic drop; plus synthesized SFX (whooshes, paper rustle, bells, tram
// bell, door hum, knocks, impacts). Rendered with OfflineAudioContext so the
// export is deterministic; the same graph plays live in the dev preview.

const CHORDS = [
  { root: 33, arp: [57, 60, 64] }, // Am
  { root: 29, arp: [57, 60, 65] }, // F
  { root: 36, arp: [55, 60, 64] }, // C
  { root: 31, arp: [55, 59, 62] }, // G
];
const LEAD = [76, null, 76, 74, 72, null, 71, 72, 69, null, null, 67, 69, null, 72, 74];
const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);

function lcg(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

export async function renderScore(tl, sampleRate = 48000) {
  const len = Math.ceil(tl.duration * sampleRate) + sampleRate;
  const ctx = new OfflineAudioContext(2, len, sampleRate);
  buildGraph(ctx, tl, 0);
  return ctx.startRendering();
}

export function playLive(tl, offset = 0) {
  const ctx = new AudioContext({ sampleRate: 48000 });
  buildGraph(ctx, tl, ctx.currentTime + 0.1 - offset);
  return ctx;
}

function buildGraph(ctx, tl, T0) {
  const rnd = lcg(1234);
  const sr = ctx.sampleRate;
  // shared noise
  const nb = ctx.createBuffer(1, sr * 2, sr);
  const nd = nb.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = rnd() * 2 - 1;
  // reverb impulse
  const ir = ctx.createBuffer(2, Math.floor(sr * 2.6), sr);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    for (let i = 0; i < d.length; i++) d[i] = (rnd() * 2 - 1) * Math.pow(1 - i / d.length, 3.2);
  }
  const master = ctx.createGain();
  master.gain.value = 0.9;
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -14; comp.ratio.value = 3.5; comp.attack.value = 0.005; comp.release.value = 0.18;
  master.connect(comp).connect(ctx.destination);
  const music = ctx.createGain();
  music.connect(master);
  const sfx = ctx.createGain();
  sfx.gain.value = 0.85;
  sfx.connect(master);
  const verb = ctx.createConvolver();
  verb.buffer = ir;
  const verbGain = ctx.createGain();
  verbGain.gain.value = 0.35;
  verb.connect(verbGain).connect(master);
  const delay = ctx.createDelay(2);
  const beat = 60 / tl.bpm;
  delay.delayTime.value = beat * 0.75;
  const fb = ctx.createGain(); fb.gain.value = 0.3;
  const dlp = ctx.createBiquadFilter(); dlp.type = 'lowpass'; dlp.frequency.value = 2600;
  delay.connect(dlp).connect(fb).connect(delay);
  const dOut = ctx.createGain(); dOut.gain.value = 0.35;
  dlp.connect(dOut).connect(music);

  // ---- ducking: score sits 8 dB under the voice
  const duck = Math.pow(10, -8 / 20);
  music.gain.setValueAtTime(1, 0);
  for (const l of tl.lines) {
    music.gain.setTargetAtTime(duck, Math.max(0, T0 + l.start - 0.12), 0.035);
    music.gain.setTargetAtTime(1, T0 + l.end + 0.08, 0.12);
  }

  const noise = (t, dur, dest, gain = 1) => {
    const s = ctx.createBufferSource();
    s.buffer = nb; s.loop = true;
    const g = ctx.createGain();
    g.gain.value = gain;
    s.connect(g).connect(dest);
    s.start(Math.max(0, t), rnd() * 1.5, dur + 0.1);
    return g;
  };
  const filt = (type, f, q = 1) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = q; return b; };
  const pan = (p, dest) => { const s = ctx.createStereoPanner(); s.pan.value = p; s.connect(dest); return s; };

  // ---------------------------------------------------------- instruments
  const kick = (t, v = 1) => {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(165, t);
    o.frequency.exponentialRampToValueAtTime(44, t + 0.13);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.95 * v, t + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.42);
    o.connect(g).connect(music);
    o.start(t); o.stop(t + 0.45);
  };
  const clap = (t, v = 1) => {
    const bp = filt('bandpass', 1500, 0.9);
    const g = noise(t, 0.3, bp, 1);
    const out = ctx.createGain();
    bp.connect(out); out.connect(music); out.connect(verb);
    out.gain.setValueAtTime(0.0001, t);
    for (let k = 0; k < 3; k++) {
      out.gain.setValueAtTime(0.55 * v, t + k * 0.011);
      out.gain.exponentialRampToValueAtTime(0.08 * v, t + k * 0.011 + 0.009);
    }
    out.gain.setValueAtTime(0.45 * v, t + 0.034);
    out.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
    void g;
  };
  const hat = (t, v = 1, open = false) => {
    const hp = filt('highpass', 7800, 0.7);
    noise(t, 0.2, hp, 1);
    const g = ctx.createGain();
    hp.connect(pan(0.25, g)); g.connect(music);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.13 * v, t + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (open ? 0.16 : 0.045));
  };
  const bass = (t, m, d, v = 1) => {
    const o = ctx.createOscillator(), o2 = ctx.createOscillator(), f = filt('lowpass', 300, 5), g = ctx.createGain();
    o.type = 'sawtooth'; o2.type = 'square';
    o.frequency.value = mtof(m); o2.frequency.value = mtof(m - 12);
    const g2 = ctx.createGain(); g2.gain.value = 0.5;
    o.connect(f); o2.connect(g2).connect(f);
    f.frequency.setValueAtTime(220, t);
    f.frequency.linearRampToValueAtTime(950, t + 0.02);
    f.frequency.exponentialRampToValueAtTime(260, t + d);
    f.connect(g).connect(music);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.32 * v, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.05);
    o.start(t); o2.start(t); o.stop(t + d + 0.1); o2.stop(t + d + 0.1);
  };
  const pluck = (t, m, v = 1, p = 0) => {
    const o = ctx.createOscillator(), o2 = ctx.createOscillator(), f = filt('lowpass', 4000, 2), g = ctx.createGain();
    o.type = 'triangle'; o2.type = 'sawtooth';
    o.frequency.value = mtof(m); o2.frequency.value = mtof(m) * 1.004;
    const g2 = ctx.createGain(); g2.gain.value = 0.25;
    o.connect(f); o2.connect(g2).connect(f);
    f.frequency.setValueAtTime(5200, t);
    f.frequency.exponentialRampToValueAtTime(650, t + 0.22);
    const pn = pan(p, music);
    f.connect(g); g.connect(pn); g.connect(delay);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.15 * v, t + 0.003);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.34);
    o.start(t); o2.start(t); o.stop(t + 0.4); o2.stop(t + 0.4);
  };
  const lead = (t, m, d, v = 1) => {
    const o = ctx.createOscillator(), lfo = ctx.createOscillator(), lg = ctx.createGain(), f = filt('lowpass', 2600, 1), g = ctx.createGain();
    o.type = 'square'; o.frequency.value = mtof(m);
    lfo.frequency.value = 5.5; lg.gain.value = 4;
    lfo.connect(lg).connect(o.frequency);
    o.connect(f).connect(g);
    g.connect(music); g.connect(delay); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.055 * v, t + 0.02);
    g.gain.setTargetAtTime(0.0001, t + d * 0.7, 0.08);
    o.start(t); lfo.start(t); o.stop(t + d + 0.4); lfo.stop(t + d + 0.4);
  };
  const pad = (t, notes, d, v = 1) => {
    const f = filt('lowpass', 1100, 0.7), g = ctx.createGain();
    f.connect(g); g.connect(music); g.connect(verb);
    for (const m of notes) for (const det of [-8, 8]) {
      const o = ctx.createOscillator();
      o.type = 'sawtooth'; o.frequency.value = mtof(m); o.detune.value = det;
      o.connect(f); o.start(t); o.stop(t + d + 1.2);
    }
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.022 * v, t + Math.min(0.6, d * 0.4));
    g.gain.setValueAtTime(0.022 * v, t + d);
    g.gain.linearRampToValueAtTime(0.0001, t + d + 1.0);
  };

  // ---------------------------------------------------------- the score
  const sections = tl.music;
  const sectionAt = (t) => sections.find((s) => t >= s.start && t < s.end) || sections[sections.length - 1];
  const step = beat / 4;
  const nSteps = Math.ceil(tl.duration / step);
  for (let i = 0; i < nSteps; i++) {
    const tt = i * step;
    const sec = sectionAt(tt + 1e-4);
    const m = sec.flags;
    const t = T0 + tt;
    if (t < 0) continue;
    const bar = Math.floor(i / 16);
    const ch = CHORDS[bar % 4];
    const s16 = i % 16;
    const e = m.energy ?? 1;
    if (m.kick && (s16 % 4 === 0 || (m.kick === 'busy' && s16 === 10))) kick(t, e);
    if (m.clap && (s16 === 4 || s16 === 12)) clap(t, e);
    if (m.hats) {
      if (m.hats === '16' || s16 % 2 === 0) hat(t, (s16 % 4 === 2 ? 1 : 0.55) * e, m.hats === 'open' && s16 % 4 === 2);
    }
    if (m.bass && s16 % 2 === 0) {
      const pat = [0, 0, 12, 0, 0, 12, 7, 12];
      bass(t, ch.root + pat[(s16 / 2) % 8], step * 1.7, e);
    }
    if (m.arp && (m.arp === '16' || s16 % 2 === 0)) {
      const seq = [0, 1, 2, 3, 2, 1, 2, 3];
      const k = seq[(m.arp === '16' ? s16 : s16 / 2) % 8];
      const note = k === 3 ? ch.arp[0] + 12 : ch.arp[k];
      pluck(t, note, (s16 % 4 === 0 ? 1 : 0.7) * (m.arpLevel ?? 1), (i % 2 ? 0.3 : -0.3));
    }
    if (m.lead && s16 % 2 === 0) {
      const n = LEAD[((bar % 2) * 8 + s16 / 2) % 16];
      if (n) lead(t, n, step * 1.8, e);
    }
    if (m.pad && s16 === 0) pad(t, ch.arp.map((n) => n - 12), beat * 4, m.pad === 'loud' ? 1.6 : 1);
    if (m.drone && s16 === 0 && bar % 2 === 0) pad(t, [38, 45, 50], beat * 8, 1.2);
  }

  // ---------------------------------------------------------- sfx
  for (const ev of tl.sfx) {
    const t = T0 + ev.t;
    if (t < 0) continue;
    switch (ev.type) {
      case 'whoosh': whoosh(t, ev.dir || 1, ev.gain ?? 1); break;
      case 'rustle': rustle(t, ev.dur || 1.2, ev.gain ?? 1, false); break;
      case 'flutter': rustle(t, ev.dur || 2, ev.gain ?? 1, true); break;
      case 'bell': bells(t, ev.n || 4, ev.gain ?? 1); break;
      case 'tram': tramBell(t, ev.gain ?? 1); break;
      case 'hum': hum(t, ev.dur || 3, ev.gain ?? 1); break;
      case 'knock': knock(t, ev.n || 3, ev.gain ?? 1); break;
      case 'impact': impact(t, ev.gain ?? 1); break;
      case 'riser': riser(t, ev.dur || 6, ev.gain ?? 1); break;
      case 'chime': chime(t, ev.gain ?? 1); break;
      case 'creak': creak(t, ev.dur || 1.6, ev.gain ?? 1); break;
      case 'tick': ticks(t, ev.dur || 3, ev.gain ?? 1); break;
      case 'wind': wind(t, ev.dur || 4, ev.gain ?? 1); break;
      case 'engine': engine(t, ev.dur || 3, ev.gain ?? 1, ev.from ?? 60, ev.to ?? 160); break;
      case 'screech': screech(t, ev.dur || 1, ev.gain ?? 1); break;
      case 'siren': siren(t, ev.dur || 3, ev.gain ?? 1); break;
      case 'buzz': buzz(t, ev.dur || 3, ev.gain ?? 1); break;
      case 'glitch': glitch(t, ev.dur || 1, ev.gain ?? 1); break;
      case 'click': knock(t, 1, 0.4 * (ev.gain ?? 1)); chime(t + 0.05, 0.6 * (ev.gain ?? 1)); break;
      case 'ding': bellTone(t, 880, 0.9 * (ev.gain ?? 1)); break;
      case 'rain': rainBed(t, ev.dur || 10, ev.gain ?? 1); break;
      default: break;
    }
  }

  function whoosh(t, dir, v) {
    const bp = filt('bandpass', 400, 1.3);
    const st = t - 0.38, en = t + 0.22;
    noise(st, en - st, bp, 1);
    bp.frequency.setValueAtTime(300, st);
    bp.frequency.exponentialRampToValueAtTime(2600, t);
    bp.frequency.exponentialRampToValueAtTime(500, en);
    const p = ctx.createStereoPanner();
    p.pan.setValueAtTime(-0.8 * dir, st);
    p.pan.linearRampToValueAtTime(0.8 * dir, en);
    const g = ctx.createGain();
    bp.connect(g).connect(p).connect(sfx);
    g.connect(verb);
    g.gain.setValueAtTime(0.0001, st);
    g.gain.exponentialRampToValueAtTime(0.75 * v, t);
    g.gain.exponentialRampToValueAtTime(0.0001, en);
  }
  function rustle(t, dur, v, flutter) {
    const n = Math.floor(dur * (flutter ? 40 : 28));
    for (let k = 0; k < n; k++) {
      const tt = t + (flutter ? (k / n) * dur + rnd() * 0.02 : rnd() * dur);
      const bp = filt('bandpass', 2200 + rnd() * 5000, 1.8);
      noise(tt, 0.08, bp, 1);
      const g = ctx.createGain();
      bp.connect(pan(rnd() * 1.4 - 0.7, g));
      g.connect(sfx);
      const a = (flutter ? 0.22 + 0.2 * Math.abs(Math.sin(k * 0.9)) : 0.12 + rnd() * 0.22) * v;
      g.gain.setValueAtTime(0.0001, tt);
      g.gain.linearRampToValueAtTime(a, tt + 0.004);
      g.gain.exponentialRampToValueAtTime(0.0001, tt + 0.02 + rnd() * 0.05);
    }
  }
  function bellTone(t, f0, v, dest = sfx) {
    const parts = [[0.5, 0.7, 4.5], [1, 1, 3.6], [1.19, 0.55, 2.8], [1.5, 0.45, 2.2], [2, 0.4, 1.8], [2.51, 0.22, 1.3], [3.01, 0.16, 1.0], [4.17, 0.1, 0.7]];
    const g = ctx.createGain();
    g.gain.value = 0.16 * v;
    g.connect(dest); g.connect(verb);
    for (const [r, a, d] of parts) {
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.frequency.value = f0 * r;
      o.connect(og).connect(g);
      og.gain.setValueAtTime(0.0001, t);
      og.gain.linearRampToValueAtTime(a, t + 0.004);
      og.gain.exponentialRampToValueAtTime(0.0001, t + d);
      o.start(t); o.stop(t + d + 0.05);
    }
  }
  function bells(t, n, v) {
    const f = [293.66, 220, 246.94, 196];
    for (let k = 0; k < n; k++) bellTone(t + k * beat * 2, f[k % f.length], v);
  }
  function tramBell(t, v) {
    for (const off of [0, 0.17]) {
      for (const [r, a, d] of [[1, 1, 0.6], [2.76, 0.5, 0.35], [5.4, 0.25, 0.2]]) {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = 1320 * r;
        o.connect(g).connect(sfx);
        g.gain.setValueAtTime(0.0001, t + off);
        g.gain.linearRampToValueAtTime(0.12 * a * v, t + off + 0.002);
        g.gain.exponentialRampToValueAtTime(0.0001, t + off + d);
        o.start(t + off); o.stop(t + off + d);
      }
    }
  }
  function hum(t, dur, v) {
    const g = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
    lfo.frequency.value = 5.2; lg.gain.value = 0.25;
    lfo.connect(lg).connect(g.gain);
    g.connect(sfx); g.connect(verb);
    const env = ctx.createGain();
    env.connect(g);
    env.gain.setValueAtTime(0.0001, t);
    env.gain.linearRampToValueAtTime(0.5 * v, t + dur * 0.35);
    env.gain.setValueAtTime(0.5 * v, t + dur * 0.8);
    env.gain.linearRampToValueAtTime(0.0001, t + dur);
    for (const [f, a] of [[73.42, 0.5], [146.83, 0.3], [220, 0.22], [293.66, 0.12], [440.5, 0.06]]) {
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.frequency.value = f; og.gain.value = a * 0.6;
      o.connect(og).connect(env);
      o.start(t); o.stop(t + dur + 0.1);
    }
    lfo.start(t); lfo.stop(t + dur + 0.1);
  }
  function knock(t, n, v) {
    for (let k = 0; k < n; k++) {
      const tt = t + k * 0.27;
      const lp = filt('lowpass', 900, 1);
      noise(tt, 0.1, lp, 1);
      const g = ctx.createGain();
      lp.connect(g); g.connect(sfx); g.connect(verb);
      g.gain.setValueAtTime(0.0001, tt);
      g.gain.linearRampToValueAtTime(0.9 * v, tt + 0.002);
      g.gain.exponentialRampToValueAtTime(0.0001, tt + 0.08);
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.frequency.setValueAtTime(150, tt);
      o.frequency.exponentialRampToValueAtTime(75, tt + 0.09);
      o.connect(og).connect(sfx);
      og.gain.setValueAtTime(0.0001, tt);
      og.gain.linearRampToValueAtTime(0.7 * v, tt + 0.003);
      og.gain.exponentialRampToValueAtTime(0.0001, tt + 0.12);
      o.start(tt); o.stop(tt + 0.15);
    }
  }
  function impact(t, v) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(70, t);
    o.frequency.exponentialRampToValueAtTime(27, t + 1.4);
    o.connect(g).connect(sfx);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(1.0 * v, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 1.8);
    o.start(t); o.stop(t + 1.9);
    const lp = filt('lowpass', 2400, 0.8);
    noise(t, 1.2, lp, 1);
    const ng = ctx.createGain();
    lp.connect(ng); ng.connect(sfx); ng.connect(verb);
    ng.gain.setValueAtTime(0.0001, t);
    ng.gain.linearRampToValueAtTime(0.6 * v, t + 0.005);
    ng.gain.exponentialRampToValueAtTime(0.0001, t + 0.9);
    kick(t, 1.2 * v);
  }
  function riser(t, dur, v) {
    const bp = filt('bandpass', 300, 2.5);
    noise(t, dur, bp, 1);
    bp.frequency.setValueAtTime(250, t);
    bp.frequency.exponentialRampToValueAtTime(7500, t + dur);
    const g = ctx.createGain();
    bp.connect(g); g.connect(sfx); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.5 * v, t + dur);
    g.gain.setValueAtTime(0.0001, t + dur + 0.01);
    const o = ctx.createOscillator(), og = ctx.createGain(), of = filt('lowpass', 2000, 1);
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(110, t);
    o.frequency.exponentialRampToValueAtTime(880, t + dur);
    o.connect(of).connect(og).connect(sfx);
    og.gain.setValueAtTime(0.0001, t);
    og.gain.exponentialRampToValueAtTime(0.09 * v, t + dur);
    og.gain.setValueAtTime(0.0001, t + dur + 0.01);
    o.start(t); o.stop(t + dur + 0.05);
    // accelerating snare roll in the last two bars
    const rollStart = t + Math.max(0, dur - beat * 8);
    let tt = rollStart, k = 0;
    while (tt < t + dur - 0.02) {
      const prog = (tt - rollStart) / (t + dur - rollStart);
      clap(tt, 0.25 + prog * 0.6);
      tt += prog < 0.5 ? beat / 2 : prog < 0.8 ? beat / 4 : beat / 8;
      if (++k > 64) break;
    }
  }
  function chime(t, v) {
    const notes = [86, 89, 93, 98, 93];
    notes.forEach((m, k) => {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'sine'; o.frequency.value = mtof(m);
      o.connect(g); g.connect(sfx); g.connect(verb);
      const tt = t + k * 0.07;
      g.gain.setValueAtTime(0.0001, tt);
      g.gain.linearRampToValueAtTime(0.07 * v, tt + 0.003);
      g.gain.exponentialRampToValueAtTime(0.0001, tt + 1.2);
      o.start(tt); o.stop(tt + 1.3);
    });
  }
  function creak(t, dur, v) {
    const o = ctx.createOscillator(), f = filt('bandpass', 700, 4), g = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
    o.type = 'sawtooth'; o.frequency.value = 85;
    lfo.frequency.value = 9; lg.gain.value = 18;
    lfo.connect(lg).connect(o.frequency);
    o.connect(f).connect(g); g.connect(sfx); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.22 * v, t + 0.2);
    g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.frequency.linearRampToValueAtTime(60, t + dur);
    o.start(t); lfo.start(t); o.stop(t + dur + 0.05); lfo.stop(t + dur + 0.05);
  }
  function ticks(t, dur, v) {
    for (let tt = t; tt < t + dur; tt += 0.5) {
      const hp = filt('highpass', 3000, 1);
      noise(tt, 0.03, hp, 1);
      const g = ctx.createGain();
      hp.connect(g).connect(sfx);
      g.gain.setValueAtTime(0.0001, tt);
      g.gain.linearRampToValueAtTime(0.35 * v, tt + 0.001);
      g.gain.exponentialRampToValueAtTime(0.0001, tt + 0.025);
    }
  }
  function engine(t, dur, v, f0, f1) {
    const o = ctx.createOscillator(), o2 = ctx.createOscillator(), f = filt('lowpass', 900, 3), g = ctx.createGain();
    o.type = 'sawtooth'; o2.type = 'square';
    o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur * 0.85);
    o2.frequency.setValueAtTime(f0 / 2, t); o2.frequency.exponentialRampToValueAtTime(f1 / 2, t + dur * 0.85);
    f.frequency.setValueAtTime(500, t); f.frequency.exponentialRampToValueAtTime(2600, t + dur * 0.8);
    const g2 = ctx.createGain(); g2.gain.value = 0.6;
    o.connect(f); o2.connect(g2).connect(f); f.connect(g).connect(sfx);
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.22 * v, t + 0.15);
    g.gain.setValueAtTime(0.22 * v, t + dur * 0.8); g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.start(t); o2.start(t); o.stop(t + dur + 0.05); o2.stop(t + dur + 0.05);
  }
  function screech(t, dur, v) {
    const bp = filt('bandpass', 2800, 8);
    noise(t, dur, bp, 1);
    const o = ctx.createOscillator(), og = ctx.createGain();
    o.frequency.setValueAtTime(1900, t); o.frequency.linearRampToValueAtTime(1500, t + dur);
    const g = ctx.createGain();
    bp.connect(g); o.connect(og).connect(g); og.gain.value = 0.15;
    g.connect(sfx); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.35 * v, t + 0.05); g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.start(t); o.stop(t + dur + 0.05);
  }
  function siren(t, dur, v) {
    const o = ctx.createOscillator(), g = ctx.createGain(), f = filt('lowpass', 2500, 1);
    o.type = 'triangle';
    for (let tt = 0; tt < dur; tt += 0.5) o.frequency.setValueAtTime(Math.floor(tt * 2) % 2 ? 660 : 880, t + tt);
    o.connect(f).connect(g); g.connect(sfx); g.connect(verb);
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.09 * v, t + 0.2); g.gain.setValueAtTime(0.09 * v, t + dur - 0.3); g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.start(t); o.stop(t + dur + 0.05);
  }
  function buzz(t, dur, v) {
    const o = ctx.createOscillator(), lfo = ctx.createOscillator(), lg = ctx.createGain(), f = filt('bandpass', 420, 2), g = ctx.createGain();
    o.type = 'sawtooth'; o.frequency.value = 118; lfo.frequency.value = 23; lg.gain.value = 14;
    lfo.connect(lg).connect(o.frequency);
    o.connect(f).connect(g); g.connect(sfx);
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.12 * v, t + dur * 0.3); g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.start(t); lfo.start(t); o.stop(t + dur + 0.05); lfo.stop(t + dur + 0.05);
  }
  function glitch(t, dur, v) {
    for (let tt = 0; tt < dur; tt += 0.045 + rnd() * 0.07) {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'square'; o.frequency.value = 200 + rnd() * 2200;
      o.connect(g); g.connect(sfx);
      const d = 0.02 + rnd() * 0.05;
      g.gain.setValueAtTime(0.06 * v, t + tt); g.gain.setValueAtTime(0.0001, t + tt + d);
      o.start(t + tt); o.stop(t + tt + d + 0.01);
    }
  }
  function rainBed(t, dur, v) {
    const hp = filt('highpass', 1800, 0.5), lp = filt('lowpass', 9000, 0.5);
    noise(t, dur, hp, 1);
    const g = ctx.createGain();
    hp.connect(lp).connect(g); g.connect(sfx);
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.06 * v, t + 0.8);
    g.gain.setValueAtTime(0.06 * v, t + dur - 1); g.gain.linearRampToValueAtTime(0.0001, t + dur);
  }
  function wind(t, dur, v) {
    const bp = filt('bandpass', 500, 0.6);
    noise(t, dur, bp, 1);
    const lfo = ctx.createOscillator(), lg = ctx.createGain();
    lfo.frequency.value = 0.3; lg.gain.value = 250;
    lfo.connect(lg).connect(bp.frequency);
    const g = ctx.createGain();
    bp.connect(g).connect(sfx);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.16 * v, t + Math.min(1, dur / 3));
    g.gain.setValueAtTime(0.16 * v, t + dur * 0.7);
    g.gain.linearRampToValueAtTime(0.0001, t + dur);
    lfo.start(t); lfo.stop(t + dur);
  }
}

export function bufferToWavBase64(buf) {
  const ch = buf.numberOfChannels, n = buf.length, sr = buf.sampleRate;
  const data = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const ws = (o, s) => { for (let i = 0; i < s.length; i++) data.setUint8(o + i, s.charCodeAt(i)); };
  ws(0, 'RIFF'); data.setUint32(4, 36 + n * ch * 2, true); ws(8, 'WAVE'); ws(12, 'fmt ');
  data.setUint32(16, 16, true); data.setUint16(20, 1, true); data.setUint16(22, ch, true);
  data.setUint32(24, sr, true); data.setUint32(28, sr * ch * 2, true); data.setUint16(32, ch * 2, true); data.setUint16(34, 16, true);
  ws(36, 'data'); data.setUint32(40, n * ch * 2, true);
  const chans = [];
  for (let c = 0; c < ch; c++) chans.push(buf.getChannelData(c));
  let o = 44;
  for (let i = 0; i < n; i++) for (let c = 0; c < ch; c++) {
    const v = Math.max(-1, Math.min(1, chans[c][i]));
    data.setInt16(o, v < 0 ? v * 0x8000 : v * 0x7fff, true);
    o += 2;
  }
  const bytes = new Uint8Array(data.buffer);
  let s = '';
  const CH = 0x8000;
  for (let i = 0; i < bytes.length; i += CH) s += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
  return btoa(s);
}
