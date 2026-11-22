// NEO KAIA — one continuous 3D world along the chase route (hero drives -Z):
//   s 0–600 street (traffic lights, neon) · 600–880 market tunnel ·
//   880–1000 ramp · 1000–1520 skyway · 1520–1610 drawbridge over the river ·
//   1610–1980 skyway to Tower Nine.
import * as THREE from 'three';
import { rng, h1 } from '../core/util.js';
import { buildingMaterial, groundMaterial, skyMaterial, rainMaterial, beamMaterial, fogUniforms } from '../core/shaders.js';
import { heroCar, trafficGeometry } from './car.js';
import { kira } from './human.js';

export const ROUTE = { tunnel: [600, 880], ramp: [880, 1000], skyY: 24, bridge: [1520, 1610], river: [1490, 1640], tower: 2060 };

export function routeY(s) {
  if (s < ROUTE.ramp[0]) return 0;
  if (s < ROUTE.ramp[1]) { const u = (s - ROUTE.ramp[0]) / (ROUTE.ramp[1] - ROUTE.ramp[0]); return ROUTE.skyY * u * u * (3 - 2 * u); }
  return ROUTE.skyY;
}

function signTexture(text, col, vertical) {
  const c = document.createElement('canvas');
  c.width = vertical ? 128 : 512; c.height = vertical ? 512 : 160;
  const g = c.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,0.85)';
  g.fillRect(0, 0, c.width, c.height);
  g.strokeStyle = col; g.lineWidth = 8; g.strokeRect(6, 6, c.width - 12, c.height - 12);
  g.fillStyle = col;
  g.shadowColor = col; g.shadowBlur = 18;
  g.textAlign = 'center'; g.textBaseline = 'middle';
  if (vertical) {
    g.font = '86px Anton, Impact, sans-serif';
    const chars = text.split('');
    chars.forEach((ch, i) => g.fillText(ch, 64, 70 + i * ((512 - 110) / Math.max(1, chars.length - 1))));
  } else {
    g.font = '104px Anton, Impact, sans-serif';
    g.fillText(text, 256, 86);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function faceTexture() {
  // stylised glowing portrait of Kira (used on every screen at the end)
  const c = document.createElement('canvas');
  c.width = 512; c.height = 900;
  const g = c.getContext('2d');
  const bg = g.createLinearGradient(0, 0, 0, 900);
  bg.addColorStop(0, '#02121a'); bg.addColorStop(1, '#00060c');
  g.fillStyle = bg; g.fillRect(0, 0, 512, 900);
  g.save();
  g.translate(256, 430);
  g.shadowColor = '#3ef2ff'; g.shadowBlur = 30;
  g.strokeStyle = '#7ff7ff'; g.lineWidth = 7; g.lineCap = 'round';
  // hair / hood silhouette
  g.fillStyle = 'rgba(40,220,255,0.10)';
  g.beginPath(); g.ellipse(0, -40, 190, 250, 0, 0, Math.PI * 2); g.fill();
  // face outline
  g.beginPath(); g.moveTo(-120, -110); g.quadraticCurveTo(-130, 110, 0, 190); g.quadraticCurveTo(130, 110, 120, -110); g.stroke();
  // fringe
  g.beginPath(); g.moveTo(-150, -90); g.quadraticCurveTo(-60, -230, 40, -160); g.quadraticCurveTo(110, -230, 150, -90); g.stroke();
  // eyes
  g.fillStyle = '#e8ffff';
  for (const s of [-1, 1]) {
    g.beginPath(); g.ellipse(s * 55, -10, 34, 13, 0, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.arc(s * 55, -10, 9, 0, Math.PI * 2); g.fill();
  }
  g.beginPath(); g.moveTo(0, 10); g.lineTo(-10, 70); g.lineTo(8, 74); g.stroke();
  g.beginPath(); g.moveTo(-40, 115); g.quadraticCurveTo(0, 128, 40, 115); g.stroke();
  g.restore();
  // scanlines
  g.fillStyle = 'rgba(0,0,0,0.35)';
  for (let y = 0; y < 900; y += 6) g.fillRect(0, y, 512, 2);
  g.font = '64px Anton, Impact, sans-serif';
  g.textAlign = 'center';
  g.fillStyle = '#7ff7ff';
  g.fillText('WELCOME HOME', 256, 820);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function envMapFor(renderer) {
  const s = new THREE.Scene();
  const sky = new THREE.Mesh(new THREE.SphereGeometry(50, 32, 16), new THREE.MeshBasicMaterial({ side: THREE.BackSide, vertexColors: true }));
  const geo = sky.geometry;
  const cols = [];
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / 50;
    const c = new THREE.Color().lerpColors(new THREE.Color('#3a1040'), new THREE.Color('#05040c'), Math.max(0, y));
    if (y < 0) c.lerp(new THREE.Color('#020205'), -y);
    cols.push(c.r, c.g, c.b);
  }
  geo.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
  s.add(sky);
  const panel = (col, x, y, z, w, h) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: col, side: THREE.DoubleSide }));
    m.position.set(x, y, z);
    m.lookAt(0, 0, 0);
    s.add(m);
  };
  panel(new THREE.Color(3, 0.3, 2), 30, 8, 10, 14, 4);
  panel(new THREE.Color(0.2, 2.5, 3), -30, 12, -10, 10, 18);
  panel(new THREE.Color(2.5, 2.2, 1.8), 0, 40, 0, 30, 30);
  panel(new THREE.Color(0.3, 1.5, 3), 10, 6, -35, 20, 3);
  panel(new THREE.Color(3, 0.6, 0.3), -15, 5, 32, 8, 3);
  const pm = new THREE.PMREMGenerator(renderer);
  const rt = pm.fromScene(s, 0.02);
  pm.dispose();
  return rt.texture;
}

