// Procedural score, rendered deterministically with an OfflineAudioContext, mixed with the voice lines.
//  - deep sub-bass pressure drone (+ brown-noise rumble), per-scene level / detune
//  - sonar pings from the shared ping schedule (faster toward the cliffhanger), sonar echo + reverb
//  - faint radio static with crackle
//  - heartbeat in the cliffhanger (shared schedule with the ECG)
//  - sound design per scene: spike thump, countdown ticks, bearing chirps, glitch bursts, log ticks, single tone
//  - score ducked 10 dB under every voice sentence; fully silent in the silence window before the final line
import { pings, heartbeats, silenceWindows, countdown, findWord, sentenceStart } from './schedule.js';
import { rng } from './draw.js';

const SR = 48000;
const DUCK = Math.pow(10, -10 / 20); // -10 dB

function noiseBuffer(ctx, sec, seed, kind = 'white') {
  const n = Math.floor(sec * SR), b = ctx.createBuffer(1, n, SR), d = b.getChannelData(0), R = rng(seed);
  let last = 0;
  for (let i = 0; i < n; i++) {
    const w = R() * 2 - 1;
    if (kind === 'brown') { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; }
    else if (kind === 'crackle') { d[i] = w * 0.35 + (R() < 0.0009 ? (R() * 2 - 1) * 4 : 0); }
    else d[i] = w;
  }
  return b;
}
function impulse(ctx, sec, seed) {
  const n = Math.floor(sec * SR), b = ctx.createBuffer(2, n, SR), R = rng(seed);
  for (let c = 0; c < 2; c++) { const d = b.getChannelData(c); for (let i = 0; i < n; i++) d[i] = (R() * 2 - 1) * Math.pow(1 - i / n, 3.2); }
  return b;
}
function env(g, t, a, peak, decay, hold = 0) {
  g.gain.setValueAtTime(0.0001, Math.max(0, t));
  g.gain.linearRampToValueAtTime(peak, t + a);
  if (hold) g.gain.setValueAtTime(peak, t + a + hold);
  g.gain.exponentialRampToValueAtTime(0.0001, t + a + hold + decay);
}

