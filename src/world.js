// The village set: procedural low-poly geometry built once, toggled by timeline state.
import * as THREE from 'three';
import { mat, rng, C, shared } from './materials.js';
import { buildExtras } from './extras.js';

const TAU = Math.PI * 2;

function box(w, h, d, color, x = 0, y = 0, z = 0, opts) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color, opts));
  m.position.set(x, y, z);
  return m;
}

function prismRoof(w, d, h, color, overhang = 0.35) {
  const s = new THREE.Shape();
  s.moveTo(-w / 2 - overhang, 0);
  s.lineTo(w / 2 + overhang, 0);
  s.lineTo(0, h);
  s.lineTo(-w / 2 - overhang, 0);
  const g = new THREE.ExtrudeGeometry(s, { depth: d + overhang * 2, bevelEnabled: false });
  g.translate(0, 0, -(d + overhang * 2) / 2);
  return new THREE.Mesh(g, mat(color));
}

// ---------------------------------------------------------------- chalk textures
export function chalkCanvas(draw, size = 256, time = '3:07') {
  const [hh, mm] = time.split(':').map(Number);
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const R = rng(size + draw.length);
  // chalk stroke: many jittered dots along a path
  const stroke = (pts, w = 7) => {
    for (let i = 0; i < pts.length - 1; i++) {
      const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
      const L = Math.hypot(x1 - x0, y1 - y0);
      const n = Math.max(2, Math.floor(L * 1.6));
      for (let k = 0; k < n; k++) {
        const u = k / n;
        const x = x0 + (x1 - x0) * u + (R() - 0.5) * w * 0.7;
        const y = y0 + (y1 - y0) * u + (R() - 0.5) * w * 0.7;
        g.globalAlpha = 0.35 + R() * 0.55;
        g.fillStyle = R() < 0.12 ? 'rgb(240,120,110)' : 'rgb(205,38,44)';
        g.fillRect(x, y, 1 + R() * w * 0.45, 1 + R() * w * 0.45);
      }
    }
  };
  const circle = (cx, cy, r, w) => {
    const pts = [];
    for (let i = 0; i <= 48; i++) {
      const a = (i / 48) * TAU + 0.2;
      pts.push([cx + Math.cos(a) * r * (1 + (R() - 0.5) * 0.04), cy + Math.sin(a) * r * (1 + (R() - 0.5) * 0.04)]);
    }
    stroke(pts, w);
  };
  const hand = (cx, cy, ang, len, w) => stroke([[cx, cy], [cx + Math.sin(ang) * len, cy - Math.cos(ang) * len]], w);
  const arrow = (cx, cy, dx, dy, len, w) => {
    const ex = cx + dx * len, ey = cy + dy * len;
    stroke([[cx - dx * len, cy - dy * len], [ex, ey]], w);
    const a = Math.atan2(dy, dx);
    stroke([[ex, ey], [ex - Math.cos(a - 0.6) * len * 0.45, ey - Math.sin(a - 0.6) * len * 0.45]], w);
    stroke([[ex, ey], [ex - Math.cos(a + 0.6) * len * 0.45, ey - Math.sin(a + 0.6) * len * 0.45]], w);
  };
  const clock = (cx, cy, r, w) => {
    circle(cx, cy, r, w);
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * TAU;
      stroke([[cx + Math.sin(a) * r * 0.78, cy - Math.cos(a) * r * 0.78], [cx + Math.sin(a) * r * 0.9, cy - Math.cos(a) * r * 0.9]], w * 0.6);
    }
    // 3:07 -> hour hand 93.5deg, minute hand 42deg
    hand(cx, cy, (((hh % 12) * 30 + mm * 0.5) * Math.PI) / 180, r * 0.48, w);
    hand(cx, cy, ((mm * 6) * Math.PI) / 180, r * 0.72, w * 0.8);
  };
  draw({ g, stroke, circle, arrow, clock, size, R });
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

export function chalkDecal(tex, w, h) {
  const m = mat(C.chalk, { map: tex, transparent: true, emissive: 0x8a1016, emissiveIntensity: 0.5, emissiveMap: tex, depthWrite: false, polygonOffset: true, unique: true });
  m.color.set(0xffffff);
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
}

