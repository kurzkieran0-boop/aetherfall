// Procedural Web Audio score + SFX + voice mix. Deterministic (seeded) so the
// realtime preview and the OfflineAudioContext export render the same music.
//   score: soft drone, pad, music-box motif, ticking clock (louder toward the end)
//   bells: additive inharmonic bell synthesised in code
//   score bus is ducked 10 dB under every narration region
import { rng } from './materials.js';

const CHORDS = {
  Dm: { root: 73.42, tones: [146.83, 174.61, 220.0] },
  Bb: { root: 58.27, tones: [116.54, 146.83, 174.61] },
  Gm: { root: 49.0, tones: [98.0, 116.54, 146.83] },
  F: { root: 87.31, tones: [174.61, 220.0, 261.63] },
  A: { root: 55.0, tones: [110.0, 138.59, 164.81] },
};
const midi = (m) => 440 * Math.pow(2, (m - 69) / 12);
// lullaby motif in D minor (16 eighth-note steps, 0 = rest)
const MOTIF = [81, 0, 86, 84, 81, 0, 77, 0, 79, 81, 0, 0, 76, 77, 74, 0];
const MOTIF_B = [74, 0, 77, 76, 74, 0, 72, 74, 76, 0, 81, 0, 79, 77, 76, 0];

function noiseBuffer(ctx, seconds, seed, brown = false) {
  const R = rng(seed);
  const b = ctx.createBuffer(1, Math.floor(ctx.sampleRate * seconds), ctx.sampleRate);
  const d = b.getChannelData(0);
  let last = 0;
  for (let i = 0; i < d.length; i++) {
    const w = R() * 2 - 1;
    if (brown) { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; } else d[i] = w;
  }
  return b;
}

function impulse(ctx, seconds, seed) {
  const R = rng(seed);
  const n = Math.floor(ctx.sampleRate * seconds);
  const b = ctx.createBuffer(2, n, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(c);
    for (let i = 0; i < n; i++) d[i] = (R() * 2 - 1) * Math.pow(1 - i / n, 2.6) * (i < 200 ? i / 200 : 1);
  }
  return b;
}