export function buildCity(renderer, seed = 9) {
  const r = rng(seed);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#05030f');
  const shared = fogUniforms();
  const env = envMapFor(renderer);
  scene.environment = null;
  const W = { scene, shared, env, updaters: [] };

  // ---- sky dome
  const sky = new THREE.Mesh(new THREE.SphereGeometry(3000, 32, 16), skyMaterial());
  sky.frustumCulled = false;
  scene.add(sky);
  W.sky = sky;

  // ---- lights for PBR objects (car, deck, Kira)
  scene.add(new THREE.HemisphereLight(0x6a70ff, 0x300a30, 0.9));
  const key = new THREE.DirectionalLight(0x9fd8ff, 1.2);
  key.position.set(40, 80, 30);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xff3399, 1.0);
  rim.position.set(-50, 20, -60);
  scene.add(rim);

  // ---- mirror reflection target (ground plane y = 0)
  const reflRT = new THREE.WebGLRenderTarget(270, 480, { type: THREE.HalfFloatType });
  const texMat = new THREE.Matrix4();
  W.refl = { rt: reflRT, texMat, cam: new THREE.PerspectiveCamera() };
  const groundMat = groundMaterial(shared, reflRT.texture, texMat);
  groundMat.uniforms.uRiver = { value: new THREE.Vector2(-ROUTE.river[1], -ROUTE.river[0]) };
  groundMat.fragmentShader = groundMat.fragmentShader.replace('uniform float uRain;', 'uniform float uRain; uniform vec2 uRiver;')
    .replace('// reflection with rain ripples', `float river = step(uRiver.x, vW.z) * step(vW.z, uRiver.y);
        col = mix(col, vec3(0.005,0.012,0.03), river);
        // reflection with rain ripples`)
    .replace('float wet = mix(0.55, 1.0, puddle) * fres;', 'float wet = mix(mix(0.55, 1.0, puddle), 1.15, river) * fres;');
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(6000, 6000), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.z = -1000;
  scene.add(ground);
  W.ground = ground;

  // ---- buildings (one instanced draw)
  const boxes = [];
  const addB = (x, z, w, d, h, litP = 0.45) => boxes.push({ x, z, w, d, h, litP });
  const inRiver = (z, d) => z + d / 2 > -ROUTE.river[1] - 10 && z - d / 2 < -ROUTE.river[0] + 10;
  for (let z = 150; z > -2500; z -= r.range(16, 30)) {
    for (const side of [-1, 1]) {
      let x = 17 + r.range(0, 4);
      let row = 0;
      while (x < 420) {
        const w = r.range(14, 30), d = r.range(14, 26);
        const cz = z - d / 2;
        const nearTower = Math.abs(cz + ROUTE.tower) < 260;
        let h = r.range(25, 90) + row * r.range(10, 28) + (nearTower ? r.range(60, 200) : 0) + (cz < -1000 ? r.range(20, 120) : 0);
        if (r.next() < 0.08) h *= 2.2;
        const inTunnelZone = cz < -ROUTE.tunnel[0] + 10 && cz > -ROUTE.tunnel[1] - 10 && x < 40;
        const plaza = Math.abs(cz + ROUTE.tower) < 120 && x < 110;
        if (!inRiver(cz, d) && !inTunnelZone && !plaza) addB(side * (x + w / 2), cz, w, d, h, r.range(0.25, 0.65));
        x += w + r.range(3, 12);
        row++;
        if (row > 9) break;
      }
    }
  }
  // far skyline ring for depth
  for (let i = 0; i < 160; i++) {
    const a = r.range(0, Math.PI * 2), rad = r.range(700, 1300);
    const bx = Math.cos(a) * rad, bz = -1000 + Math.sin(a) * rad;
    if (Math.abs(bx) < 140 && bz > -2400 && bz < 250) continue; // keep the route clear
    addB(bx, bz, r.range(40, 90), r.range(40, 90), r.range(120, 520), 0.35);
  }
  // Tower Nine
  addB(0, -ROUTE.tower, 92, 92, 880, 0.75);
  const bgeo = new THREE.BoxGeometry(1, 1, 1);
  const bmat = buildingMaterial(shared);
  W.buildingMat = bmat;
  const inst = new THREE.InstancedMesh(bgeo, bmat, boxes.length);
  const aSeed = new Float32Array(boxes.length), aTint = new Float32Array(boxes.length * 3), aLitP = new Float32Array(boxes.length);
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion();
  const tints = [[0.55, 0.6, 0.9], [0.8, 0.5, 0.8], [0.5, 0.75, 0.8], [0.7, 0.65, 0.6], [0.45, 0.5, 0.7]];
  boxes.forEach((b, i) => {
    m4.compose(new THREE.Vector3(b.x, b.h / 2, b.z), q, new THREE.Vector3(b.w, b.h, b.d));
    inst.setMatrixAt(i, m4);
    aSeed[i] = h1(i, 3);
    const t = tints[i % tints.length];
    aTint.set(t, i * 3);
    aLitP[i] = b.litP;
  });
  bgeo.setAttribute('aSeed', new THREE.InstancedBufferAttribute(aSeed, 1));
  bgeo.setAttribute('aTint', new THREE.InstancedBufferAttribute(aTint, 3));
  bgeo.setAttribute('aLitP', new THREE.InstancedBufferAttribute(aLitP, 1));
  inst.frustumCulled = false;
  scene.add(inst);
  W.boxes = boxes;

  // ---- rooftop antennas + aircraft lights
  const antGeo = new THREE.CylinderGeometry(0.25, 0.4, 1, 6);
  const tall = boxes.filter((b) => b.h > 140);
  const ant = new THREE.InstancedMesh(antGeo, new THREE.MeshBasicMaterial({ color: '#0c0c14' }), tall.length);
  const beacon = new THREE.InstancedMesh(new THREE.SphereGeometry(0.9, 8, 6), new THREE.MeshBasicMaterial({ color: new THREE.Color(5, 0.3, 0.3), toneMapped: false }), tall.length);
  tall.forEach((b, i) => {
    const ah = 10 + h1(i, 5) * 30;
    m4.compose(new THREE.Vector3(b.x, b.h + ah / 2, b.z), q, new THREE.Vector3(1, ah, 1));
    ant.setMatrixAt(i, m4);
    m4.compose(new THREE.Vector3(b.x, b.h + ah, b.z), q, new THREE.Vector3(1, 1, 1));
    beacon.setMatrixAt(i, m4);
  });
  scene.add(ant, beacon);
  W.beacon = beacon;

  // ---- neon signs on road-facing facades
  const words = [['NEO KAIA', '#ff2e88'], ['AUTO ONLY', '#3ef2ff'], ['RAMEN', '#ffb13e'], ['HOTEL 9', '#b06bff'], ['GRID', '#3ef2ff'], ['NO DRIVERS', '#ff2e88'], ['24H', '#7dff6b'], ['SYNC', '#3ef2ff'], ['TOWER 9', '#ffd23e'], ['KAIA', '#ff2e88']];
  const signMats = words.map(([t, c], i) => new THREE.MeshBasicMaterial({ map: signTexture(t, c, i % 2 === 1), toneMapped: false, color: new THREE.Color(2.2, 2.2, 2.2) }));
  W.signMats = signMats;
  const front = boxes.filter((b) => Math.abs(b.x) - b.w / 2 < 24 && b.z > -1480);
  front.forEach((b, i) => {
    if (h1(i, 8) < 0.35) return;
    const k = i % words.length;
    const vertical = k % 2 === 1;
    const w = vertical ? 2.6 : 9, hh = vertical ? 10 : 2.8;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, hh), signMats[k]);
    const side = Math.sign(b.x);
    const fx = b.x - side * (b.w / 2 + 0.3);
    m.position.set(fx, 5 + h1(i, 9) * Math.min(30, b.h - 12), b.z + (h1(i, 10) - 0.5) * b.d * 0.6);
    m.rotation.y = side > 0 ? -Math.PI / 2 : Math.PI / 2;
    if (vertical) { m.rotation.y += side * 0.0; m.position.x -= side * 1.2; m.rotation.y = side > 0 ? -Math.PI / 2 + Math.PI / 2 * 0.0 : Math.PI / 2; }
    scene.add(m);
  });

  // ---- giant holo billboards (switch to Kira's face in the finale)
  const faceTex = faceTexture();
  const boardMat = new THREE.ShaderMaterial({
    uniforms: { uTime: shared.uTime, uFace: { value: 0 }, tFace: { value: faceTex }, uSeed: { value: 0 } },
    vertexShader: `varying vec2 vUv; varying vec3 vW; void main(){ vUv=uv; vec4 w = modelMatrix*vec4(position,1.); vW=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `uniform float uTime; uniform float uFace; uniform sampler2D tFace; varying vec2 vUv; varying vec3 vW;
      float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); return fract(p.x*p.y); }
      void main(){
        float sd = hash(floor(vW.xz/50.));
        vec3 a = mix(vec3(1.0,0.1,0.55), vec3(0.1,0.9,1.0), sd);
        float wave = 0.5+0.5*sin(vUv.y*14.0 - uTime*2.0 + sd*20.0);
        vec3 ad = a*(0.25 + 0.75*wave) * (0.6 + 0.4*step(0.5, fract(vUv.x*3.0 + uTime*0.2)));
        float scan = 0.85 + 0.15*sin(vUv.y*600.0);
        vec3 face = texture2D(tFace, vUv).rgb * 2.2;
        vec3 c = mix(ad, face, uFace) * scan * 1.6;
        float g = step(0.97, hash(vec2(floor(vUv.y*40.0), floor(uTime*12.0)))) * uFace;
        c += vec3(0.6,1.2,1.4)*g;
        gl_FragColor = vec4(c, 1.0);
      }`,
    toneMapped: false,
  });
  W.boardMat = boardMat;
  const boardHosts = boxes.filter((b) => b.h > 90 && Math.abs(b.x) - b.w / 2 < 60 && b.z < 0 && b.z > -1950);
  boardHosts.forEach((b, i) => {
    if (i % 2) return;
    const side = Math.sign(b.x);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(Math.min(b.d * 0.92, 24), 42), boardMat);
    m.position.set(b.x - side * (b.w / 2 + 0.4), Math.min(b.h - 25, 26 + h1(i, 2) * 30), b.z);
    m.rotation.y = side > 0 ? -Math.PI / 2 : Math.PI / 2;
    scene.add(m);
  });
  // Tower Nine crown screen
  const crown = new THREE.Mesh(new THREE.PlaneGeometry(80, 140), boardMat);
  crown.position.set(0, 700, -ROUTE.tower + 46.5);
  scene.add(crown);
  const nine = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshBasicMaterial({ map: signTexture('9', '#ffd23e', false), toneMapped: false, color: new THREE.Color(2.5, 2.5, 2.5) }));
  nine.position.set(0, 820, -ROUTE.tower + 46.6);
  scene.add(nine);
  const spire = new THREE.Mesh(new THREE.ConeGeometry(14, 160, 8), new THREE.MeshBasicMaterial({ color: '#0a0a14' }));
  spire.position.set(0, 960, -ROUTE.tower);
  scene.add(spire);
  // glass elevator shaft + capsule on Tower Nine
  const shaft = new THREE.Mesh(new THREE.BoxGeometry(8, 860, 4), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.1, 0.5, 0.7), transparent: true, opacity: 0.25, blending: THREE.AdditiveBlending, depthWrite: false }));
  shaft.position.set(0, 430 + ROUTE.skyY, -ROUTE.tower + 48);
  scene.add(shaft);
  const capsule = new THREE.Mesh(new THREE.BoxGeometry(6, 7, 3.5), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.5, 2.2, 1.6), toneMapped: false }));
  capsule.position.set(0, ROUTE.skyY + 4, -ROUTE.tower + 48);
  scene.add(capsule);
  W.capsule = capsule;

  // ---- street: traffic lights + lamps
  const lightMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.2, 3, 0.6), toneMapped: false });
  W.trafficLightMat = lightMat;
  const poleMat = new THREE.MeshStandardMaterial({ color: '#1a1a22', metalness: 0.8, roughness: 0.4, envMap: env });
  const lampMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 2.2, 1.4), toneMapped: false });
  for (let z = -40; z > -600; z -= 80) {
    for (const side of [-1, 1]) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.2, 7, 8), poleMat);
      pole.position.set(side * 12.5, 3.5, z);
      const arm = new THREE.Mesh(new THREE.BoxGeometry(6, 0.2, 0.2), poleMat);
      arm.position.set(side * 9.8, 6.8, z);
      const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.6, 0.5), lightMat);
      lamp.position.set(side * 7.4, 6.2, z);
      scene.add(pole, arm, lamp);
    }
  }
  const lampPos = [];
  for (let z = 0; z > -600; z -= 32) for (const side of [-1, 1]) lampPos.push([side * 13.5, 9, z - (side > 0 ? 16 : 0)]);
  for (let z = -1000; z > -1980; z -= 36) for (const side of [-1, 1]) if (z > -ROUTE.bridge[0] || z < -ROUTE.bridge[1]) lampPos.push([side * 12.4, ROUTE.skyY + 9, z]);
  const lampHead = new THREE.InstancedMesh(new THREE.BoxGeometry(1.6, 0.3, 0.6), lampMat, lampPos.length);
  const lampPole = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.12, 0.16, 9, 6), poleMat, lampPos.length);
  lampPos.forEach(([x, y, z], i) => {
    m4.compose(new THREE.Vector3(x - Math.sign(x) * 0.8, y, z), q, new THREE.Vector3(1, 1, 1));
    lampHead.setMatrixAt(i, m4);
    m4.compose(new THREE.Vector3(x, y - 4.5, z), q, new THREE.Vector3(1, 1, 1));
    lampPole.setMatrixAt(i, m4);
  });
  scene.add(lampHead, lampPole);
  const lampBeam = new THREE.InstancedMesh(new THREE.ConeGeometry(4.5, 9, 16, 1, true), beamMaterial('#ffd8a0', 0.2), lampPos.length);
  lampPos.forEach(([x, y, z], i) => {
    m4.compose(new THREE.Vector3(x - Math.sign(x) * 0.8, y - 4.5, z), q, new THREE.Vector3(1, 1, 1));
    lampBeam.setMatrixAt(i, m4);
  });
  scene.add(lampBeam);

  // ---- market tunnel
  const tl = ROUTE.tunnel[1] - ROUTE.tunnel[0];
  const shell = new THREE.Mesh(new THREE.CylinderGeometry(14, 14, tl, 32, 1, true, -Math.PI / 2, Math.PI), new THREE.MeshStandardMaterial({ color: '#0c0a14', roughness: 0.8, side: THREE.BackSide, envMap: env, envMapIntensity: 0.3 }));
  shell.rotation.x = Math.PI / 2;
  shell.position.set(0, 0, -(ROUTE.tunnel[0] + tl / 2));
  scene.add(shell);
  const ringN = Math.floor(tl / 7);
  const ringGeo = new THREE.TorusGeometry(13.6, 0.12, 4, 40, Math.PI);
  const ringMatA = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.1, 1.3, 1.7), toneMapped: false });
  const ringMatB = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.7, 0.1, 0.85), toneMapped: false });
  const ringsA = new THREE.InstancedMesh(ringGeo, ringMatA, Math.ceil(ringN / 2));
  const ringsB = new THREE.InstancedMesh(ringGeo, ringMatB, Math.ceil(ringN / 2));
  for (let i = 0; i < ringN; i++) {
    m4.compose(new THREE.Vector3(0, 0, -(ROUTE.tunnel[0] + i * 7)), q, new THREE.Vector3(1, 1, 1));
    (i % 2 ? ringsB : ringsA).setMatrixAt(Math.floor(i / 2), m4);
  }
  scene.add(ringsA, ringsB);
  // stalls + lanterns along the tunnel walls
  const stallMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.8, 1.0, 0.45), toneMapped: false });
  const stallBody = new THREE.MeshStandardMaterial({ color: '#2a1a1a', roughness: 0.7, envMap: env, envMapIntensity: 0.4 });
  const lantMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 1.4, 0.4), toneMapped: false });
  for (let z = ROUTE.tunnel[0] + 6; z < ROUTE.tunnel[1] - 6; z += 9) {
    for (const side of [-1, 1]) {
      const st = new THREE.Mesh(new THREE.BoxGeometry(2.4, 3, 6), stallBody);
      st.position.set(side * 11.6, 1.5, -z);
      const glow = new THREE.Mesh(new THREE.PlaneGeometry(5.2, 1.6), stallMat);
      glow.position.set(side * 10.35, 1.9, -z);
      glow.rotation.y = side > 0 ? -Math.PI / 2 : Math.PI / 2;
      const l = new THREE.Mesh(new THREE.SphereGeometry(0.45, 10, 8), lantMat);
      l.position.set(side * (7 + h1(z, 2) * 3), 6 + h1(z, 3) * 4, -z - 3);
      scene.add(st, glow, l);
    }
  }

  // ---- skyway deck, ramp, pillars, rails
  const deckTex = (() => {
    const c = document.createElement('canvas'); c.width = 256; c.height = 1024;
    const g = c.getContext('2d');
    g.fillStyle = '#0b0b10'; g.fillRect(0, 0, 256, 1024);
    for (let i = 0; i < 3000; i++) { g.fillStyle = `rgba(255,255,255,${r.next() * 0.03})`; g.fillRect(r.next() * 256, r.next() * 1024, 2, 2); }
    g.fillStyle = 'rgba(230,230,210,0.55)';
    for (let y = 0; y < 1024; y += 96) { g.fillRect(80, y, 5, 48); g.fillRect(171, y, 5, 48); }
    g.fillStyle = 'rgba(240,200,60,0.6)'; g.fillRect(126, 0, 4, 1024);
    const t = new THREE.CanvasTexture(c); t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    return t;
  })();
  const deckMat = new THREE.MeshStandardMaterial({ map: deckTex, color: '#ffffff', roughness: 0.22, metalness: 0.35, envMap: env, envMapIntensity: 1.1 });
  const railMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.2, 2.4, 3.0), toneMapped: false });
  const concrete = new THREE.MeshStandardMaterial({ color: '#2a2833', roughness: 0.85, envMap: env, envMapIntensity: 0.3 });
  const deckSeg = (z0, z1, y0, y1) => {
    const len = z1 - z0;
    const geo = new THREE.BoxGeometry(26, 1.2, len);
    const tex = deckTex.clone(); tex.repeat.set(1, len / 60); tex.needsUpdate = true;
    const mat = deckMat.clone(); mat.map = tex;
    const m = new THREE.Mesh(geo, mat);
    const ang = Math.atan2(y1 - y0, len);
    m.position.set(0, (y0 + y1) / 2 - 0.6, -(z0 + z1) / 2);
    m.rotation.x = ang;
    m.scale.z = Math.sqrt(len * len + (y1 - y0) ** 2) / len;
    scene.add(m);
    for (const side of [-1, 1]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, len), railMat);
      rail.position.set(side * 12.8, (y0 + y1) / 2 + 1.0, -(z0 + z1) / 2);
      rail.rotation.x = ang;
      rail.scale.z = m.scale.z;
      const wall = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.0, len), concrete);
      wall.position.set(side * 12.8, (y0 + y1) / 2 + 0.4, -(z0 + z1) / 2);
      wall.rotation.x = ang;
      wall.scale.z = m.scale.z;
      scene.add(rail, wall);
    }
  };
  // ramp in segments to follow the smoothstep
  for (let s = ROUTE.ramp[0]; s < ROUTE.ramp[1]; s += 20) deckSeg(s, s + 20, routeY(s), routeY(s + 20));
  deckSeg(ROUTE.ramp[1], ROUTE.bridge[0], ROUTE.skyY, ROUTE.skyY);
  deckSeg(ROUTE.bridge[1], ROUTE.tower - 50, ROUTE.skyY, ROUTE.skyY);
  for (let s = ROUTE.ramp[1]; s < ROUTE.tower - 60; s += 40) {
    if (s > ROUTE.bridge[0] - 20 && s < ROUTE.bridge[1] + 20) continue;
    for (const side of [-1, 1]) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(2.2, ROUTE.skyY, 2.2), concrete);
      p.position.set(side * 8, ROUTE.skyY / 2 - 1, -s);
      scene.add(p);
    }
  }
  // drawbridge: two leaves hinged at the bridge ends
  const leafLen = (ROUTE.bridge[1] - ROUTE.bridge[0]) / 2;
  const leaves = [];
  for (const end of [0, 1]) {
    const pivot = new THREE.Group();
    pivot.position.set(0, ROUTE.skyY - 0.6, -(end === 0 ? ROUTE.bridge[0] : ROUTE.bridge[1]));
    const leaf = new THREE.Mesh(new THREE.BoxGeometry(26, 1.4, leafLen), deckMat);
    leaf.position.z = end === 0 ? -leafLen / 2 : leafLen / 2;
    pivot.add(leaf);
    for (const side of [-1, 1]) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, leafLen), new THREE.MeshBasicMaterial({ color: new THREE.Color(3.2, 1.6, 0.2), toneMapped: false }));
      rail.position.set(side * 12.8, 1.4, leaf.position.z);
      pivot.add(rail);
    }
    scene.add(pivot);
    leaves.push({ pivot, end });
    // bridge towers with warning lights
    for (const side of [-1, 1]) {
      const tw = new THREE.Mesh(new THREE.BoxGeometry(5, 60, 5), concrete);
      tw.position.set(side * 16, 30, pivot.position.z + (end === 0 ? 3 : -3));
      const wl = new THREE.Mesh(new THREE.SphereGeometry(1.2, 10, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color(5, 0.4, 0.1), toneMapped: false }));
      wl.position.set(side * 16, 61, tw.position.z);
      scene.add(tw, wl);
    }
  }
  W.leaves = leaves;

  // ---- traffic (instanced bodies + light strips)
  const N = 220;
  const tGeo = trafficGeometry();
  const tMat = new THREE.MeshStandardMaterial({ color: '#2a2c36', metalness: 0.7, roughness: 0.35, envMap: env, envMapIntensity: 1.0 });
  const traffic = new THREE.InstancedMesh(tGeo, tMat, N);
  const tails = new THREE.InstancedMesh(new THREE.BoxGeometry(1.7, 0.12, 0.05), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 0.12, 0.2), toneMapped: false }), N);
  const heads = new THREE.InstancedMesh(new THREE.BoxGeometry(1.7, 0.12, 0.05), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.5, 2.8, 3.2), toneMapped: false }), N);
  const tcols = [];
  for (let i = 0; i < N; i++) {
    const lane = [-9.5, -5.5, 5.5, 9.5][i % 4];
    const skyway = i % 3 === 0;
    tcols.push({ lane, dir: lane < 0 ? 1 : -1, s0: h1(i, 40) * (skyway ? 950 : 600) + (skyway ? 1000 : 0), v: 12 + h1(i, 41) * 10, skyway, col: h1(i, 42) });
  }
  W.trafficData = tcols;
  traffic.frustumCulled = tails.frustumCulled = heads.frustumCulled = false;
  scene.add(traffic, tails, heads);
  W.traffic = { traffic, tails, heads };

  // ---- the river road far below the drawbridge: rivers of headlights
  const HP = 4000;
  const hpGeo = new THREE.BufferGeometry();
  const hpPos = new Float32Array(HP * 3), hpSeed = new Float32Array(HP * 2);
  for (let i = 0; i < HP; i++) { hpSeed[i * 2] = h1(i, 60); hpSeed[i * 2 + 1] = h1(i, 61); }
  hpGeo.setAttribute('position', new THREE.BufferAttribute(hpPos, 3));
  hpGeo.setAttribute('aSeed', new THREE.BufferAttribute(hpSeed, 2));
  const hpMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: shared.uTime, uZ: { value: new THREE.Vector2(-ROUTE.river[0] + 2, -ROUTE.river[1] - 2) }, uTurn: { value: 0 } },
    vertexShader: `uniform float uTime; uniform vec2 uZ; uniform float uTurn; attribute vec2 aSeed; varying vec3 vC;
      void main(){
        float road = step(0.5, aSeed.y);
        float lane = fract(aSeed.y*7.0);
        float dir = lane > 0.5 ? 1.0 : -1.0;
        float x = mod(aSeed.x*1600.0 + uTime*(14.0+lane*8.0)*dir*(1.0-uTurn), 1600.0) - 800.0;
        float z = mix(uZ.x, uZ.y, road) + (lane-0.5)*10.0;
        vec3 p = vec3(x, 0.8, z);
        vC = dir > 0.0 ? vec3(2.6,2.7,3.0) : vec3(3.0,0.2,0.25);
        vC = mix(vC, vec3(2.8,2.9,3.2), uTurn);
        vec4 mv = viewMatrix*vec4(p,1.0);
        gl_PointSize = clamp(260.0 / -mv.z, 1.5, 9.0);
        gl_Position = projectionMatrix*mv;
      }`,
    fragmentShader: `varying vec3 vC; void main(){ vec2 d = gl_PointCoord-0.5; float a = smoothstep(0.5,0.0,length(d)); gl_FragColor = vec4(vC*a, 1.0); }`,
  });
  const hp = new THREE.Points(hpGeo, hpMat);
  hp.frustumCulled = false;
  scene.add(hp);
  W.riverLights = hpMat;

  // ---- drones
  const DN = 70;
  const drone = new THREE.InstancedMesh(new THREE.BoxGeometry(1.4, 0.3, 1.4), new THREE.MeshStandardMaterial({ color: '#15151c', metalness: 0.8, roughness: 0.3, envMap: env }), DN);
  const droneEye = new THREE.InstancedMesh(new THREE.SphereGeometry(0.28, 8, 6), new THREE.MeshBasicMaterial({ color: new THREE.Color(5, 0.2, 0.3), toneMapped: false }), DN);
  drone.frustumCulled = droneEye.frustumCulled = false;
  scene.add(drone, droneEye);
  W.drones = { drone, droneEye, n: DN };

  // ---- rain
  const RN = 6000;
  const rg = new THREE.BufferGeometry();
  const rp = new Float32Array(RN * 2 * 3), rs = new Float32Array(RN * 2 * 3), re = new Float32Array(RN * 2);
  for (let i = 0; i < RN; i++) {
    const sx = h1(i, 70), sy = h1(i, 71), sz = h1(i, 72);
    for (let k = 0; k < 2; k++) { rs.set([sx, sy, sz], (i * 2 + k) * 3); re[i * 2 + k] = k; }
  }
  rg.setAttribute('position', new THREE.BufferAttribute(rp, 3));
  rg.setAttribute('aSeed', new THREE.BufferAttribute(rs, 3));
  rg.setAttribute('aEnd', new THREE.BufferAttribute(re, 1));
  const rain = new THREE.LineSegments(rg, rainMaterial());
  rain.frustumCulled = false;
  scene.add(rain);
  W.rain = rain;

  // ---- hero car + Kira
  W.car = heroCar(env);
  scene.add(W.car);
  W.kira = kira(env);
  W.kira.visible = false;
  scene.add(W.kira);
  return W;
}