// ---------------------------------------------------------------- cobble texture
function cobbleTexture() {
  const c = document.createElement('canvas');
  c.width = c.height = 512;
  const g = c.getContext('2d');
  g.fillStyle = '#8f7d62';
  g.fillRect(0, 0, 512, 512);
  const R = rng(42);
  const rows = 14;
  for (let r = 0; r < rows; r++) {
    const y = (r / rows) * 512;
    let x = (r % 2) * 18 - 18;
    while (x < 512) {
      const w = 26 + R() * 22;
      const v = 150 + R() * 45;
      g.fillStyle = `rgb(${v + 22},${v + 8},${v - 18})`;
      const rr = 7;
      const h = 512 / rows - 4;
      g.beginPath();
      g.roundRect(x + 2, y + 2, w - 4, h, rr);
      g.fill();
      g.fillStyle = 'rgba(255,240,210,0.12)';
      g.fillRect(x + 5, y + 4, w - 12, 3);
      x += w;
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(12, 12);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

// ---------------------------------------------------------------- buildings
function house({ w = 5, d = 4.5, h = 3.6, roofH = 2.0, wall = C.plaster, roof = C.roofTeal, seed = 1, lit = [] }) {
  const R = rng(seed);
  const g = new THREE.Group();
  g.add(box(w, h, d, wall, 0, h / 2, 0));
  // timber trim
  g.add(box(w + 0.06, 0.18, d + 0.06, C.wood, 0, h - 0.09, 0));
  g.add(box(w + 0.1, 0.35, d + 0.1, C.stoneDark, 0, 0.17, 0));
  const rr = prismRoof(d, w, roofH, roof);
  rr.rotation.y = Math.PI / 2;
  rr.position.y = h;
  g.add(rr);
  // door on +z face
  g.add(box(1.0, 2.0, 0.12, C.woodDark, (R() - 0.5) * (w - 2.5), 1.0, d / 2 + 0.04));
  // windows
  const wins = [];
  for (let i = 0; i < 2; i++) {
    const x = (i ? 1 : -1) * (w / 2 - 0.9);
    const win = box(0.75, 0.8, 0.1, 0x1c2a2c, x, h * 0.62, d / 2 + 0.04, { emissive: 0xffb25e, emissiveIntensity: 0, unique: true });
    g.add(win);
    g.add(box(0.95, 0.08, 0.16, C.wood, x, h * 0.62 - 0.45, d / 2 + 0.06));
    // shutters + flower box
    for (const sd of [1, -1]) g.add(box(0.32, 0.86, 0.05, roof, x + sd * 0.56, h * 0.62, d / 2 + 0.07));
    g.add(box(0.8, 0.18, 0.2, C.wood, x, h * 0.62 - 0.56, d / 2 + 0.14));
    for (let k = 0; k < 4; k++) {
      const fl = new THREE.Mesh(new THREE.IcosahedronGeometry(0.075, 0), mat([0xf2c879, 0xf1e4c8, 0x7fb0a8, 0xe9a25a][(k + i) % 4]));
      fl.position.set(x - 0.27 + k * 0.18, h * 0.62 - 0.43, d / 2 + 0.16);
      g.add(fl);
    }
    wins.push(win);
  }
  if (R() > 0.35) {
    g.add(box(0.45, 1.2, 0.45, C.stoneDark, w * 0.25, h + roofH * 0.6, -d * 0.15));
    g.userData.chimney = new THREE.Vector3(w * 0.25, h + roofH * 0.6 + 0.65, -d * 0.15);
  }
  g.userData.windows = wins;
  return g;
}

export function buildWorld(scene) {
  const W = { scene, decals: [], windows: [], lights: {} };
  const R = rng(7);

  // ------------------------------------------------ sky dome
  const skyU = {
    top: { value: new THREE.Color() }, horizon: { value: new THREE.Color() }, fogC: { value: new THREE.Color() },
    sunColor: { value: new THREE.Color() }, sunDir: { value: new THREE.Vector3(-0.25, 0.14, -1).normalize() },
    sunInt: { value: 1 }, time: shared.uTime, fogAmt: { value: 0.5 }, stars: { value: 0 },
  };
  const sky = new THREE.Mesh(
    new THREE.SphereGeometry(450, 32, 18),
    new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, depthTest: true, fog: false, uniforms: skyU,
      vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); vec4 p = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position = p.xyww; }`,
      fragmentShader: `uniform vec3 top, horizon, fogC, sunColor, sunDir; uniform float sunInt, time, fogAmt, stars; varying vec3 vDir;
        float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
        float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
          return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
        void main(){ vec3 d = normalize(vDir); float h = d.y;
          vec3 col = mix(horizon, top, smoothstep(-0.02, 0.6, h));
          float s = max(dot(d, sunDir), 0.0);
          // wispy cloud bands lit by the sun
          vec2 cp = d.xz / max(h + 0.18, 0.05) * 1.4 + vec2(time*0.01, 0.0);
          float cl = smoothstep(0.55, 0.85, noise(cp) * 0.65 + noise(cp * 2.7) * 0.35) * smoothstep(0.0, 0.2, h);
          col = mix(col, mix(top * 1.4, sunColor * 1.2, pow(s, 3.0)), cl * 0.45);
          col += sunColor * (pow(s, 1400.0) * 40.0 + pow(s, 18.0) * 0.9 + pow(s, 3.0) * 0.25) * sunInt;
          if (stars > 0.01) {
            vec2 sp = d.xz / max(d.y + 0.35, 0.05) * 160.0;
            float st = step(0.9965, hash(floor(sp))) * smoothstep(0.05, 0.3, h);
            float tw = 0.6 + 0.4 * sin(time * 3.0 + hash(floor(sp) + 3.0) * 40.0);
            col += vec3(0.85, 0.9, 1.0) * st * tw * stars * 1.6;
          }
          col = mix(col, fogC, smoothstep(0.22, -0.02, h) * fogAmt);
          gl_FragColor = vec4(col, 1.0); }`,
    })
  );
  sky.renderOrder = 10; // drawn after opaque geometry: only visible sky pixels get shaded
  sky.frustumCulled = false;
  scene.add(sky);
  W.sky = sky;
  W.skyU = skyU;

  // ------------------------------------------------ ground, square, road
  const groundGeo = new THREE.PlaneGeometry(320, 320, 90, 90);
  groundGeo.rotateX(-Math.PI / 2);
  const pos = groundGeo.attributes.position;
  const col = new Float32Array(pos.count * 3);
  const base = new THREE.Color(C.earth), grass = new THREE.Color(C.grass), tmp = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    const d = Math.hypot(x, z + 6);
    const hill = Math.max(0, d - 42) * 0.12 * (0.6 + 0.4 * Math.sin(x * 0.05) * Math.cos(z * 0.04));
    pos.setY(i, hill + (d > 16 ? (R() - 0.5) * 0.12 : -0.02));
    tmp.copy(base).lerp(grass, Math.min(1, Math.max(0, (d - 14) / 14)) * (0.5 + R() * 0.3));
    tmp.multiplyScalar(0.9 + R() * 0.15);
    col.set([tmp.r, tmp.g, tmp.b], i * 3);
  }
  groundGeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  groundGeo.computeVertexNormals();
  const groundMat = mat(0xffffff, { unique: true, detail: 5 });
  groundMat.vertexColors = true;
  scene.add(new THREE.Mesh(groundGeo, groundMat));

  const sq = new THREE.Mesh(new THREE.CircleGeometry(13.5, 48), mat(0xffffff, { map: cobbleTexture(), unique: true, flat: false }));
  sq.rotation.x = -Math.PI / 2;
  sq.position.y = 0.02;
  scene.add(sq);

  const roadPts = [[6, -1.0], [18, -2.5], [28, -4], [34, -16], [27, -31], [8, -38], [-14, -36], [-30, -24], [-34, -6], [-27, 5], [-14, 2.5], [-6, 1.2]]
    .map(([x, z]) => new THREE.Vector3(x, 0, z));
  const curve = new THREE.CatmullRomCurve3(roadPts, false, 'catmullrom', 0.5);
  W.roadCurve = curve;
  {
    const N = 260, wdt = 1.7;
    const verts = [], idx = [];
    for (let i = 0; i <= N; i++) {
      const p = curve.getPoint(i / N), tg = curve.getTangent(i / N);
      const n = new THREE.Vector3(-tg.z, 0, tg.x).normalize();
      const y = 0.035 + Math.max(0, Math.hypot(p.x, p.z + 6) - 42) * 0.12 * 0.6;
      verts.push(p.x + n.x * wdt, y, p.z + n.z * wdt, p.x - n.x * wdt, y, p.z - n.z * wdt);
      if (i < N) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
    }
    const rg = new THREE.BufferGeometry();
    rg.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    rg.setIndex(idx);
    rg.computeVertexNormals();
    const road = new THREE.Mesh(rg, mat(C.road, { side: THREE.DoubleSide }));
    scene.add(road);
    // fence posts + lanterns along the road
    for (let i = 0; i < 70; i++) {
      const u = i / 70;
      const p = curve.getPoint(u), tg = curve.getTangent(u);
      const n = new THREE.Vector3(-tg.z, 0, tg.x).normalize();
      const sd = i % 2 ? 1 : -1;
      if (Math.hypot(p.x, p.z) < 15) continue;
      const post = box(0.12, 0.9, 0.12, C.wood, p.x + n.x * 2.4 * sd, 0.45, p.z + n.z * 2.4 * sd);
      scene.add(post);
    }
  }

  // ------------------------------------------------ well (origin)
  {
    const well = new THREE.Group();
    const ring = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.18, 0.9, 12), mat(C.stone));
    ring.position.y = 0.45;
    const water = new THREE.Mesh(new THREE.CircleGeometry(0.92, 12), mat(0x0f2a30));
    water.rotation.x = -Math.PI / 2; water.position.y = 0.88;
    const lip = new THREE.Mesh(new THREE.TorusGeometry(1.08, 0.08, 4, 12), mat(C.stoneDark));
    lip.rotation.x = Math.PI / 2; lip.position.y = 0.92;
    well.add(ring, water, lip);
    for (const sd of [1, -1]) well.add(box(0.14, 2.2, 0.14, C.wood, 0, 1.4, 0.95 * sd));
    well.add(box(0.1, 0.1, 2.1, C.wood, 0, 2.35, 0));
    const roof = prismRoof(1.2, 2.4, 0.7, C.roofThatch, 0.15);
    roof.position.y = 2.42;
    roof.rotation.y = Math.PI / 2;
    well.add(roof);
    const bucket = new THREE.Group();
    bucket.add(new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.13, 0.24, 8), mat(C.wood)));
    const rope = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.008, 2.0, 3), mat(0xcdbb95));
    rope.position.y = 1.1;
    bucket.add(rope);
    bucket.position.set(0, 1.2, 0);
    well.add(bucket);
    W.wellBucket = bucket;
    scene.add(well);
    const d = chalkDecal(chalkCanvas(({ arrow, clock }) => { clock(128, 92, 52, 7); arrow(128, 196, 0, -1, 30, 7); }), 0.36, 0.36);
    d.scale.setScalar(1.35);
    d.position.set(0, 0.5, 1.13);
    scene.add(d);
    W.decals.push(d);
  }

  // ------------------------------------------------ clock tower (0,0,-24)
  {
    const T = new THREE.Group();
    T.position.set(0, 0, -24);
    T.add(box(5, 16, 5, C.stone, 0, 8, 0));
    T.add(box(5.4, 0.5, 5.4, C.stoneDark, 0, 0.25, 0));
    T.add(box(5.3, 0.35, 5.3, C.stoneDark, 0, 9.5, 0));
    T.add(box(5.5, 0.5, 5.5, C.stoneDark, 0, 16.1, 0));
    for (const [x, z] of [[2.2, 2.2], [-2.2, 2.2], [2.2, -2.2], [-2.2, -2.2]]) T.add(box(0.6, 3.6, 0.6, C.stone, x, 18.1, z));
    T.add(box(5.5, 0.45, 5.5, C.stoneDark, 0, 20.0, 0));
    const roof = new THREE.Mesh(new THREE.ConeGeometry(4.2, 5.0, 4), mat(C.roofTeal));
    roof.rotation.y = Math.PI / 4;
    roof.position.y = 22.7;
    T.add(roof);
    // clock face stopped at 3:07
    const face = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 1.35, 0.15, 24), mat(C.cream));
    face.rotation.x = Math.PI / 2;
    face.position.set(0, 12.2, 2.53);
    T.add(face);
    { const rim = new THREE.Mesh(new THREE.TorusGeometry(1.38, 0.1, 4, 24), mat(C.woodDark)); rim.position.set(0, 12.2, 2.58); T.add(rim); }
    const hand = (ang, len, wdt) => {
      const g = new THREE.Group();
      const m = box(wdt, len, 0.05, 0x1c1c1c, 0, len / 2, 0);
      g.add(m);
      g.position.set(0, 12.2, 2.64);
      g.rotation.z = -ang;
      T.add(g);
    };
    hand((93.5 * Math.PI) / 180, 0.75, 0.1);
    hand((42 * Math.PI) / 180, 1.1, 0.07);
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * TAU;
      T.add(box(0.06, 0.18, 0.04, 0x2a2a2a, Math.sin(a) * 1.15, 12.2 + Math.cos(a) * 1.15, 2.62));
    }
    // bell
    const pivot = new THREE.Group();
    pivot.position.set(0, 19.5, 0);
    const prof = [[0.02, 0], [0.3, 0], [0.42, -0.12], [0.5, -0.45], [0.62, -0.85], [0.86, -1.18], [0.9, -1.25], [0.02, -1.25]]
      .map(([r, y]) => new THREE.Vector2(r, y));
    const bell = new THREE.Mesh(new THREE.LatheGeometry(prof, 14), mat(C.bronze, { side: THREE.DoubleSide, emissive: 0x2a1a08, emissiveIntensity: 0.6 }));
    bell.position.y = -0.15;
    pivot.add(bell);
    const clapper = new THREE.Mesh(new THREE.IcosahedronGeometry(0.15, 0), mat(C.iron));
    clapper.position.y = -1.25;
    pivot.add(clapper);
    pivot.add(box(0.3, 0.3, 3.8, C.woodDark, 0, 0.05, 0));
    T.add(pivot);
    W.bellPivot = pivot;
    // door (front face z=+2.5 -> world z=-21.5)
    T.add(box(2.2, 3.1, 0.2, C.stoneWarm, 0, 1.55, 2.5));
    const recess = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 2.6), new THREE.MeshBasicMaterial({ color: 0x050b0d }));
    recess.position.set(0, 1.3, 2.61);
    T.add(recess);
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 2.5), new THREE.MeshBasicMaterial({ color: 0x5f8a95, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }));
    glow.position.set(0, 1.3, 2.615);
    T.add(glow);
    W.towerGlow = glow;
    const hinge = new THREE.Group();
    hinge.position.set(-0.8, 0, 2.66);
    const door = box(1.6, 2.6, 0.1, 0x7a5638, 0.8, 1.3, 0);
    hinge.add(door);
    for (const y of [0.5, 1.3, 2.1]) hinge.add(box(1.62, 0.08, 0.12, C.iron, 0.8, y, 0.01));
    // padlock
    const lock = new THREE.Group();
    lock.add(box(0.16, 0.18, 0.08, 0x3a3630, 0, 0, 0));
    const shackle = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.015, 4, 10, Math.PI), mat(0x4a4640));
    shackle.position.y = 0.09;
    lock.add(shackle);
    lock.add(box(0.03, 0.05, 0.02, 0x111111, 0, -0.02, 0.045));
    lock.position.set(0.8, 1.34, 0.1);
    hinge.add(lock);
    // carved handwriting groove (subtle; the line-draw overlay renders the text)
    hinge.add(box(1.0, 0.3, 0.015, 0x6a4a30, 0.8, 0.86, 0.055));
    T.add(hinge);
    W.towerDoor = hinge;
    // lantern beside the forbidden door
    T.add(box(0.08, 0.08, 0.5, C.iron, 1.45, 2.55, 2.85));
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.34, 0.24), new THREE.MeshBasicMaterial({ color: 0xffc27a }));
    lamp.position.set(1.45, 2.3, 3.05); // world (1.45, 2.3, -20.95)
    T.add(lamp);
    T.add(box(0.3, 0.06, 0.3, C.iron, 1.45, 2.5, 3.05));
    const tl = new THREE.PointLight(0xffb46a, 6, 10, 2);
    tl.position.set(1.0, 2.1, 3.6);
    T.add(tl);
    W.towerLight = tl;
    W.towerLamp = lamp;
    scene.add(T);
    W.tower = T;
  }

  // ------------------------------------------------ bakery (-10,0,-5) facing +x
  {
    const B = house({ w: 5, d: 6, h: 4.2, roofH: 2.2, wall: C.stoneWarm, roof: C.roofThatch, seed: 3 });
    B.rotation.y = Math.PI / 2;
    B.position.set(-10, 0, -5);
    B.traverse((o) => { if (o.isMesh && Math.abs(o.position.z - 3.04) < 0.02 && o.geometry.parameters?.width === 1.0) o.visible = false; });
    scene.add(B);
    W.windows.push(...B.userData.windows);
    // bakery door + awning + sign
    scene.add(box(0.12, 2.1, 1.1, C.woodDark, -6.96, 1.35, -5));
    const aw = box(1.2, 0.08, 2.4, 0xb98a4c, -6.4, 2.7, -5);
    aw.rotation.z = -0.25;
    scene.add(aw);
    const sign = box(0.08, 0.5, 1.2, C.wood, -6.9, 3.25, -5);
    scene.add(sign);
    const loaf = new THREE.Mesh(new THREE.CapsuleGeometry(0.12, 0.4, 3, 8), mat(0xd29a52));
    loaf.rotation.x = Math.PI / 2;
    loaf.position.set(-6.82, 3.25, -5);
    scene.add(loaf);
    // the creaking step(s)
    scene.add(box(0.5, 0.3, 1.4, C.woodDark, -6.75, 0.15, -5));
    const step = box(0.42, 0.14, 1.3, C.wood, -6.3, 0.07, -5);
    scene.add(step);
    W.creakStep = step;
    // crates & barrels
    for (let i = 0; i < 3; i++) scene.add(box(0.6, 0.6, 0.6, C.wood, -6.7, 0.3 + (i === 2 ? 0.6 : 0), -2.0 - (i % 2) * 0.65));
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.9, 9), mat(C.wood));
    barrel.position.set(-6.6, 0.45, -7.6);
    scene.add(barrel);
    const d = chalkDecal(chalkCanvas(({ arrow, clock }) => { clock(90, 128, 46, 7); arrow(185, 128, 1, 0, 40, 8); }), 0.6, 0.6);
    d.scale.setScalar(1.3);
    d.position.set(-6.98, 1.62, -3.0);
    d.rotation.y = Math.PI / 2;
    scene.add(d);
    W.decals.push(d);
  }

  // ------------------------------------------------ mill (13,0,-12)
  {
    const M = new THREE.Group();
    M.position.set(13, 0, -12);
    const tower = new THREE.Mesh(new THREE.CylinderGeometry(2.1, 2.5, 7, 8), mat(C.plaster));
    tower.position.y = 3.5;
    tower.rotation.y = Math.PI / 8;
    M.add(tower);
    const cap = new THREE.Mesh(new THREE.ConeGeometry(2.6, 2.6, 8), mat(C.roofSlate));
    cap.position.y = 8.3;
    cap.rotation.y = Math.PI / 8;
    M.add(cap);
    M.add(box(1.0, 1.9, 0.2, C.woodDark, 0, 0.95, 2.4));
    const hub = new THREE.Group();
    hub.position.set(0, 6.0, 2.55);
    for (let i = 0; i < 4; i++) {
      const arm = new THREE.Group();
      arm.rotation.z = (i / 4) * TAU;
      arm.add(box(0.12, 3.8, 0.1, C.wood, 0, 2.0, 0));
      arm.add(box(0.7, 3.0, 0.04, 0xe9dcc0, 0.42, 2.3, 0.04));
      hub.add(arm);
    }
    hub.add(box(0.4, 0.4, 0.4, C.woodDark));
    M.add(hub);
    W.millHub = hub;
    scene.add(M);
    const d = chalkDecal(chalkCanvas(({ arrow, clock }) => { clock(160, 128, 46, 7); arrow(64, 128, -1, 0, 40, 8); }), 0.6, 0.6);
    d.scale.setScalar(1.3);
    d.position.set(10.77, 1.62, -12);
    d.rotation.y = -Math.PI / 2;
    scene.add(d);
    W.decals.push(d);
  }

  // ------------------------------------------------ Wren's house: hollow, two rooms (x 11..21, z 4..12)
  {
    const H = new THREE.Group();
    const wallC = C.plaster, t = 0.3, h = 4;
    const add = (m) => (H.add(m), m);
    // north wall (z=4)
    add(box(10.3, h, t, wallC, 16, h / 2, 4));
    // east wall
    add(box(t, h, 8.3, wallC, 21, h / 2, 8));
    // south wall (z=12) with windows at x 12.9..14.1 and 17.9..19.1, sill 1.0, top 2.2
    add(box(1.9, h, t, wallC, 11.95, h / 2, 12));
    add(box(3.8, h, t, wallC, 16, h / 2, 12));
    add(box(1.9, h, t, wallC, 20.05, h / 2, 12));
    for (const cx of [13.5, 18.5]) {
      add(box(1.2, 1.0, t, wallC, cx, 0.5, 12));
      add(box(1.2, h - 2.2, t, wallC, cx, 2.2 + (h - 2.2) / 2, 12));
      add(box(1.3, 0.08, 0.5, C.wood, cx, 1.02, 12));
      add(box(0.06, 1.2, 0.06, C.wood, cx, 1.6, 12));
      add(box(1.2, 0.06, 0.06, C.wood, cx, 1.6, 12));
    }
    // west/front wall (x=11) with door gap z 7.3..8.7, height 2.4
    add(box(t, h, 3.3, wallC, 11, h / 2, 5.65));
    add(box(t, h, 3.3, wallC, 11, h / 2, 10.35));
    add(box(t, h - 2.4, 1.4, wallC, 11, 2.4 + (h - 2.4) / 2, 8));
    // closed front door, outer face at x~10.82
    add(box(0.1, 2.4, 1.4, C.woodDark, 10.86, 1.2, 8));
    add(box(0.04, 0.1, 1.3, C.iron, 10.8, 0.6, 8));
    add(box(0.04, 0.1, 1.3, C.iron, 10.8, 1.9, 8));
    add(box(0.06, 0.12, 0.06, 0x8a7a50, 10.78, 1.15, 7.45));
    // trim + roof
    add(box(10.5, 0.2, 8.5, C.wood, 16, h, 8));
    const roof = prismRoof(8.3, 10.3, 2.6, C.roofTeal, 0.4);
    roof.position.set(16, h, 8);
    roof.rotation.y = Math.PI / 2;
    add(roof);
    add(box(0.5, 1.6, 0.5, C.stoneDark, 12.4, h + 1.6, 5.2));
    // partition x=16 with doorway z 7.5..8.5
    add(box(0.2, h, 3.5, 0xe2d2b2, 16, h / 2, 5.75));
    add(box(0.2, h, 3.5, 0xe2d2b2, 16, h / 2, 10.25));
    add(box(0.2, h - 2.3, 1.0, 0xe2d2b2, 16, 2.3 + (h - 2.3) / 2, 8));
    // floor + ceiling beams
    add(box(9.6, 0.06, 7.6, 0x7b5a3e, 16, 0.03, 8));
    const ceil = box(9.6, 0.08, 7.6, 0x5c4330, 16, h - 0.05, 8);
    add(ceil);
    for (let i = 0; i < 5; i++) add(box(0.18, 0.2, 7.6, C.woodDark, 12 + i * 2, h - 0.2, 8));
    // kitchen: table, bowls, bread, hearth, shelves
    add(box(1.7, 0.08, 0.95, C.wood, 13.3, 0.78, 10.55));
    for (const [x, z] of [[12.55, 10.15], [14.05, 10.15], [12.55, 10.95], [14.05, 10.95]]) add(box(0.08, 0.76, 0.08, C.woodDark, x, 0.38, z));
    const bowl = new THREE.Mesh(new THREE.SphereGeometry(0.14, 8, 5, 0, TAU, Math.PI / 2, Math.PI / 2), mat(C.cream, { side: THREE.DoubleSide }));
    bowl.position.set(13.6, 0.95, 10.4);
    add(bowl);
    const porr = new THREE.Mesh(new THREE.CircleGeometry(0.12, 8), mat(0xe8cf9a));
    porr.rotation.x = -Math.PI / 2; porr.position.set(13.6, 0.91, 10.4);
    add(porr);
    const bread = new THREE.Mesh(new THREE.CapsuleGeometry(0.08, 0.22, 3, 7), mat(0xc58a44));
    bread.rotation.z = Math.PI / 2; bread.position.set(12.9, 0.9, 10.7);
    add(bread);
    add(box(0.35, 0.45, 0.35, C.wood, 14.3, 0.22, 9.6));
    add(box(1.8, 1.5, 0.7, C.stoneDark, 12.6, 0.75, 4.5));
    const fire = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.5, 0.3), new THREE.MeshBasicMaterial({ color: 0xff9440 }));
    fire.position.set(12.6, 0.45, 4.85);
    add(fire);
    W.fire = fire;
    add(box(1.6, 0.06, 0.35, C.wood, 14.6, 2.1, 4.35));
    for (let i = 0; i < 4; i++) {
      const jar = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.1, 0.22 + (i % 2) * 0.1, 7), mat(i % 2 ? 0xb07a48 : 0xd9c7a3));
      jar.position.set(14.0 + i * 0.38, 2.25, 4.35);
      add(jar);
    }
    // bedroom: bed along x (18.9..20.9) at z 9.6, window at x 18.5
    add(box(2.0, 0.35, 1.15, C.woodDark, 19.9, 0.25, 9.6));
    add(box(1.95, 0.16, 1.08, C.cream, 19.9, 0.5, 9.6));
    add(box(1.25, 0.1, 1.12, 0x2f5a5d, 19.55, 0.6, 9.6));
    add(box(0.45, 0.12, 0.75, 0xf3ead6, 20.6, 0.62, 9.6));
    add(box(0.12, 1.0, 1.15, C.woodDark, 20.92, 0.6, 9.6));
    add(box(0.6, 0.5, 0.45, C.wood, 20.6, 0.25, 11.4));
    const rug = new THREE.Mesh(new THREE.CircleGeometry(0.9, 10), mat(0x8a5a3a));
    rug.rotation.x = -Math.PI / 2; rug.position.set(18.2, 0.07, 8.6);
    add(rug);
    const candle = new THREE.Group();
    candle.add(box(0.06, 0.16, 0.06, C.cream, 0, 0.08, 0));
    const flame = new THREE.Mesh(new THREE.ConeGeometry(0.025, 0.07, 5), new THREE.MeshBasicMaterial({ color: 0xffc070 }));
    flame.position.y = 0.2;
    candle.add(flame);
    candle.position.set(18.95, 1.06, 11.85);
    add(candle);
    W.candle = candle;
    scene.add(H);
    W.house = H;

    // interior lights (short range)
    const L = (c, i, d, x, y, z) => { const l = new THREE.PointLight(c, i, d, 2); l.position.set(x, y, z); scene.add(l); return l; };
    W.lights.kitchen = L(0xffb36b, 0, 9, 13.4, 2.9, 8.0);
    W.lights.hearth = L(0xff8a3c, 0, 6, 12.6, 0.9, 5.2);
    W.lights.bedroom = L(0xffd2a0, 0, 7, 18.0, 2.9, 8.2);
    W.lights.candle = L(0xffb060, 0, 5, 18.9, 1.35, 11.6);
    // fake volumetric light shafts through the windows
    const shaftMat = new THREE.MeshBasicMaterial({ color: 0xffd39a, transparent: true, opacity: 0.0, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    W.shafts = [];
    for (const cx of [13.5, 18.5]) {
      const g = new THREE.CylinderGeometry(0.55, 1.1, 3.6, 4, 1, true);
      const s = new THREE.Mesh(g, shaftMat.clone());
      s.position.set(cx - 0.3, 0.9, 10.6);
      s.rotation.set(0.9, Math.PI / 4, 0.25);
      scene.add(s);
      W.shafts.push(s);
    }
    const d = chalkDecal(chalkCanvas(({ arrow, clock }) => { clock(128, 104, 66, 8); arrow(128, 212, -1, 0, 30, 7); }), 0.46, 0.46);
    d.position.set(10.8, 1.5, 8.0);
    d.rotation.y = -Math.PI / 2;
    scene.add(d);
    W.decals.push(d);
    W.doorDecal = d;
    W.makeDoorClock = (time) => chalkCanvas(({ arrow, clock }) => { clock(128, 104, 66, 8); arrow(128, 212, -1, 0, 30, 7); }, 256, time);
    W.chimneys = [new THREE.Vector3(12.4, 6.4, 5.2)];
  }

  // ------------------------------------------------ village houses
  const houses = [
    [-15.5, 8.5, 5, 4.5, 3.6, C.roofTeal], [-7.5, 16, 5.5, 4.5, 3.8, C.roofThatch], [3, 18, 5, 4.2, 3.4, C.roofSlate],
    [-17, -13, 5, 5, 4, C.roofTeal], [8.5, -20, 4.5, 4, 3.4, C.roofThatch], [-8.8, -19.5, 4.5, 4.5, 3.6, C.roofSlate],
    [22.5, -9, 5, 4.5, 3.6, C.roofTeal], [-23, 15, 5, 4.5, 3.5, C.roofThatch], [11, 20, 5, 4.5, 3.8, C.roofTeal],
    [-23, -5, 4.5, 4.5, 3.4, C.roofSlate], [24, 14, 5, 4.5, 3.6, C.roofThatch], [-2, -32, 6, 5, 4, C.roofTeal],
  ];
  houses.forEach(([x, z, w, d, h, roof], i) => {
    const g = house({ w, d, h, roof, seed: 10 + i, wall: i % 3 === 0 ? C.stoneWarm : C.plaster });
    g.position.set(x, 0, z);
    g.rotation.y = Math.atan2(-x, -z) + (R() - 0.5) * 0.25;
    scene.add(g);
    W.windows.push(...g.userData.windows);
    if (g.userData.chimney) { g.updateMatrixWorld(true); W.chimneys.push(g.localToWorld(g.userData.chimney.clone())); }
  });

  // lantern posts around the square
  W.lanterns = [];
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU + 0.5;
    const x = Math.cos(a) * 12.4, z = Math.sin(a) * 12.4;
    scene.add(box(0.12, 2.6, 0.12, C.iron, x, 1.3, z));
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.32, 0.26), mat(0x2b2b28, { emissive: 0xffb25e, emissiveIntensity: 0, unique: true }));
    lamp.position.set(x, 2.75, z);
    scene.add(lamp);
    W.lanterns.push(lamp);
  }

  // ------------------------------------------------ trees (instanced) + hills
  {
    const cone = new THREE.ConeGeometry(1.4, 4.2, 6);
    cone.translate(0, 3.4, 0);
    const trunk = new THREE.CylinderGeometry(0.18, 0.24, 1.6, 5);
    trunk.translate(0, 0.8, 0);
    const N = 170;
    const im = new THREE.InstancedMesh(cone, mat(C.tree), N);
    const it = new THREE.InstancedMesh(trunk, mat(C.trunk), N);
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), p = new THREE.Vector3();
    const samples = Array.from({ length: 200 }, (_, i) => curve.getPoint(i / 199));
    let n = 0, guard = 0;
    while (n < N && guard++ < 5000) {
      const a = R() * TAU, r = 25 + R() * 55;
      const x = Math.cos(a) * r, z = Math.sin(a) * r - 6;
      if (samples.some((s) => Math.hypot(s.x - x, s.z - z) < 3.4)) continue;
      if (Math.abs(x) < 6 && z < -20 && z > -30) continue;
      const y = Math.max(0, Math.hypot(x, z + 6) - 42) * 0.12 * 0.6;
      const s = 0.7 + R() * 0.8;
      p.set(x, y - 0.1, z); q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), R() * TAU); sc.set(s, s * (0.85 + R() * 0.4), s);
      m4.compose(p, q, sc);
      im.setMatrixAt(n, m4);
      it.setMatrixAt(n, m4);
      n++;
    }
    im.count = it.count = n;
    scene.add(im, it);
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * TAU, r = 120 + R() * 40;
      const hill = new THREE.Mesh(new THREE.ConeGeometry(30 + R() * 25, 18 + R() * 20, 5), mat(C.treeDark));
      hill.position.set(Math.cos(a) * r, 0, Math.sin(a) * r);
      scene.add(hill);
    }
  }

  // ------------------------------------------------ rain (shader-driven, can freeze mid-air)
  {
    const N = 2200;
    const pos = new Float32Array(N * 2 * 3), end = new Float32Array(N * 2);
    for (let i = 0; i < N; i++) {
      const x = (R() - 0.5) * 30, y = R() * 10, z = (R() - 0.5) * 26 + 1;
      pos.set([x, y, z, x, y, z], i * 6);
      end[i * 2] = 0; end[i * 2 + 1] = 1;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('aEnd', new THREE.BufferAttribute(end, 1));
    const rainU = { uFall: { value: 0 }, uLen: { value: 0.05 }, uAlpha: { value: 0 }, uTime: shared.uTime };
    const rain = new THREE.LineSegments(g, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, uniforms: rainU,
      vertexShader: `attribute float aEnd; uniform float uFall, uLen, uTime; varying float vA;
        void main(){ vec3 p = position; float y = mod(p.y - uFall * 11.0, 10.0);
          float shimmer = (1.0 - step(0.001, uFall)) * sin(uTime * 2.0 + p.x * 3.1) * 0.004;
          p.y = y + aEnd * (uLen + 0.02) + shimmer; p.x += aEnd * uLen * 0.12; vA = 1.0 - aEnd * 0.6;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }`,
      fragmentShader: `uniform float uAlpha; varying float vA; void main(){ gl_FragColor = vec4(0.86, 0.9, 0.92, uAlpha * vA); }`,
    }));
    rain.frustumCulled = false;
    rain.visible = false;
    scene.add(rain);
    W.rain = rain;
    W.rainU = rainU;
  }

  // ------------------------------------------------ dust motes in the light
  {
    const N = 900;
    const p = new Float32Array(N * 3), ph = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      p.set([(R() - 0.5) * 40, R() * 6, (R() - 0.5) * 50 - 6], i * 3);
      ph[i] = R() * 100;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    g.setAttribute('aPh', new THREE.BufferAttribute(ph, 1));
    const U = { uTime: shared.uTime, uAmt: { value: 0.6 }, uColor: { value: new THREE.Color(0xffd9a0) }, uScale: { value: 900 } };
    const motes = new THREE.Points(g, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, uniforms: U,
      vertexShader: `attribute float aPh; uniform float uTime, uScale; varying float vF;
        void main(){ vec3 q = position + vec3(sin(uTime*0.13+aPh)*0.6, sin(uTime*0.09+aPh*1.7)*0.4, cos(uTime*0.11+aPh)*0.6);
          vec4 mv = modelViewMatrix * vec4(q,1.0); gl_Position = projectionMatrix * mv;
          gl_PointSize = clamp(uScale * 0.03 / -mv.z, 1.0, 7.0); vF = smoothstep(30.0, 2.0, -mv.z) * (0.5 + 0.5*sin(uTime*0.7+aPh*3.0)); }`,
      fragmentShader: `uniform vec3 uColor; uniform float uAmt; varying float vF;
        void main(){ vec2 c = gl_PointCoord - 0.5; float d = smoothstep(0.5, 0.0, length(c)); gl_FragColor = vec4(uColor * d * vF * uAmt, 1.0); }`,
    }));
    motes.frustumCulled = false;
    scene.add(motes);
    W.motes = motes;
    W.motesU = U;
  }

  buildExtras(W, scene);
  return W;
}
