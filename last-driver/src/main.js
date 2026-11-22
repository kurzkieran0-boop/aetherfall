// Entry point: exposes window.MC for deterministic frame/audio capture;
// in a normal browser it is a live preview player.
import { Engine3D } from './core/engine3d.js';
import { renderScore, bufferToWavBase64, playLive } from './core/audio.js';

async function boot() {
  await Promise.all([document.fonts.load('100px Anton')]);
  const q = new URLSearchParams(location.search);
  const tl = await (await fetch(q.get('timeline') || 'data/timeline.json')).json();
  const eng = new Engine3D(tl);
  window.MC = {
    tl, eng,
    warm() { return true; },
    async jpeg(t, quality = 0.93) {
      const c = eng.render(t);
      const blob = await new Promise((res) => c.toBlob(res, 'image/jpeg', quality));
      const buf = new Uint8Array(await blob.arrayBuffer());
      let s = '';
      for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
      return btoa(s);
    },
    async audio() { return bufferToWavBase64(await renderScore(tl, 48000)); },
  };
  window.MC_READY = true;
  if (!navigator.webdriver) preview(eng, tl);
}

function preview(eng, tl) {
  const view = document.getElementById('view');
  view.replaceWith(eng.canvas);
  eng.canvas.id = 'view';
  const info = document.getElementById('info');
  let playing = false, t0 = 0, offset = 0, actx = null;
  const draw = (t) => { eng.render(t); const s = eng.shotAt(t); info.textContent = `${t.toFixed(2)}s · ${s.id} · ${s.scene}`; };
  const tick = () => { if (!playing) return; const t = offset + (performance.now() - t0) / 1000; if (t >= tl.duration) { playing = false; return; } draw(t); requestAnimationFrame(tick); };
  document.getElementById('play').onclick = async () => {
    if (playing) { playing = false; offset += (performance.now() - t0) / 1000; if (actx) actx.close(); return; }
    actx = playLive(tl, offset);
    for (const l of tl.lines) {
      if (l.start < offset) continue;
      try {
        const b = await actx.decodeAudioData(await (await fetch(`data/voice/${l.file}`)).arrayBuffer());
        const src = actx.createBufferSource(); src.buffer = b; src.connect(actx.destination); src.start(actx.currentTime + 0.1 + l.start - offset);
      } catch {}
    }
    playing = true; t0 = performance.now(); tick();
  };
  const scrub = document.getElementById('scrub');
  scrub.max = tl.duration;
  scrub.oninput = () => { offset = +scrub.value; if (!playing) draw(offset); };
  draw(0);
}
boot();
