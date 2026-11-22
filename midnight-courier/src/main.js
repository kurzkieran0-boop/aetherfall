// Entry point. In a normal browser this is a live preview player (with the
// Web Audio score + voice). Under Playwright (navigator.webdriver) it only
// exposes window.MC for deterministic frame / audio capture.
import { Engine } from './core/engine.js';
import { renderScore, bufferToWavBase64, playLive } from './core/audio.js';

async function boot() {
  await Promise.all([document.fonts.load('100px "Lilita One"'), document.fonts.load('60px "Caveat"')]);
  const q = new URLSearchParams(location.search);
  const tl = await (await fetch(q.get('timeline') || 'data/timeline.json')).json();
  const eng = new Engine(tl);
  window.MC = {
    tl,
    eng,
    warm(t0, t1) { eng.warm(t0, t1); return true; },
    async jpeg(t, quality = 0.93) {
      const c = eng.render(t);
      const blob = await new Promise((res) => c.toBlob(res, 'image/jpeg', quality));
      const buf = new Uint8Array(await blob.arrayBuffer());
      let s = '';
      for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
      return btoa(s);
    },
    async png(t) {
      const c = eng.render(t);
      return c.toDataURL('image/png').split(',')[1];
    },
    async audio() {
      const buf = await renderScore(tl, 48000);
      return bufferToWavBase64(buf);
    },
  };
  window.MC_READY = true;
  if (!navigator.webdriver) preview(eng, tl);
}

function preview(eng, tl) {
  const view = document.getElementById('view');
  view.width = 1080; view.height = 1920;
  const vctx = view.getContext('2d');
  const info = document.getElementById('info');
  let playing = false, t0 = 0, offset = 0, actx = null;
  const voices = [];
  const draw = (t) => {
    vctx.drawImage(eng.render(t), 0, 0);
    const s = eng.shotAt(t);
    info.textContent = `${t.toFixed(2)}s / ${tl.duration.toFixed(1)}s · ${s.id} · ${s.scene} · ${s.palette}`;
  };
  const tick = () => {
    if (!playing) return;
    const t = offset + (performance.now() - t0) / 1000;
    if (t >= tl.duration) { playing = false; stopAudio(); return; }
    draw(t);
    requestAnimationFrame(tick);
  };
  const stopAudio = () => { if (actx) actx.close(); actx = null; };
  async function startAudio(from) {
    actx = playLive(tl, from);
    for (const l of tl.lines) {
      if (!voices[l.idx]) {
        try { voices[l.idx] = await actx.decodeAudioData(await (await fetch(`data/voice/${l.file}`)).arrayBuffer()); } catch { voices[l.idx] = null; }
      }
      const b = voices[l.idx];
      if (!b || l.start < from) continue;
      const src = actx.createBufferSource();
      src.buffer = b;
      const g = actx.createGain(); g.gain.value = l.gain ?? 1;
      src.connect(g).connect(actx.destination);
      src.start(actx.currentTime + 0.1 + (l.start - from));
    }
  }
  document.getElementById('play').onclick = async () => {
    if (playing) { playing = false; offset += (performance.now() - t0) / 1000; stopAudio(); return; }
    playing = true; t0 = performance.now(); await startAudio(offset); t0 = performance.now(); tick();
  };
  const scrub = document.getElementById('scrub');
  scrub.max = tl.duration;
  scrub.oninput = () => { offset = +scrub.value; if (!playing) draw(offset); };
  draw(0);
}

boot();