export function buildMix(ctx, tl, voices, T0 = 0) {
  const R = rng(1234);
  const dur = tl.duration;
  const at = (t) => T0 + Math.max(0, t);

  // ---- buses
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -10; comp.knee.value = 8; comp.ratio.value = 5; comp.attack.value = 0.004; comp.release.value = 0.25;
  const master = ctx.createGain();
  master.gain.value = 0.92;
  master.connect(comp).connect(ctx.destination);
  const voiceBus = ctx.createGain(); voiceBus.gain.value = 1.0; voiceBus.connect(master);
  const fxBus = ctx.createGain(); fxBus.gain.value = 0.8; fxBus.connect(master);
  const musicMaster = ctx.createGain(); musicMaster.gain.value = 1; musicMaster.connect(master);
  const duck = ctx.createGain(); duck.gain.value = 1; duck.connect(musicMaster);
  const score = ctx.createGain(); score.gain.value = 0.85; score.connect(duck);
  const verb = ctx.createConvolver(); verb.buffer = impulse(ctx, 3.8, 99);
  const verbWet = ctx.createGain(); verbWet.gain.value = 0.42; verb.connect(verbWet).connect(score);
  const delay = ctx.createDelay(2); delay.delayTime.value = 0.68;
  const fb = ctx.createGain(); fb.gain.value = 0.32;
  const dlp = ctx.createBiquadFilter(); dlp.type = 'lowpass'; dlp.frequency.value = 2600;
  delay.connect(dlp).connect(fb).connect(delay);
  const delayOut = ctx.createGain(); delayOut.gain.value = 0.35; dlp.connect(delayOut).connect(score);
  const voiceVerb = ctx.createConvolver(); voiceVerb.buffer = impulse(ctx, 1.2, 5);
  const vv = ctx.createGain(); vv.gain.value = 0.1; voiceVerb.connect(vv).connect(master);

  // ---- ducking: -10 dB under narration
  const DUCK = Math.pow(10, -10 / 20);
  const regs = [];
  for (const [a, b] of tl.voiceRegions) {
    const l = regs[regs.length - 1];
    if (l && a - l[1] < 1.1) l[1] = b; else regs.push([a, b]);
  }
  duck.gain.setValueAtTime(1, at(0));
  for (const [a, b] of regs) {
    duck.gain.setValueAtTime(1, at(a - 0.4));
    duck.gain.linearRampToValueAtTime(DUCK, at(a - 0.05));
    duck.gain.setValueAtTime(DUCK, at(b));
    duck.gain.linearRampToValueAtTime(1, at(b + 0.75));
  }

  // ---- silence (music drops out) + restore at end card
  const silence = tl.events.find((e) => e.type === 'silence');
  const endT = tl.endCard.start;
  if (silence) {
    musicMaster.gain.setValueAtTime(1, at(silence.t - 0.05));
    musicMaster.gain.linearRampToValueAtTime(0, at(silence.t + 0.25));
    musicMaster.gain.setValueAtTime(0, at(endT - 0.05));
    musicMaster.gain.linearRampToValueAtTime(1, at(endT + 0.1));
  }
  const musicOff = (t) => silence && t > silence.t && t < endT;

  // ---- per-scene mood automation
  const sceneAt = (t) => { let s = tl.scenes[0]; for (const x of tl.scenes) if (x.start <= t) s = x; return s; };

  // drone
  const droneOsc = [], droneG = ctx.createGain(), droneLP = ctx.createBiquadFilter();
  droneLP.type = 'lowpass'; droneLP.frequency.value = 420; droneLP.Q.value = 0.7;
  droneG.gain.value = 0;
  droneLP.connect(droneG); droneG.connect(score); droneG.connect(verb);
  [[1, 'sawtooth', 0.0], [1.5, 'sawtooth', 4], [0.5, 'sine', 0], [1.003, 'sawtooth', -6]].forEach(([mul, type, det]) => {
    const o = ctx.createOscillator(); o.type = type; o.detune.value = det;
    o.frequency.value = CHORDS.Dm.root * mul; o.connect(droneLP);
    o.start(at(0)); o.stop(at(dur + 0.5));
    droneOsc.push([o, mul]);
  });
  const lfo = ctx.createOscillator(); lfo.frequency.value = 0.07;
  const lfoG = ctx.createGain(); lfoG.gain.value = 160; lfo.connect(lfoG).connect(droneLP.frequency);
  lfo.start(at(0)); lfo.stop(at(dur + 0.5));
  // pad
  const padG = ctx.createGain(); padG.gain.value = 0;
  const padLP = ctx.createBiquadFilter(); padLP.type = 'lowpass'; padLP.frequency.value = 1300;
  padLP.connect(padG); padG.connect(score); padG.connect(verb);
  const padOsc = [];
  for (let i = 0; i < 3; i++) for (const det of [-7, 7]) {
    const o = ctx.createOscillator(); o.type = 'triangle'; o.detune.value = det;
    o.frequency.value = CHORDS.Dm.tones[i]; o.connect(padLP);
    o.start(at(0)); o.stop(at(dur + 0.5));
    padOsc.push([o, i]);
  }
  for (const s of tl.scenes) {
    const ch = CHORDS[s.sound.chord] || CHORDS.Dm;
    const t = s.start;
    droneOsc.forEach(([o, mul]) => o.frequency.setTargetAtTime(ch.root * mul, at(t), 0.5));
    padOsc.forEach(([o, i]) => o.frequency.setTargetAtTime(ch.tones[i], at(t), 0.6));
    droneG.gain.setTargetAtTime(0.055 * (s.sound.drone ?? 0.5), at(t), 0.9);
    padG.gain.setTargetAtTime(0.03 * (s.sound.pad ?? 0.3), at(t), 1.2);
  }
  droneG.gain.setTargetAtTime(0.035, at(endT), 0.4);
  padG.gain.setTargetAtTime(0.012, at(endT), 0.4);

  // music box
  const musicBox = (t, f, vel = 1) => {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, at(t));
    g.gain.linearRampToValueAtTime(0.06 * vel, at(t) + 0.004);
    g.gain.setTargetAtTime(0, at(t) + 0.004, 0.42);
    g.connect(score); g.connect(verb); g.connect(delay);
    [[1, 1], [2, 0.28], [4.07, 0.1], [6.9, 0.04]].forEach(([m, a]) => {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f * m;
      const og = ctx.createGain(); og.gain.value = a;
      if (m > 3) { og.gain.setValueAtTime(a, at(t)); og.gain.setTargetAtTime(0, at(t), 0.08); }
      o.connect(og).connect(g); o.start(at(t)); o.stop(at(t) + 2.6);
    });
  };
  const step = 60 / 66 / 2; // eighth notes at 66 bpm
  for (let t = 0.6, i = 0; t < endT - 0.5; t += step, i++) {
    if (musicOff(t)) continue;
    const s = sceneAt(t);
    const dens = s.sound.box ?? 0.5;
    const bar = Math.floor(i / 16);
    let m = (bar % 3 === 2 ? MOTIF_B : MOTIF)[i % 16];
    const r = R();
    if (!m || r > 0.25 + dens * 0.75) continue;
    if (s.sound.chord === 'A' && m % 12 === 0) m += 1; // C -> C# over A
    const swing = (i % 2) * 0.03;
    musicBox(t + swing, midi(m), 0.6 + 0.4 * R());
  }

  // ticking clock: louder toward the cliffhanger, stops at the silence
  const nb = noiseBuffer(ctx, 0.05, 3);
  const firstTick = 1;
  for (let t = firstTick, i = 0; t < endT; t += 1, i++) {
    if (musicOff(t)) continue;
    const s = sceneAt(t);
    const prog = t / endT;
    const lvl = (s.sound.tick ?? 0.1) * (0.35 + 0.65 * prog);
    if (lvl < 0.01) continue;
    const src = ctx.createBufferSource(); src.buffer = nb;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = i % 2 ? 1900 : 2700; bp.Q.value = 9;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at(t)); g.gain.linearRampToValueAtTime(0.55 * lvl, at(t) + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, at(t) + 0.045);
    src.connect(bp).connect(g).connect(score);
    src.start(at(t)); src.stop(at(t) + 0.06);
  }

  // ---- bell (additive, inharmonic partials)
  const PARTIALS = [[0.5, 0.55, 1.0], [1, 0.9, 0.8], [1.19, 0.6, 0.55], [1.5, 0.32, 0.45], [2, 0.7, 0.42], [2.51, 0.26, 0.3], [2.66, 0.2, 0.26], [3.01, 0.2, 0.22], [4.17, 0.13, 0.15], [5.43, 0.09, 0.1]];
  const bell = (t, { f = 196, gain = 0.32, decay = 7, pan = -0.2, wrong = false, bus = score } = {}) => {
    const out = ctx.createGain(); out.gain.value = gain;
    const p = ctx.createStereoPanner(); p.pan.value = pan;
    out.connect(p); p.connect(bus); p.connect(verb);
    if (wrong) {
      // reversed swell into a detuned, sour strike
      const sw = ctx.createGain(); sw.gain.setValueAtTime(0.0001, at(t - 1.6)); sw.gain.exponentialRampToValueAtTime(0.5, at(t)); sw.gain.setValueAtTime(0, at(t) + 0.01);
      sw.connect(out);
      [0.5, 1, 1.19, 2].forEach((m) => { const o = ctx.createOscillator(); o.frequency.value = f * m * 1.03; o.connect(sw); o.start(at(t - 1.6)); o.stop(at(t) + 0.05); });
    }
    PARTIALS.forEach(([m, a, d], k) => {
      for (const det of [0, wrong ? 7.3 : 0.9]) {
        const o = ctx.createOscillator(); o.type = 'sine';
        o.frequency.value = f * m * (wrong ? 1 + (k % 3) * 0.031 : 1) + det;
        const g = ctx.createGain();
        g.gain.setValueAtTime(0, at(t));
        g.gain.linearRampToValueAtTime(a * 0.5, at(t) + 0.004);
        g.gain.setTargetAtTime(0, at(t) + 0.004, (decay * d) / 4.5);
        o.connect(g).connect(out); o.start(at(t)); o.stop(at(t) + decay * d * 1.3 + 0.1);
      }
    });
    // strike transient
    const n = ctx.createBufferSource(); n.buffer = noiseBuffer(ctx, 0.08, 17);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2200; bp.Q.value = 1.4;
    const ng = ctx.createGain(); ng.gain.setValueAtTime(0.35, at(t)); ng.gain.exponentialRampToValueAtTime(0.001, at(t) + 0.07);
    n.connect(bp).connect(ng).connect(out); n.start(at(t)); n.stop(at(t) + 0.09);
  };

  // ---- sfx helpers
  const noiseHit = (t, { len = 0.1, f = 2000, q = 1, g = 0.3, type = 'bandpass', bus = fxBus, brown = false, attack = 0.002 }) => {
    const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx, len + 0.05, Math.floor(t * 1000) + 7, brown);
    const flt = ctx.createBiquadFilter(); flt.type = type; flt.frequency.value = f; flt.Q.value = q;
    const gg = ctx.createGain(); gg.gain.setValueAtTime(0.0001, at(t)); gg.gain.linearRampToValueAtTime(g, at(t) + attack);
    gg.gain.exponentialRampToValueAtTime(0.0001, at(t) + len);
    s.connect(flt).connect(gg).connect(bus); s.start(at(t)); s.stop(at(t) + len + 0.05);
    return { flt, gg };
  };
  const creak = (t, { f = 140, len = 0.7, g = 0.12 } = {}) => {
    const o = ctx.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(f, at(t));
    for (let k = 1; k <= 8; k++) o.frequency.linearRampToValueAtTime(f * (0.8 + 0.5 * R()), at(t) + (len * k) / 8);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 900; bp.Q.value = 6;
    const gg = ctx.createGain(); gg.gain.setValueAtTime(0, at(t)); gg.gain.linearRampToValueAtTime(g, at(t) + 0.08);
    gg.gain.setValueAtTime(g, at(t) + len * 0.7); gg.gain.linearRampToValueAtTime(0, at(t) + len);
    o.connect(bp).connect(gg).connect(fxBus); o.start(at(t)); o.stop(at(t) + len + 0.05);
  };
  const rewind = (t) => {
    const o = ctx.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(2400, at(t - 0.5)); o.frequency.exponentialRampToValueAtTime(60, at(t));
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, at(t - 0.5)); g.gain.exponentialRampToValueAtTime(0.07, at(t - 0.1)); g.gain.linearRampToValueAtTime(0, at(t) + 0.02);
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1200; bp.Q.value = 0.8;
    o.connect(bp).connect(g).connect(fxBus); o.start(at(t - 0.5)); o.stop(at(t) + 0.05);
    const n = noiseHit(t - 0.5, { len: 0.55, f: 4000, q: 0.6, g: 0.12, attack: 0.4 });
    n.flt.frequency.setValueAtTime(6000, at(t - 0.5)); n.flt.frequency.exponentialRampToValueAtTime(300, at(t));
    noiseHit(t, { len: 0.12, f: 120, q: 0.7, g: 0.4, type: 'lowpass', brown: true });
  };
  const boom = (t, g = 0.5) => {
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(70, at(t)); o.frequency.exponentialRampToValueAtTime(38, at(t) + 1.5);
    const gg = ctx.createGain(); gg.gain.setValueAtTime(0, at(t)); gg.gain.linearRampToValueAtTime(g, at(t) + 0.01); gg.gain.setTargetAtTime(0, at(t) + 0.02, 0.5);
    o.connect(gg).connect(score); o.start(at(t)); o.stop(at(t) + 3);
  };

  // ---- event-driven sounds
  const rainStart = tl.events.find((e) => e.type === 'rainStart');
  for (const e of tl.events) {
    const t = e.t;
    switch (e.type) {
      case 'titleSting': bell(t + 0.25, { f: 196, gain: 0.34, decay: 8 }); boom(t + 0.25, 0.35); break;
      case 'endSting':
        bell(t + 0.1, { f: 196, gain: 0.3, decay: 7 });
        [74, 77, 81, 86].forEach((m, k) => musicBox(t + 0.9 + k * 0.32, midi(m), 0.9));
        break;
      case 'bell': bell(t, { f: 196, gain: 0.26, decay: 6.5, pan: -0.3 + 0.2 * R() }); break;
      case 'bellWrong': bell(t, { f: 184, gain: 0.34, decay: 6, wrong: true, pan: 0.15 }); break;
      case 'reset':
        rewind(t);
        if (e.bell !== false) bell(t + 0.02, { f: 196, gain: 0.3, decay: 6 });
        break;
      case 'glitchFrame':
        noiseHit(t, { len: 0.09, f: 3000, q: 0.5, g: 0.35 });
        bell(t + 0.01, { f: 196, gain: 0.14, decay: 1.6, bus: fxBus });
        break;
      case 'clatter':
        for (let k = 0; k < 9; k++) noiseHit(t + R() * 0.55, { len: 0.05 + R() * 0.08, f: 1500 + R() * 3000, q: 3 + R() * 6, g: 0.2 + R() * 0.15 });
        noiseHit(t, { len: 0.18, f: 160, q: 0.8, g: 0.45, type: 'lowpass', brown: true });
        break;
      case 'creak': creak(t, { f: 150, len: 0.65, g: 0.12 }); break;
      case 'doorCreak': creak(t, { f: 85, len: 1.8, g: 0.09 }); break;
      case 'rumble': noiseHit(t, { len: 5, f: 140, q: 0.6, g: 0.25, type: 'lowpass', brown: true, attack: 1.2 }); break;
      case 'chime': [86, 89, 93].forEach((m, k) => musicBox(t + k * 0.12, midi(m), 0.5)); break;
      case 'sting': boom(t, 0.25); musicBox(t + 0.05, midi(93), 1); musicBox(t + 0.05, midi(98), 0.6); break;
      case 'hush': noiseHit(t, { len: 1.2, f: 600, q: 0.5, g: 0.06, attack: 0.5 }); break;
      case 'scratch': {
        const n = noiseHit(t, { len: 4.0, f: 3200, q: 2.5, g: 0.06, attack: 0.2 });
        const tr = ctx.createOscillator(); tr.frequency.value = 7; const trg = ctx.createGain(); trg.gain.value = 0.05;
        tr.connect(trg).connect(n.gg.gain); tr.start(at(t)); tr.stop(at(t) + 4);
        break;
      }
      default: break;
    }
  }
  // rain bed
  if (rainStart) {
    const sc = tl.scenes[rainStart.scene];
    const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx, 2, 77); s.loop = true;
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 900;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 7000;
    const g = ctx.createGain(); g.gain.setValueAtTime(0, at(rainStart.t)); g.gain.linearRampToValueAtTime(0.09, at(rainStart.t) + 0.4);
    g.gain.setValueAtTime(0.09, at(sc.end - 0.6)); g.gain.linearRampToValueAtTime(0, at(sc.end + 0.6));
    s.connect(hp).connect(lp).connect(g).connect(fxBus); s.start(at(rainStart.t)); s.stop(at(sc.end + 0.7));
  }

  // ---- voice
  for (const line of tl.voiceLines) {
    const buf = voices[line.file];
    if (!buf) continue;
    const s = ctx.createBufferSource(); s.buffer = buf;
    const g = ctx.createGain(); g.gain.value = line.whisper ? 1.35 : 1.0;
    s.connect(g); g.connect(voiceBus); g.connect(voiceVerb);
    s.start(at(line.start));
  }
  return { master };
}