export async function renderMix(tl, series, base = '') {
  const dur = tl.total + 0.5;
  const ctx = new OfflineAudioContext(2, Math.ceil(dur * SR), SR);
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -12; comp.ratio.value = 3; comp.attack.value = 0.005; comp.release.value = 0.25;
  const master = ctx.createGain(); master.gain.value = 0.9;
  comp.connect(master).connect(ctx.destination);
  const score = ctx.createGain(); score.connect(comp);
  const voiceBus = ctx.createGain(); voiceBus.gain.value = 1.0; voiceBus.connect(comp);

  const rev = ctx.createConvolver(); rev.buffer = impulse(ctx, 3.6, 11);
  const revGain = ctx.createGain(); revGain.gain.value = 0.35; rev.connect(revGain).connect(score);

  const sil = silenceWindows(tl);
  const S = tl.scenes;

  // ------------------------------------------------ drone
  const droneGain = ctx.createGain(); droneGain.gain.value = 0;
  const droneLP = ctx.createBiquadFilter(); droneLP.type = 'lowpass'; droneLP.frequency.value = 180;
  const lfoStage = ctx.createGain(); lfoStage.gain.value = 1; // multiplicative LFO so silence stays silent
  droneLP.connect(lfoStage).connect(droneGain).connect(score);
  const oscs = [[36.7, 'sine', 0.55], [55.0, 'sine', 0.32], [73.4, 'triangle', 0.08], [36.9, 'sine', 0.3]].map(([f, type, g]) => {
    const o = ctx.createOscillator(); o.type = type; o.frequency.value = f;
    const gg = ctx.createGain(); gg.gain.value = g; o.connect(gg).connect(droneLP); o.start(0); o.stop(dur); return o;
  });
  const rumble = ctx.createBufferSource(); rumble.buffer = noiseBuffer(ctx, 8, 3, 'brown'); rumble.loop = true;
  const rLP = ctx.createBiquadFilter(); rLP.type = 'lowpass'; rLP.frequency.value = 110;
  const rG = ctx.createGain(); rG.gain.value = 0.5; rumble.connect(rLP).connect(rG).connect(droneLP); rumble.start(0); rumble.stop(dur);
  const lfo = ctx.createOscillator(); lfo.frequency.value = 0.07; const lfoG = ctx.createGain(); lfoG.gain.value = 0.15;
  lfo.connect(lfoG).connect(lfoStage.gain); lfo.start(0); lfo.stop(dur);

  // ------------------------------------------------ static
  const stat = ctx.createBufferSource(); stat.buffer = noiseBuffer(ctx, 6, 5, 'crackle'); stat.loop = true;
  const sBP = ctx.createBiquadFilter(); sBP.type = 'bandpass'; sBP.frequency.value = 3200; sBP.Q.value = 0.5;
  const statG = ctx.createGain(); statG.gain.value = 0;
  stat.connect(sBP).connect(statG).connect(score); stat.start(0); stat.stop(dur);

  // ------------------------------------------------ single tone (scene with sound.tone)
  const tone = ctx.createOscillator(); tone.frequency.value = 440; const toneG = ctx.createGain(); toneG.gain.value = 0;
  tone.connect(toneG).connect(score); toneG.connect(rev); tone.start(0); tone.stop(dur);

  // per-scene levels
  const segStart = (i) => (i === 0 ? 0 : S[i].start - 0.4);
  S.forEach((sc, i) => {
    const s = sc.sound || {}, t = segStart(i);
    droneGain.gain.setTargetAtTime(0.42 * (s.drone ?? 0.6), t, i === 0 ? 1.6 : 0.7);
    statG.gain.setTargetAtTime(0.045 * (s.static ?? 0.3), t, 0.5);
    toneG.gain.setTargetAtTime(0.05 * (s.tone || 0), t, 0.8);
    oscs.forEach((o) => o.detune.setTargetAtTime(s.detune || 0, t, 1.2));
  });
  // title card + end card keep the bed going
  droneGain.gain.setTargetAtTime(0.3, tl.titleCard.start, 0.4);
  droneGain.gain.setTargetAtTime(0.42 * (S[1].sound?.drone ?? 0.6), S[1].start - 0.4, 0.7);
  // silence: hard off; end card: low bed returns
  for (const w of sil) {
    for (const g of [droneGain.gain, statG.gain, toneG.gain]) { g.cancelScheduledValues(w.a - 0.25); g.setTargetAtTime(0, w.a - 0.25, 0.06); }
  }
  droneGain.gain.setTargetAtTime(0.22, tl.endCard.start + 0.3, 0.5);
  statG.gain.setTargetAtTime(0.008, tl.endCard.start + 0.3, 0.5);

  // ------------------------------------------------ sonar pings (+ echo)
  const pingBus = ctx.createGain(); pingBus.gain.value = 1;
  const dly = ctx.createDelay(1.0); dly.delayTime.value = 0.42; const fb = ctx.createGain(); fb.gain.value = 0.32;
  const dLP = ctx.createBiquadFilter(); dLP.type = 'lowpass'; dLP.frequency.value = 2200;
  pingBus.connect(score); pingBus.connect(rev); pingBus.connect(dly); dly.connect(dLP).connect(fb).connect(dly); dLP.connect(score);
  function ping(t, magenta, strong) {
    const parts = magenta ? [[660, 0.22], [987, 0.1], [662.5, 0.12]] : [[1318, 0.16], [2636, 0.025]];
    for (const [f, g] of parts) {
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * 0.985, t + 2);
      const gg = ctx.createGain(); env(gg, t, 0.004, g * (strong ? 1.5 : 1), magenta ? 3.8 : 2.2);
      o.connect(gg).connect(pingBus); o.start(t); o.stop(t + 4.5);
    }
  }
  for (const p of pings(tl)) ping(p.t, p.color === 'magenta', p.strong);

  // ------------------------------------------------ thumps / heartbeat
  function thump(t, f0, f1, peak, decay, out = score) {
    const o = ctx.createOscillator(); o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + 0.14);
    const g = ctx.createGain(); env(g, t, 0.006, peak, decay);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 160;
    o.connect(lp).connect(g).connect(out); o.start(t); o.stop(t + decay + 0.2);
  }
  for (const b of heartbeats(tl)) { thump(b.t, 70, 42, 0.75, 0.2); thump(b.t + 0.27, 62, 40, 0.5, 0.22); }

  const burstBuf = noiseBuffer(ctx, 1, 21);
  function burst(t, len, f, q, peak, out = score) {
    const s = ctx.createBufferSource(); s.buffer = burstBuf;
    const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = q;
    const g = ctx.createGain(); env(g, t, 0.002, peak, len);
    s.connect(bp).connect(g).connect(out); s.start(t, rng(Math.floor(t * 100))() * 0.5); s.stop(t + len + 0.1);
  }
  function blip(t, f, len, peak, type = 'square') {
    const o = ctx.createOscillator(); o.type = type; o.frequency.value = f;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3000;
    const g = ctx.createGain(); env(g, t, 0.002, peak, len);
    o.connect(lp).connect(g).connect(score); o.start(t); o.stop(t + len + 0.05);
  }
  // template stings: title + end card
  function sting(t) { thump(t, 70, series.template.sting.sub, 0.42, 2.6); ping(t + 0.02, false, true); burst(t - 0.6, 0.6, 1800, 0.4, 0.05); }
  sting(tl.titleCard.start + 0.15);
  sting(tl.endCard.start + 0.45);

  for (const sc of S) {
    const v = sc.visual, T0 = sc.start;
    if (v.type === 'spectrum') { const w = findWord(sc, v.spikeWord); if (w) { const t = T0 + w.t0 + 0.12; thump(t, 90, 38, 0.8, 0.8); burst(t, 0.25, 2400, 0.6, 0.18); } }
    if (v.type === 'countdown') for (const e of countdown(sc)) blip(T0 + e.t, 1760, 0.035, 0.05);
    if (v.type === 'triangulation') for (let i = 0; i < 3; i++) { const t = T0 + sentenceStart(sc, 1) + i * 0.5; const o = ctx.createOscillator(); o.frequency.setValueAtTime(900, t); o.frequency.exponentialRampToValueAtTime(2400, t + 0.18); const g = ctx.createGain(); env(g, t, 0.004, 0.05, 0.2); o.connect(g).connect(score); o.start(t); o.stop(t + 0.5); }
    if (v.type === 'glitchWords') { const R = rng(9); for (let i = 0; i < 12; i++) burst(T0 + 0.4 + R() * 3.2, 0.04 + R() * 0.1, 800 + R() * 3000, 2, 0.12); }
    if (v.type === 'terminalLog') { const R = rng(4); const stop = T0 + sentenceStart(sc, v.highlightSentence) - 0.05; for (let t = T0 + 0.2; t < stop; t += 0.06 + R() * 0.1) burst(t, 0.012, 4000, 3, 0.05 + R() * 0.04); blip(stop, 880, 0.18, 0.06, 'sine'); }
    if (v.type === 'cliffhanger') { const w = findWord(sc, v.clockWord); if (w) blip(T0 + w.t0 + 0.05, 1975, 0.5, 0.06, 'sine'); }
  }

  // ------------------------------------------------ ducking (-10 dB under voice) + full silence
  const spans = [];
  for (const sc of S) for (const s of sc.voice.sentences) spans.push([sc.start + s.start - 0.12, sc.start + s.start + s.duration + 0.12]);
  spans.sort((a, b) => a[0] - b[0]);
  const merged = [];
  for (const sp of spans) { const m = merged[merged.length - 1]; if (m && sp[0] - m[1] < 0.5) m[1] = Math.max(m[1], sp[1]); else merged.push([...sp]); }
  // one sampled gain curve = duck(t) * silence(t), 200 Hz
  const RATE = 200, N = Math.ceil(dur * RATE), curve = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    const t = i / RATE;
    let d = 1;
    for (const [a, b] of merged) {
      if (t >= a - 0.15 && t < a) d = Math.min(d, 1 - (1 - DUCK) * ((t - (a - 0.15)) / 0.15));
      else if (t >= a && t <= b) d = DUCK;
      else if (t > b && t < b + 0.35) d = Math.min(d, DUCK + (1 - DUCK) * ((t - b) / 0.35));
    }
    let m = 1;
    for (const w of sil) { if (t >= w.a - 0.1 && t < w.a) m = Math.min(m, (w.a - t) / 0.1); else if (t >= w.a && t < w.b) m = 0; }
    curve[i] = d * m;
  }
  score.gain.setValueCurveAtTime(curve, 0, N / RATE);

  // ------------------------------------------------ voice lines
  const meta = { voice: [] };
  for (const sc of S) {
    const res = await fetch(`${base}/episodes/${tl.__ep}/${sc.voice.file}`);
    const buf = await ctx.decodeAudioData(await res.arrayBuffer());
    const src = ctx.createBufferSource(); src.buffer = buf; src.connect(voiceBus); src.start(sc.start + sc.voice.offset);
    meta.voice.push({ id: sc.id, t: sc.start + sc.voice.offset, d: buf.duration });
  }
  const out = await ctx.startRendering();
  return { buffer: out, meta, duckSpans: merged, silence: sil };
}

export function toWav(buffer) {
  const n = buffer.length, ch = buffer.numberOfChannels, bytes = new ArrayBuffer(44 + n * ch * 2), v = new DataView(bytes);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, 'RIFF'); v.setUint32(4, 36 + n * ch * 2, true); w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
  v.setUint16(22, ch, true); v.setUint32(24, buffer.sampleRate, true); v.setUint32(28, buffer.sampleRate * ch * 2, true); v.setUint16(32, ch * 2, true); v.setUint16(34, 16, true);
  w(36, 'data'); v.setUint32(40, n * ch * 2, true);
  const chans = Array.from({ length: ch }, (_, c) => buffer.getChannelData(c));
  let o = 44;
  for (let i = 0; i < n; i++) for (let c = 0; c < ch; c++) { const s = Math.max(-1, Math.min(1, chans[c][i])); v.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true); o += 2; }
  return new Uint8Array(bytes);
}
