// Series engine: loads an episode timeline.json and renders it deterministically.
//   preview:  http://localhost:5173/?ep=part1            (click to play with audio)
//   export:   ?ep=part1&w=1080&h=1920&export=1           (driven frame-by-frame by Playwright)
import * as THREE from 'three';
import '@fontsource/im-fell-english/400.css';
import '@fontsource/im-fell-english/400-italic.css';
import '@fontsource/im-fell-english-sc/400.css';
import '@fontsource/homemade-apple/400.css';
import './style.css';
import { buildWorld } from './world.js';
import { createActor, applyAction } from './characters.js';
import { Post } from './post.js';
import { Overlay } from './overlay.js';
import { shared } from './materials.js';
import { renderOffline, encodeWav, loadVoices, buildMix } from './audio.js';

const q = new URLSearchParams(location.search);
const EP = q.get('ep') || 'part1';
const BASE = `${import.meta.env.BASE_URL}episodes/${EP}`;
const EXPORT = q.has('export');
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
const LOCO = new Set(['walk', 'walkJoke', 'roll', 'loom']);

async function main() {
  const tl = await (await fetch(`${BASE}/timeline.json`)).json();
  const aspect = q.get('aspect') || '9:16';
  const [ax, ay] = aspect.split(':').map(Number);
  let W = +q.get('w'), H = +q.get('h');
  if (!W || !H) { // preview: fit window, modest internal resolution
    const s = Math.min(innerWidth / ax, innerHeight / ay);
    W = Math.round(ax * s); H = Math.round(ay * s);
  }
  const stage = document.getElementById('stage');
  stage.style.width = `${W}px`; stage.style.height = `${H}px`;
  stage.style.setProperty('--u', `${Math.min(W, H) / 100}px`);
  stage.classList.toggle('portrait', H > W);

  await Promise.all([
    document.fonts.load(`italic 40px "${tl.series.fonts.caption}"`),
    document.fonts.load(`40px "${tl.series.fonts.caption}"`),
    document.fonts.load(`40px "${tl.series.fonts.title}"`),
    document.fonts.load(`40px "${tl.series.fonts.hand}"`),
  ]);
  await document.fonts.ready;

  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1);
  renderer.setSize(W, H);
  stage.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0xc08a63, 0.02);
  const camera = new THREE.PerspectiveCamera(45, W / H, 0.05, 900);
  const world = buildWorld(scene);
  const hemi = new THREE.HemisphereLight(0xffffff, 0x333333, 1);
  const sun = new THREE.DirectionalLight(0xffffff, 2);
  const fill = new THREE.DirectionalLight(0xffffff, 0.4);
  scene.add(hemi, sun, sun.target, fill, fill.target);
  const sunDir = world.skyU.sunDir.value;

  const actors = {};
  for (const name of Object.keys(tl.actors)) {
    const a = createActor(name, world);
    if (a.root) scene.add(a.root);
    actors[name] = a;
  }

  const post = new Post(renderer, W, H, { scale: +(q.get('rs') || 0.75), samples: +(q.get('msaa') || 0) });
  const overlay = new Overlay(document.getElementById('overlay'), tl);

  const resets = tl.events.filter((e) => e.type === 'reset');
  const evOf = (type) => tl.events.filter((e) => e.type === type);
  const sceneAt = (t) => { let s = tl.scenes[0]; for (const x of tl.scenes) if (x.start <= t + 1e-6) s = x; return s; };
  const lastReset = (t) => { let r = -1e9; for (const e of resets) if (e.t <= t) r = e.t; return r; };

  // ---------------------------------------------------------------- palette
  const cA = new THREE.Color(), cB = new THREE.Color();
  function lerpPal(a, b, k) {
    const out = {};
    for (const key of Object.keys(b)) {
      const va = a[key] ?? b[key], vb = b[key];
      if (typeof vb === 'number') out[key] = va + (vb - va) * k;
      else if (typeof vb === 'string' && vb.startsWith('#')) out[key] = '#' + cA.set(va).lerp(cB.set(vb), k).getHexString();
      else out[key] = vb;
    }
    return out;
  }
  function paletteAt(t) {
    const K = tl.paletteKeys;
    if (t <= K[0].t) return K[0].palette;
    for (let i = 0; i < K.length - 1; i++) {
      if (t >= K[i].t && t < K[i + 1].t) {
        if (K[i + 1].cut) return K[i].palette;
        return lerpPal(K[i].palette, K[i + 1].palette, smooth(K[i].t, K[i + 1].t, t));
      }
    }
    return K[K.length - 1].palette;
  }

  // ---------------------------------------------------------------- camera spline (one continuous camera)
  const v3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);
  const K = tl.cameraKeys.map((k) => ({ ...k, P: v3(k.pos), L: v3(k.look) }));
  function hermite(i, t, field) {
    const k0 = K[i], k1 = K[i + 1];
    const dt = k1.t - k0.t, s = (t - k0.t) / dt;
    const prev = !k0.cut && i > 0 ? K[i - 1] : null;
    const next = K[i + 2] && !K[i + 2].cut ? K[i + 2] : null;
    const get = (k) => (field === 'fov' ? new THREE.Vector3(k.fov, 0, 0) : k[field]);
    const p0 = get(k0), p1 = get(k1);
    const m0 = prev ? get(k1).clone().sub(get(prev)).multiplyScalar(dt / (k1.t - prev.t)) : new THREE.Vector3();
    const m1 = next ? get(next).clone().sub(get(k0)).multiplyScalar(dt / (next.t - k0.t)) : new THREE.Vector3();
    // monotone (Fritsch-Carlson style) tangent limiting per component: no overshoot past keys
    const d = p1.clone().sub(p0);
    const dPrev = prev ? p0.clone().sub(get(prev)).multiplyScalar(dt / (k0.t - prev.t)) : null;
    const dNext = next ? get(next).clone().sub(p1).multiplyScalar(dt / (next.t - k1.t)) : null;
    for (const c of ['x', 'y', 'z']) {
      if (dPrev && d[c] * dPrev[c] <= 0) m0[c] = 0;
      else m0[c] = Math.sign(m0[c]) * Math.min(Math.abs(m0[c]), 3 * Math.abs(d[c]), dPrev ? 3 * Math.abs(dPrev[c]) : Infinity);
      if (dNext && d[c] * dNext[c] <= 0) m1[c] = 0;
      else m1[c] = Math.sign(m1[c]) * Math.min(Math.abs(m1[c]), 3 * Math.abs(d[c]), dNext ? 3 * Math.abs(dNext[c]) : Infinity);
    }
    const s2 = s * s, s3 = s2 * s;
    return p0.clone().multiplyScalar(2 * s3 - 3 * s2 + 1).add(m0.multiplyScalar(s3 - 2 * s2 + s))
      .add(p1.clone().multiplyScalar(-2 * s3 + 3 * s2)).add(m1.multiplyScalar(s3 - s2));
  }
  function cameraAt(t) {
    if (t <= K[0].t) return { P: K[0].P.clone(), L: K[0].L.clone(), fov: K[0].fov };
    const last = K[K.length - 1];
    if (t >= last.t) return { P: last.P.clone(), L: last.L.clone(), fov: last.fov };
    let i = 0;
    while (i < K.length - 2 && K[i + 1].t <= t) i++;
    if (K[i + 1].cut) return { P: K[i].P.clone(), L: K[i].L.clone(), fov: K[i].fov };
    return { P: hermite(i, t, 'P'), L: hermite(i, t, 'L'), fov: hermite(i, t, 'fov').x };
  }

  // ---------------------------------------------------------------- actors
  function updateActors(t) {
    for (const [name, A] of Object.entries(tl.actors)) {
      const actor = actors[name];
      const keys = A.keys;
      let i = -1;
      for (let k = 0; k < keys.length; k++) if (keys[k].t <= t) i = k;
      const key = keys[Math.max(0, i)];
      const inSpan = A.spans.some(([a, b]) => t >= a && t <= b);
      const visible = !!(inSpan || actor.alwaysVisible) && key.action !== 'hidden';
      if (actor.root) actor.root.visible = visible;
      if (!visible && !actor.alwaysVisible) continue;
      let pos = key.pos, rot = key.rot ?? 0;
      const nxt = keys[i + 1];
      if (i >= 0 && nxt && LOCO.has(key.action) && nxt.pos && key.pos) {
        const u = smooth(key.t, nxt.t, t) * 0.25 + clamp((t - key.t) / (nxt.t - key.t)) * 0.75;
        pos = key.pos.map((v, j) => v + (nxt.pos[j] - v) * u);
        rot = rot + ((nxt.rot ?? rot) - rot) * u;
      }
      if (actor.root && pos) { actor.root.position.set(pos[0], pos[1], pos[2]); actor.root.rotation.y = rot; }
      const lt = Math.max(0, t - key.t);
      let action = key.action;
      if (action === 'sitInBed') action = 'sitUpInBed';
      const ltA = key.action === 'sitInBed' ? 10 : lt;
      applyAction(actor, action, { t, lt: ltA, loopT: Math.max(0, t - Math.max(key.t, lastReset(t))), key, world });
    }
  }

  // ---------------------------------------------------------------- per-frame state
  const tmpV = new THREE.Vector3();
  function frame(t) {
    const fps = tl.fps;
    shared.uTime.value = t;
    const sc = sceneAt(t);
    const set = sc.set || {};
    const pal = paletteAt(t);
    const night = 1 - clamp(pal.sunIntensity / 1.6);

    // camera
    const cam = cameraAt(t);
    const drift = 1;
    cam.P.add(tmpV.set(Math.sin(t * 0.31) * 0.025, Math.sin(t * 0.47 + 1.3) * 0.018, Math.cos(t * 0.27) * 0.025).multiplyScalar(drift));
    cam.L.add(tmpV.set(Math.sin(t * 0.23 + 2) * 0.03, Math.sin(t * 0.41) * 0.02, 0).multiplyScalar(drift));
    for (const e of evOf('bellWrong')) if (t > e.t && t < e.t + 4) {
      const a = 0.025 * Math.exp(-(t - e.t) * 1.2);
      cam.P.add(tmpV.set(Math.sin(t * 61) * a, Math.sin(t * 47) * a, 0));
    }
    camera.position.copy(cam.P);
    camera.lookAt(cam.L);
    const asp = W / H;
    camera.fov = asp >= 1 ? cam.fov : (2 * Math.atan(Math.tan((cam.fov * Math.PI) / 360) / asp) * 180) / Math.PI;
    camera.aspect = asp;
    camera.updateProjectionMatrix();

    // lights + atmosphere
    hemi.color.set(pal.hemiSky); hemi.groundColor.set(pal.hemiGround); hemi.intensity = pal.hemiIntensity;
    sun.color.set(pal.sun); sun.intensity = pal.sunIntensity;
    sun.position.copy(sunDir).multiplyScalar(60); sun.target.position.set(0, 0, 0);
    fill.color.set(pal.highlightTint); fill.intensity = 0.35;
    fill.position.copy(camera.position); fill.target.position.copy(cam.L);
    let fogD = pal.fogDensity;
    for (const e of evOf('fogPulse')) fogD += 0.5 * Math.exp(-(((t - e.t) / 0.55) ** 2));
    scene.fog.color.set(pal.fog); scene.fog.density = fogD;
    world.skyU.top.value.set(pal.skyTop); world.skyU.horizon.value.set(pal.skyHorizon); world.skyU.fogC.value.set(pal.fog);
    world.skyU.sunColor.value.set(pal.sun); world.skyU.sunInt.value = pal.sunIntensity / 2;
    world.skyU.fogAmt.value = clamp(fogD * 18);
    world.sky.position.copy(camera.position);

    const p = camera.position;
    const inside = p.x > 11.1 && p.x < 20.9 && p.z > 4.1 && p.z < 11.9 && p.y < 4;
    const flick = 0.85 + 0.1 * Math.sin(t * 13.1) * Math.sin(t * 7.3) + 0.05 * Math.sin(t * 31);
    for (const l of Object.values(world.lights)) l.visible = inside;
    world.lights.kitchen.intensity = inside ? pal.interior * 9 : 0;
    world.lights.hearth.intensity = inside ? pal.interior * 7 * flick : 0;
    world.lights.bedroom.intensity = inside ? pal.interior * 3.5 * (1 - night * 0.85) : 0;
    const nearTower = p.z < -9 && Math.abs(p.x) < 9;
    world.towerLight.visible = nearTower;
    world.towerLight.intensity = (3.5 + 5 * (1 - clamp(pal.sunIntensity / 2.5))) * flick;
    world.towerLamp.material.color.setRGB(1, 0.76 * flick, 0.48 * flick);
    world.candle.visible = !!set.candle;
    world.lights.candle.intensity = inside && set.candle ? 7 * night * flick + 0.5 : 0;
    world.lights.candle.visible = inside && !!set.candle;
    world.fire.material.color.setRGB(1, 0.5 + 0.15 * flick, 0.2);
    world.shafts.forEach((s) => (s.material.opacity = inside ? 0.05 * (1 - night) * pal.rays : 0));
    world.windows.forEach((w) => (w.material.emissiveIntensity = 0.15 + night * 1.6));
    world.lanterns.forEach((l) => (l.material.emissiveIntensity = 0.2 + night * 2.4));
    world.decals.forEach((d) => (d.visible = !!set.chalk));
    world.motesU.uAmt.value = pal.rays * 0.9 * (1 - night * 0.6);
    world.motesU.uColor.value.set(pal.sun);
    world.millHub.rotation.z = set.millStopped ? world.millHub.rotation.z : t * 0.35;
    // creaking step
    let dip = 0;
    for (const e of evOf('creak')) if (t > e.t && t < e.t + 1) dip = 0.03 * Math.exp(-(t - e.t) * 4) * Math.abs(Math.sin((t - e.t) * 22));
    world.creakStep.position.y = 0.07 - dip;
    world.creakStep.rotation.z = dip * 1.5;
    // tower door ajar
    let open = 0;
    if (set.towerDoorAjar) for (const e of evOf('doorCreak')) if (t > e.t && e.scene === sc.index) open = smooth(e.t, e.t + 2.2, t) * 0.85;
    world.towerDoor.rotation.y = open;
    world.towerGlow.material.opacity = open * 0.16;
    // rain: frozen mid-air, then falling
    const rs = evOf('rainStart')[0];
    if (rs) {
      const rsc = tl.scenes[rs.scene];
      const a = smooth(rs.t - 2.6, rs.t - 1.8, t) * (1 - smooth(rsc.end - 0.2, rsc.end + 0.8, t));
      world.rain.visible = a > 0.001;
      world.rainU.uAlpha.value = a * 0.55;
      world.rainU.uFall.value = Math.max(0, t - rs.t);
      world.rainU.uLen.value = t < rs.t ? 0.035 : 0.035 + 0.3 * clamp((t - rs.t) / 0.25);
    }
    // shadow falling across Wren
    shared.uSweepDark.value = 0;
    if (sc.shadowSweep && actors.wren) {
      const dir = shared.uSweepDir.value.set(0.25, -0.45, 1).normalize();
      const base = actors.wren.root.position.dot(dir) + 0.45 * dir.y;
      const { from, to } = sc.shadowSweep;
      shared.uSweep.value = base - 0.75 + 1.05 * smooth(from, to, t);
      shared.uSweepDark.value = 0.72 * smooth(from - 0.2, from + 0.5, t);
    }

    updateActors(t);

    // post FX state
    let glitch = 0, rewind = 0, flash = 0, fade = 0;
    for (const e of resets) {
      if (t > e.t - 0.6 && t < e.t + 0.45) {
        const pre = t < e.t ? smooth(e.t - 0.55, e.t, t) : 0;
        const postg = t >= e.t ? 1 - smooth(e.t, e.t + 0.42, t) : 0;
        glitch = Math.max(glitch, pre * 0.85, postg);
        rewind = Math.max(rewind, pre);
        flash = Math.max(flash, 0.55 * Math.exp(-(((t - e.t - 0.03) / 0.05) ** 2)));
      }
    }
    for (const e of evOf('fadeIn')) fade = Math.max(fade, 1 - smooth(e.t, e.t + 2.0, t));
    for (const e of evOf('blackout')) if (t >= e.t) fade = Math.max(fade, smooth(e.t, e.t + 0.4, t));
    for (const e of evOf('glitchFrame')) if (t >= e.t && t < e.t + 2.5 / fps) { glitch = 1; fade = 0.15; flash = 0.12; }
    const fr = Math.round(t * fps);
    const u = post.compMat.uniforms;
    u.time.value = t; u.frame.value = fr % 1000;
    u.exposure.value = pal.exposure; u.raysColor.value.set(pal.sun); u.raysAmt.value = pal.rays;
    u.shadowTint.value.set(pal.shadowTint); u.highlightTint.value.set(pal.highlightTint);
    u.glitch.value = glitch; u.rewind.value = rewind; u.flash.value = flash; u.fade.value = fade;
    u.seed.value = Math.floor(t * 12) * 1.37 % 97;
    u.ca.value = 0.0018;

    post.render(scene, camera, camera.position.clone().add(sunDir.clone().multiplyScalar(400)));
    overlay.update(t, {
      w: W, h: H, glitch,
      project: (a) => { const v = new THREE.Vector3(a[0], a[1], a[2]).project(camera); return { x: (v.x + 1) / 2 * W, y: (1 - v.y) / 2 * H }; },
    });
    document.getElementById('overlay').style.opacity = String(1 - 0.5 * glitch);
  }

  // ---------------------------------------------------------------- export API
  let wavBytes = null;
  window.__vtr = {
    info: () => ({ duration: tl.duration, fps: tl.fps, scenes: tl.scenes.map((s) => ({ id: s.id, start: s.start, end: s.end, duration: s.duration })), endCard: tl.endCard, W, H }),
    frame: (t) => { frame(t); return true; },
    debug: () => ({ canvases: document.querySelectorAll("canvas").length, calls: renderer.info.render.calls, cam: camera.position.toArray(), look: cameraAt(0).L.toArray(), bakerVis: actors.baker?.root.visible, bakerParentVis: actors.baker?.root.parent === scene, visible: Object.entries(actors).filter(([, a]) => a.root?.visible).map(([n, a]) => [n, a.root.position.toArray()]) }),
    renderAudio: async () => { const buf = await renderOffline(tl, BASE); wavBytes = encodeWav(buf); return wavBytes.length; },
    audioChunk: (off, len) => {
      const sub = wavBytes.subarray(off, off + len);
      let s = '';
      for (let i = 0; i < sub.length; i += 0x8000) s += String.fromCharCode.apply(null, sub.subarray(i, i + 0x8000));
      return btoa(s);
    },
  };
  frame(0);
  window.__vtrReady = true;
  if (EXPORT) return;

  // ---------------------------------------------------------------- preview playback
  const hud = document.getElementById('hud');
  hud.style.display = 'block';
  let playing = false, t0 = 0, ctx = null, cur = 0, startedAt = 0;
  const draw = () => {
    if (playing) {
      cur = ctx ? ctx.currentTime - startedAt : (performance.now() / 1000 - t0);
      if (cur >= tl.duration) { playing = false; cur = tl.duration; }
    }
    frame(cur);
    hud.textContent = `${cur.toFixed(1)}s / ${tl.duration.toFixed(1)}s · ${sceneAt(cur).title}  —  click/space: play · ←/→ seek (silent)`;
    requestAnimationFrame(draw);
  };
  const play = async () => {
    if (playing) { playing = false; ctx?.close(); ctx = null; return; }
    if (cur < 0.05 || cur >= tl.duration) {
      cur = 0;
      ctx = new AudioContext();
      const voices = await loadVoices(ctx, tl, BASE);
      startedAt = ctx.currentTime + 0.1;
      buildMix(ctx, tl, voices, startedAt);
    } else { ctx = null; t0 = performance.now() / 1000 - cur; }
    playing = true;
  };
  addEventListener('click', play);
  addEventListener('keydown', (e) => {
    if (e.code === 'Space') play();
    if (e.code === 'ArrowRight' || e.code === 'ArrowLeft') {
      playing = false; ctx?.close(); ctx = null;
      cur = clamp(cur + (e.code === 'ArrowRight' ? 5 : -5), 0, tl.duration);
    }
  });
  requestAnimationFrame(draw);
}

main().catch((e) => { console.error(e); document.body.dataset.error = String(e); window.__vtrError = String(e.stack || e); });