export async function loadVoices(ctx, tl, base) {
  const out = {};
  await Promise.all(tl.voiceLines.map(async (l) => {
    const r = await fetch(`${base}/${l.file}`);
    out[l.file] = await ctx.decodeAudioData(await r.arrayBuffer());
  }));
  return out;
}

export async function renderOffline(tl, base, sampleRate = 48000) {
  const len = Math.ceil((tl.duration + 0.2) * sampleRate);
  const ctx = new OfflineAudioContext(2, len, sampleRate);
  const voices = await loadVoices(ctx, tl, base);
  buildMix(ctx, tl, voices, 0);
  return ctx.startRendering();
}

export function encodeWav(buf) {
  const ch = buf.numberOfChannels, n = buf.length, sr = buf.sampleRate;
  const out = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const w = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
  w(0, 'RIFF'); out.setUint32(4, 36 + n * ch * 2, true); w(8, 'WAVE'); w(12, 'fmt ');
  out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, ch, true);
  out.setUint32(24, sr, true); out.setUint32(28, sr * ch * 2, true); out.setUint16(32, ch * 2, true); out.setUint16(34, 16, true);
  w(36, 'data'); out.setUint32(40, n * ch * 2, true);
  const data = [...Array(ch)].map((_, c) => buf.getChannelData(c));
  let o = 44;
  for (let i = 0; i < n; i++) for (let c = 0; c < ch; c++) {
    const v = Math.max(-1, Math.min(1, data[c][i]));
    out.setInt16(o, v < 0 ? v * 0x8000 : v * 0x7fff, true); o += 2;
  }
  return new Uint8Array(out.buffer);
}
