// THE CORE — inside the top of Tower Nine: a cathedral-scale server hall,
// racks of blinking LEDs, a reflective floor, and the wall of light.
import * as THREE from 'three';
import { h1, clamp } from '../core/util.js';
import { kira, poseKira } from './human.js';
import { beamMaterial } from '../core/shaders.js';
import { win } from './city-update.js';

const HALL_L = 90;

function screenTexture() {
  const c = document.createElement('canvas');
  c.width = 1024; c.height = 768;
  return { c, g: c.getContext('2d'), tex: new THREE.CanvasTexture(c) };
}

export function buildCore(renderer, env) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#010205');
  scene.fog = new THREE.FogExp2('#031018', 0.01);
  const W = { scene, env };
  scene.add(new THREE.HemisphereLight(0x40c0ff, 0x050010, 0.6));
  const key = new THREE.DirectionalLight(0xdff6ff, 1.2);
  key.position.set(0, 10, -80);
  scene.add(key);
  // reflection RT for the polished floor
  const reflRT = new THREE.WebGLRenderTarget(270, 480, { type: THREE.HalfFloatType });
  const texMat = new THREE.Matrix4();
  W.refl = { rt: reflRT, texMat, cam: new THREE.PerspectiveCamera() };
  const floorMat = new THREE.ShaderMaterial({
    uniforms: { tRefl: { value: reflRT.texture }, uTexMat: { value: texMat }, uTime: { value: 0 } },
    vertexShader: `uniform mat4 uTexMat; varying vec4 vRU; varying vec3 vW; void main(){ vec4 w = modelMatrix*vec4(position,1.0); vW=w.xyz; vRU=uTexMat*w; gl_Position=projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `uniform sampler2D tRefl; varying vec4 vRU; varying vec3 vW;
      void main(){
        vec2 g = abs(fract(vW.xz/2.0)-0.5);
        float line = smoothstep(0.48,0.5,max(g.x,g.y));
        vec3 base = vec3(0.01,0.012,0.018) + vec3(0.0,0.25,0.35)*line*0.25;
        vec3 refl = texture2D(tRefl, vRU.xy/vRU.w).rgb;
        vec3 V = normalize(cameraPosition - vW);
        float fres = 0.45 + 0.5*pow(1.0-max(V.y,0.0),3.0);
        vec3 col = base + refl*fres*0.85;
        float d = length(cameraPosition - vW);
        col = mix(col, vec3(0.006,0.03,0.045), 1.0-exp(-d*0.01));
        gl_FragColor = vec4(col,1.0);
      }`,
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, HALL_L + 40), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.z = -HALL_L / 2;
  scene.add(floor);
  W.ground = floor;
  // walls + ceiling
  const wallMat = new THREE.MeshStandardMaterial({ color: '#06080c', roughness: 0.5, metalness: 0.6, envMap: env, envMapIntensity: 0.6 });
  for (const side of [-1, 1]) {
    const w = new THREE.Mesh(new THREE.BoxGeometry(1, 30, HALL_L + 20), wallMat);
    w.position.set(side * 14, 15, -HALL_L / 2);
    scene.add(w);
  }
  const ceil = new THREE.Mesh(new THREE.BoxGeometry(30, 1, HALL_L + 20), wallMat);
  ceil.position.set(0, 24, -HALL_L / 2);
  scene.add(ceil);
  // ceiling light strips + volumetric beams
  const stripMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.8, 1.4, 1.6), toneMapped: false });
  for (let z = -4; z > -HALL_L; z -= 9) {
    const s = new THREE.Mesh(new THREE.BoxGeometry(18, 0.15, 0.4), stripMat);
    s.position.set(0, 23.4, z);
    scene.add(s);
    const b = new THREE.Mesh(new THREE.CylinderGeometry(4, 9, 23, 20, 1, true), beamMaterial('#9fe8ff', 0.05));
    b.position.set(0, 11.5, z);
    scene.add(b);
  }
  // server racks with LED faces (instanced; LEDs computed in shader)
  const rackMat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uPulse: { value: 0 } },
    vertexShader: `attribute float aSeed; varying vec2 vUv; varying float vS; varying vec3 vN; varying vec3 vW;
      void main(){ vUv=uv; vS=aSeed; vec4 w = modelMatrix*instanceMatrix*vec4(position,1.0); vW=w.xyz; vN=normalize(mat3(modelMatrix*instanceMatrix)*normal); gl_Position=projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `uniform float uTime; uniform float uPulse; varying vec2 vUv; varying float vS; varying vec3 vN; varying vec3 vW;
      float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); return fract(p.x*p.y); }
      void main(){
        vec3 col = vec3(0.012,0.014,0.02);
        if (abs(vN.x) > 0.5) {
          vec2 g = vec2(vUv.x*10.0, vUv.y*40.0);
          vec2 cell = floor(g); vec2 fr = fract(g);
          float led = step(0.3,fr.x)*step(fr.x,0.55)*step(0.35,fr.y)*step(fr.y,0.65);
          float r = hash(cell + vS*91.0);
          float on = step(0.5, fract(r*13.0 + uTime*(0.5+r*3.0)));
          vec3 lc = r > 0.85 ? vec3(3.0,0.6,0.3) : (r > 0.4 ? vec3(0.2,2.4,3.0) : vec3(0.4,3.0,1.2));
          col += lc*led*on*(1.0+uPulse*2.0);
          col += vec3(0.0,0.05,0.07)*step(0.95, fract(vUv.y*8.0));
        }
        float d = length(cameraPosition - vW);
        col = mix(col, vec3(0.012,0.06,0.09), 1.0-exp(-d*0.012));
        gl_FragColor = vec4(col,1.0);
      }`,
  });
  W.rackMat = rackMat;
  const racks = [];
  for (let z = -6; z > -HALL_L + 14; z -= 2.2) for (const side of [-1, 1]) for (const col of [0, 1]) racks.push([side * (6.5 + col * 3.2), z]);
  const rg = new THREE.BoxGeometry(1.2, 9, 2);
  const seeds = new Float32Array(racks.length);
  racks.forEach((_, i) => { seeds[i] = h1(i, 5); });
  rg.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seeds, 1));
  const rk = new THREE.InstancedMesh(rg, rackMat, racks.length);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion();
  racks.forEach(([x, z], i) => { m4.compose(new THREE.Vector3(x, 4.5, z), q, new THREE.Vector3(1, 1, 1)); rk.setMatrixAt(i, m4); });
  scene.add(rk);
  // the wall of light
  const scr = screenTexture();
  W.screen = scr;
  const wallLight = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uMode: { value: 0 }, tText: { value: scr.tex }, uText: { value: 0 }, uBright: { value: 0.42 } },
    toneMapped: false,
    vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform float uTime; uniform float uMode; uniform sampler2D tText; uniform float uText; uniform float uBright; varying vec2 vUv;
      float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); return fract(p.x*p.y); }
      void main(){
        float colm = floor(vUv.x*90.0);
        float sp = 0.3 + hash(vec2(colm,1.0))*1.2;
        float y = fract(vUv.y*3.0 + uTime*sp + hash(vec2(colm,2.0)));
        float stream = smoothstep(0.0,0.6,y)*step(y,0.62)*step(0.35, hash(vec2(colm,3.0)));
        vec3 data = vec3(0.25,1.2,1.6)*(0.12 + stream*1.1);
        vec3 c = data;
        c = mix(c, vec3(0.0), clamp(uMode,0.0,1.0));          // 1 = black
        c = mix(c, vec3(3.2,3.3,3.4), clamp(uMode-1.0,0.0,1.0)); // 2 = white
        vec4 t = texture2D(tText, vUv);
        c = c*(1.0 - 0.65*uText);
        gl_FragColor = vec4(c*uBright,1.0);
      }`,
  });
  W.wallMat = wallLight;
  const wl = new THREE.Mesh(new THREE.PlaneGeometry(26, 20), wallLight);
  wl.position.set(0, 10, -HALL_L);
  scene.add(wl);
  // the message panel (sized so the words fit the frame)
  const tp = new THREE.Mesh(new THREE.PlaneGeometry(6.6, 4.95), new THREE.MeshBasicMaterial({ map: scr.tex, transparent: true, toneMapped: false, color: new THREE.Color(1.05, 1.1, 1.1), depthWrite: false }));
  tp.position.set(0, 8.4, -HALL_L + 0.05);
  scene.add(tp);
  W.textPlane = tp;
  // pedestal + port
  const ped = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.3, 0.8), new THREE.MeshStandardMaterial({ color: '#0d1016', metalness: 0.9, roughness: 0.2, envMap: env }));
  ped.position.set(0, 0.65, -HALL_L + 6);
  scene.add(ped);
  const port = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.04, 0.14), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.15, 1.1, 1.3), toneMapped: false }));
  port.position.set(0, 1.31, -HALL_L + 6);
  scene.add(port);
  W.port = port;
  W.kira = kira(env);
  scene.add(W.kira);
  W.HALL_L = HALL_L;
  return W;
}

function drawScreen(W, text, sub) {
  const { c, g, tex } = W.screen;
  g.clearRect(0, 0, c.width, c.height);
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillStyle = '#e8ffff';
  g.shadowColor = '#3ef2ff';
  g.shadowBlur = 10;
  // wrap into lines that fit the panel
  const words = text.split(' ');
  const lines = [];
  let cur = '';
  g.font = '150px Anton, Impact, sans-serif';
  for (const w of words) { const tryL = cur ? cur + ' ' + w : w; if (g.measureText(tryL).width > 720 && cur) { lines.push(cur); cur = w; } else cur = tryL; }
  if (cur) lines.push(cur);
  const lh = 165;
  const y0 = 384 - ((lines.length - 1) * lh) / 2 - (sub ? 40 : 0);
  lines.forEach((l, i) => g.fillText(l, 512, y0 + i * lh));
  if (sub) { g.font = '70px Anton, Impact, sans-serif'; g.fillText(sub, 512, y0 + lines.length * lh + 10); }
  tex.needsUpdate = true;
  W.screen.last = text + (sub || '');
}

export function updateCore(W, f) {
  const { t, p, fx } = f;
  W.rackMat.uniforms.uTime.value = t;
  W.wallMat.uniforms.uTime.value = t;
  W.rackMat.uniforms.uPulse.value = fx.pulse ? win(p, fx.pulse[0], fx.pulse[1]) : 0;
  // screen sequence: data -> black -> white -> text
  let mode = 0, txt = 0;
  if (fx.screen) {
    const s = fx.screen; // {black, white, text, chars}
    if (s.black !== undefined && p >= s.black) mode = 1;
    if (s.white !== undefined && p >= s.white) mode = 2 - clamp((p - s.white) / 0.15) * 1.0;
    if (s.text !== undefined && p >= s.text) { txt = 1; mode = 1; }
    if (s.full) { mode = 1; txt = 1; }
  }
  W.wallMat.uniforms.uMode.value = mode;
  W.wallMat.uniforms.uText.value = txt;
  W.textPlane.visible = !!txt;
  if (txt) {
    const full = (fx.screen && fx.screen.msg) || 'WELCOME BACK, KIRA.';
    const n = fx.screen.typeAt ? Math.floor(full.length * clamp((p - fx.screen.text) / Math.max(0.01, fx.screen.typeAt - fx.screen.text))) : full.length;
    const shown = full.slice(0, n) + (Math.floor(t * 3) % 2 ? '_' : ' ');
    if (W.screen.last !== shown + (fx.screen.sub || '')) drawScreen(W, shown, fx.screen.sub);
  }
  W.port.material.color.setRGB(0.15, 1.1 * (fx.plugged !== undefined && p > fx.plugged ? 2.2 : 1), 1.3);
  // Kira
  const K = W.kira;
  const k = fx.kira || {};
  K.visible = fx.kira !== false && !!fx.kira;
  if (fx.kira) {
    const from = new THREE.Vector3(...(k.from || k.pos || [0, 0, -40]));
    const to = new THREE.Vector3(...(k.to || k.pos || [0, 0, -40]));
    K.position.copy(from.lerp(to, win(p, k.a ?? 0, k.b ?? 1, 'none')));
    K.rotation.y = k.yaw ?? Math.PI;
    const walking = k.from && p > (k.a ?? 0) && p < (k.b ?? 1);
    poseKira(K, walking ? 'walk' : k.pose || 'stand', t * 6.5, k.reach ? win(p, k.reach[0], k.reach[1]) : 1);
  }
}
