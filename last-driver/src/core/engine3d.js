// 3D frame engine: render(t) is a pure function of the resolved timeline.
// Scene rendered at 720x1280 (software WebGL budget), bloomed, then upscaled
// to 1080x1920 in the final pass where captions are composited crisp.
import * as THREE from 'three';
import gsap from 'gsap';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FinalShader } from './shaders.js';
import { Captions } from './captions.js';
import { clamp, noise1 } from './util.js';
import { buildCity } from '../world/city.js';
import { updateCity, carState, win } from '../world/city-update.js';
import { buildCore, updateCore } from '../world/core.js';

const OUT_W = 1080, OUT_H = 1920, IN_W = 720, IN_H = 1280;

export class Engine3D {
  constructor(tl) {
    this.tl = tl;
    this.fps = tl.fps || 30;
    const r = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
    r.setPixelRatio(1);
    r.setSize(OUT_W, OUT_H, false);
    r.outputColorSpace = THREE.LinearSRGBColorSpace;
    r.toneMapping = THREE.NoToneMapping;
    this.renderer = r;
    this.canvas = r.domElement;
    this.camera = new THREE.PerspectiveCamera(50, IN_W / IN_H, 0.3, 6000);
    this.city = buildCity(r);
    this.core = buildCore(r, this.city.env);
    const comp = new EffectComposer(r);
    comp.setPixelRatio(1);
    comp.setSize(IN_W, IN_H);
    this.renderPass = new RenderPass(this.city.scene, this.camera);
    comp.addPass(this.renderPass);
    this.bloom = new UnrealBloomPass(new THREE.Vector2(IN_W / 2, IN_H / 2), 0.75, 0.5, 0.92);
    comp.addPass(this.bloom);
    // final pass: tone map + grade + caption overlay
    const fs = { ...FinalShader, uniforms: THREE.UniformsUtils.clone(FinalShader.uniforms) };
    fs.uniforms.uExposure = { value: 1.0 };
    fs.fragmentShader = fs.fragmentShader
      .replace('uniform float uCA;', 'uniform float uCA; uniform float uExposure;\n vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }')
      .replace('float l = dot(col, vec3(0.299,0.587,0.114));', 'col = pow(aces(col*uExposure), vec3(1.0/2.2));\n      float l = dot(col, vec3(0.299,0.587,0.114));');
    this.final = new ShaderPass(fs);
    this.final.uniforms.uRes.value.set(OUT_W, OUT_H);
    comp.addPass(this.final);
    this.composer = comp;
    // caption overlay
    this.ov = document.createElement('canvas');
    this.ov.width = OUT_W; this.ov.height = OUT_H;
    this.octx = this.ov.getContext('2d');
    this.ovTex = new THREE.CanvasTexture(this.ov);
    this.ovTex.colorSpace = THREE.NoColorSpace;
    this.ovTex.minFilter = THREE.LinearFilter;
    this.final.uniforms.tOv.value = this.ovTex;
    this.final.uniforms.uHasOv.value = 1;
    this.captions = new Captions(tl, this.octx);
  }

