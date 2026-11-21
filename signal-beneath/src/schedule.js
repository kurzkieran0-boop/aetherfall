// Time schedules shared by the picture and the procedural score so that pings, heartbeats,
// countdown ticks and silences line up exactly in both.
const norm = (w) => w.toLowerCase().replace(/[^a-z0-9-]/g, '');

export function findWord(scene, word, after = 0) {
  const target = norm(word);
  for (const s of scene.voice.sentences) for (const w of s.words) if (w.t0 >= after - 1e-6 && norm(w.w) === target) return w;
  return null;
}
export const sentenceStart = (scene, i) => scene.voice.sentences[Math.min(i, scene.voice.sentences.length - 1)].start;
export const sentenceEnd = (scene, i) => { const s = scene.voice.sentences[Math.min(i, scene.voice.sentences.length - 1)]; return s.start + s.duration; };

// absolute windows of total silence (score + voice) before a "final" line
export function silenceWindows(tl) {
  const out = [];
  for (const sc of tl.scenes) for (const s of sc.voice.sentences) if (s.silenceBefore > 0) out.push({ a: sc.start + s.start - s.silenceBefore, b: sc.start + s.start, scene: sc.id, final: s.final });
  return out;
}
export function finalLine(tl) {
  for (const sc of tl.scenes) for (const s of sc.voice.sentences) if (s.final) return { t: sc.start + s.start, end: sc.start + s.start + s.duration, scene: sc };
  return null;
}

// sonar pings: interval per scene (gets faster toward the cliffhanger), none inside silence
export function pings(tl) {
  const out = [];
  const sil = silenceWindows(tl);
  for (const sc of tl.scenes) {
    const every = sc.sound?.pingEvery || 0;
    if (sc.visual.type === 'coldOpen') out.push({ t: sc.start + 0.35, color: 'cyan', strong: true });
    if (!every) continue;
    const firstSil = sil.find((w) => w.a >= sc.start && w.a < sc.start + sc.duration);
    const end = firstSil ? firstSil.a - 0.2 : sc.start + sc.duration;
    for (let t = sc.start + (sc.visual.type === 'coldOpen' ? 0.35 + every : 0.5); t < end; t += every) out.push({ t, color: 'cyan' });
  }
  const fl = finalLine(tl);
  if (fl) out.push({ t: fl.t, color: 'magenta', strong: true });
  return out.sort((a, b) => a.t - b.t);
}

// heartbeat in scenes with sound.heartbeat, from scene start until the silence
export function heartbeats(tl) {
  const out = [];
  const sil = silenceWindows(tl);
  for (const sc of tl.scenes) {
    if (!sc.sound?.heartbeat) continue;
    const w = sil.find((x) => x.a >= sc.start && x.a < sc.start + sc.duration);
    const end = w ? w.a - 0.15 : sc.start + sc.duration;
    let t = sc.start + 0.4, k = 0;
    while (t < end - 0.3) { out.push({ t, k }); const f = (t - sc.start) / (end - sc.start); t += 1.0 - 0.22 * f; k++; }
  }
  return out;
}

// countdown events {t (scene-local), n} from word marks
export function countdown(scene) {
  const ev = [];
  let after = 0;
  for (const m of scene.visual.marks || []) {
    if (m.word) { const w = findWord(scene, m.word, after); if (w) { ev.push({ t: w.t0 + 0.05, n: m.n }); after = w.t0; } }
    else if (m.rushFrom) {
      const a = findWord(scene, m.rushFrom, after), b = findWord(scene, m.rushTo, after);
      if (!a || !b) continue;
      const t0 = a.t0, t1 = b.t0 + 0.05, N = m.from - m.to;
      for (let i = 0; i <= N; i++) { const u = i / N; ev.push({ t: t0 + (t1 - t0) * (1 - Math.pow(1 - u, 1.7)), n: m.from - i }); }
      after = b.t0;
    }
  }
  return ev.sort((a, b) => a.t - b.t);
}

// jellyfish clock: slows to a stop in scenes with freezeJellyfish (integrated speed)
export function makeJellyClock(tl, dt = 0.05) {
  const total = tl.total, n = Math.ceil(total / dt) + 2, tab = new Float32Array(n);
  const speed = (t) => {
    for (const sc of tl.scenes) if (sc.freezeJellyfish && t >= sc.start) {
      return Math.max(0, 1 - (t - sc.start) / 1.6); // first freezing scene: ease to a halt
    }
    return 1;
  };
  for (let i = 1; i < n; i++) { const t = i * dt; tab[i] = tab[i - 1] + speed(t - dt / 2) * dt; }
  return (t) => { const i = Math.max(0, Math.min(n - 2, Math.floor(t / dt))), f = t / dt - i; return tab[i] + (tab[i + 1] - tab[i]) * f; };
}