  shotAt(t) {
    const S = this.tl.shots;
    let lo = 0, hi = S.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (S[mid].start <= t + 1e-6) lo = mid; else hi = mid - 1; }
    return S[lo];
  }
  warm() { return true; }

  // camera for a shot at local progress p (pure)
  camAt(shot, p) {
    const c = shot.camera || {};
    const k = gsap.parseEase(c.ease || 'power1.inOut')(clamp(p));
    const L = (a, b) => (a === undefined ? b : b === undefined ? a : Array.isArray(a) ? a.map((x, i) => x + (b[i] - x) * k) : a + (b - a) * k);
    const F = c.from || {}, T = c.to || {};
    const g = (n, d) => { const v = L(F[n], T[n]); return v === undefined ? d : v; };
    let pos, look;
    const car = shot.scene === 'city' ? carState(shot, p) : null;
    const tgt = () => {
      if (c.target === 'kira') {
        const kz = shot.fx?.kira || {};
        const a = kz.from || kz.pos || [0, 0, 0], b = kz.to || kz.pos || a;
        const w = win(p, kz.a ?? 0, kz.b ?? 1, 'none');
        return new THREE.Vector3(a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w, a[2] + (b[2] - a[2]) * w);
      }
      return car ? car.pos.clone() : new THREE.Vector3();
    };
    const mode = c.mode || 'chase';
    if (mode === 'chase') {
      const base = tgt();
      pos = base.clone().add(new THREE.Vector3(g('side', 0), g('up', 2.2), g('back', 8)));
      look = base.clone().add(new THREE.Vector3(g('lookSide', 0), g('lookUp', 1), -g('ahead', 6)));
    } else if (mode === 'orbit') {
      const base = tgt();
      const a = g('angle', 0) * Math.PI / 180, rr = g('radius', 8);
      pos = base.clone().add(new THREE.Vector3(Math.sin(a) * rr, g('up', 1.5), Math.cos(a) * rr));
      look = base.clone().add(new THREE.Vector3(0, g('lookUp', 0.8), 0));
    } else if (mode === 'track') {
      pos = new THREE.Vector3(...g('pos', [0, 5, 0]));
      if (c.relZ) pos.z += tgt().z;
      look = tgt().add(new THREE.Vector3(...g('lookOff', [0, 1, 0])));
    } else {
      pos = new THREE.Vector3(...g('pos', [0, 10, 30]));
      look = new THREE.Vector3(...g('look', [0, 10, 0]));
    }
    const sh = c.shake || 0;
    if (sh) {
      const lt = p * shot.dur;
      pos.add(new THREE.Vector3((noise1(lt * 8, 1) - 0.5) * sh, (noise1(lt * 8, 2) - 0.5) * sh, 0));
      look.add(new THREE.Vector3((noise1(lt * 6, 3) - 0.5) * sh * 0.6, (noise1(lt * 6, 4) - 0.5) * sh * 0.6, 0));
    }
    return { pos, look, fov: g('fov', 50), roll: g('roll', 0), car };
  }

  applyCam(cam, s) {
    cam.position.copy(s.pos);
    cam.up.set(0, 1, 0);
    cam.lookAt(s.look);
    cam.rotateZ((s.roll * Math.PI) / 180);
    cam.fov = s.fov;
    cam.aspect = IN_W / IN_H;
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld(true);
  }

  renderReflection(W) {
    if (!W.refl) return;
    const cam = this.camera, rc = W.refl.cam;
    const normal = new THREE.Vector3(0, 1, 0);
    const mirror = new THREE.Vector3(0, 0, 0);
    const camPos = new THREE.Vector3().setFromMatrixPosition(cam.matrixWorld);
    const rot = new THREE.Matrix4().extractRotation(cam.matrixWorld);
    const lookAt = new THREE.Vector3(0, 0, -1).applyMatrix4(rot).add(camPos);
    const view = mirror.clone().sub(camPos).reflect(normal).negate().add(mirror);
    const target = mirror.clone().sub(lookAt).reflect(normal).negate().add(mirror);
    rc.position.copy(view);
    rc.up.set(0, 1, 0).applyMatrix4(rot).reflect(normal);
    rc.lookAt(target);
    rc.near = cam.near; rc.far = cam.far;
    rc.projectionMatrix.copy(cam.projectionMatrix);
    rc.updateMatrixWorld(true);
    rc.matrixWorldInverse.copy(rc.matrixWorld).invert();
    W.refl.texMat.set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1).multiply(rc.projectionMatrix).multiply(rc.matrixWorldInverse);
    W.ground.visible = false;
    const hideRain = W.rain && W.rain.visible;
    if (W.rain) W.rain.visible = false;
    const r = this.renderer;
    r.setRenderTarget(W.refl.rt);
    r.clear();
    r.render(W.scene, rc);
    r.setRenderTarget(null);
    W.ground.visible = true;
    if (W.rain) W.rain.visible = hideRain;
  }

  render(t) {
    const shot = this.shotAt(t);
    const lt = t - shot.start;
    const p = clamp(lt / shot.dur);
    const fx = shot.fx || {};
    const W = shot.scene === 'core' ? this.core : this.city;
    const s = this.camAt(shot, p);
    this.applyCam(this.camera, s);
    const f = { t, p, lt, fx, shot, camera: this.camera };
    if (W === this.city) updateCity(W, f, s.car || carState(shot, p));
    else updateCore(W, f);
    this.renderReflection(W);
    // motion blur from camera motion (projected point ahead of the lens)
    const dt = 1 / this.fps;
    const pp = clamp(p - dt / shot.dur);
    const prevS = this.camAt(shot, pp === p ? clamp(p + dt / shot.dur) : pp);
    const prevCam = this.camera.clone();
    this.applyCam(prevCam, prevS);
    const probe = new THREE.Vector3(0, 0, -30).applyMatrix4(this.camera.matrixWorld);
    const a = probe.clone().project(this.camera), b = probe.clone().project(prevCam);
    let bx = (a.x - b.x) * OUT_W * 0.5 * 0.55, by = -(a.y - b.y) * OUT_H * 0.5 * 0.55;
    if (pp === p) { bx = -bx; by = -by; }
    const md = shot.camera?.mode || 'chase';
    const bm = fx.blur ?? (md === 'chase' || md === 'orbit' ? 0.3 : md === 'track' ? 0.45 : 0.9);
    bx *= bm; by *= bm;
    const len = Math.hypot(bx, by);
    if (len > 42) { bx *= 42 / len; by *= 42 / len; }
    // grade, flashes, glitch
    const u = this.final.uniforms;
    u.uBlur.value.set(bx, by);
    u.uTime.value = t;
    let flash = 0;
    if (shot.flashIn) flash = Math.max(flash, shot.flashIn * Math.exp(-lt * 8));
    for (const fl of fx.flash || []) if (p >= fl[0]) flash = Math.max(flash, fl[1] * Math.exp(-(p - fl[0]) * shot.dur * 5));
    u.uFlash.value = clamp(flash);
    u.uFlashCol.value.set(...(fx.flashCol || [0.85, 0.95, 1]));
    u.uGlitch.value = fx.glitch ? win(p, fx.glitch[0], fx.glitch[1], 'none') * (fx.glitch[2] ?? 1) : 0;
    u.uSat.value = fx.sat ?? 1.12;
    u.uExposure.value = fx.exposure ?? 1.0;
    this.bloom.strength = fx.bloom ?? (shot.scene === 'core' ? 0.42 : 0.75);
    // captions
    const o = this.octx;
    o.setTransform(1, 0, 0, 1, 0, 0);
    o.clearRect(0, 0, OUT_W, OUT_H);
    const beatDur = 60 / this.tl.bpm;
    this.captions.draw(o, t, ((t / beatDur) % 1 + 1) % 1);
    this.ovTex.needsUpdate = true;
    this.renderPass.scene = W.scene;
    this.composer.render();
    return this.canvas;
  }
}
