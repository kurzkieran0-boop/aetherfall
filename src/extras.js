// Part 2 art pass + sets: grass & flowers, chimney smoke, birds, the trapdoor behind the
// mill, and the chalk-clock cellar (built 30 m underground at x=60 so it never intersects the village).
import * as THREE from 'three';
import { mat, rng, C, shared } from './materials.js';
import { chalkCanvas, chalkDecal } from './world.js';

const TAU = Math.PI * 2;
export const CELLAR = new THREE.Vector3(60, -30, 0);

function box(w, h, d, color, x = 0, y = 0, z = 0, opts) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(color, opts));
  m.position.set(x, y, z);
  return m;
}

export function buildExtras(W, scene) {
  const R = rng(321);
  const roadPts = Array.from({ length: 160 }, (_, i) => W.roadCurve.getPoint(i / 159));
  const blocked = [[0, -24, 4], [-10, -5, 4.2], [13, -12, 3.2], [16, 8, 6.2], [15, -15.8, 1.4]];
  const free = (x, z) => !roadPts.some((p) => Math.hypot(p.x - x, p.z - z) < 2.3) && !blocked.some(([bx, bz, r]) => Math.hypot(bx - x, bz - z) < r);
  const groundY = (x, z) => Math.max(0, Math.hypot(x, z + 6) - 42) * 0.12 * 0.6;

  // ---------------------------------------------------------------- grass tufts + wild flowers
  {
    const blade = new THREE.ConeGeometry(0.05, 0.42, 3);
    blade.translate(0, 0.21, 0);
    const parts = [];
    for (let i = 0; i < 4; i++) {
      const b = blade.clone();
      b.rotateZ((i - 1.5) * 0.28);
      b.rotateY(i * 1.3);
      b.translate((i - 1.5) * 0.04, 0, (i % 2) * 0.04);
      parts.push(b);
    }
    const tuft = mergeGeos(parts);
    const N = 2600;
    const im = new THREE.InstancedMesh(tuft, mat(0x76834d, { flat: true }), N);
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
    let n = 0, guard = 0;
    while (n < N && guard++ < 20000) {
      const a = R() * TAU, r = 13.9 + Math.pow(R(), 1.6) * 34;
      const x = Math.cos(a) * r, z = Math.sin(a) * r;
      if (!free(x, z)) continue;
      const sc = 0.6 + R() * 0.9;
      p.set(x, groundY(x, z) - 0.02, z); q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), R() * TAU); s.set(sc, sc * (0.7 + R() * 0.7), sc);
      im.setMatrixAt(n, m4.compose(p, q, s));
      im.setColorAt(n, c.setHSL(0.19 + R() * 0.06, 0.32 + R() * 0.15, 0.3 + R() * 0.14));
      n++;
    }
    im.count = n;
    scene.add(im);
    const fl = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.06, 0), mat(0xffffff), 700);
    const cols = [0xf2c879, 0xf1e4c8, 0x9cc7c0, 0xe9a25a, 0xd8d0f0];
    n = 0; guard = 0;
    while (n < 700 && guard++ < 9000) {
      const a = R() * TAU, r = 14 + R() * 26;
      const x = Math.cos(a) * r, z = Math.sin(a) * r;
      if (!free(x, z)) continue;
      p.set(x, groundY(x, z) + 0.28 + R() * 0.12, z); s.setScalar(0.7 + R() * 0.6);
      fl.setMatrixAt(n, m4.compose(p, q.identity(), s));
      fl.setColorAt(n, c.set(cols[Math.floor(R() * cols.length)]));
      n++;
    }
    fl.count = n;
    scene.add(fl);
  }

  // ---------------------------------------------------------------- chimney smoke (shader particles)
  {
    const per = 26;
    const N = W.chimneys.length * per;
    const pos = new Float32Array(N * 3), seed = new Float32Array(N);
    W.chimneys.forEach((ch, i) => {
      for (let k = 0; k < per; k++) {
        pos.set([ch.x, ch.y, ch.z], (i * per + k) * 3);
        seed[i * per + k] = k / per + R() * 0.03;
      }
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
    const U = { uTime: shared.uTime, uColor: { value: new THREE.Color(0xd8cfc0) }, uAmt: { value: 0.5 }, uScale: { value: 900 } };
    const smoke = new THREE.Points(g, new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, uniforms: U,
      vertexShader: `attribute float aSeed; uniform float uTime, uScale; varying float vA;
        void main(){ float age = fract(uTime * 0.11 + aSeed);
          vec3 p = position + vec3(age * 2.6 + sin(age * 6.0 + aSeed * 30.0) * 0.25, age * 5.5, age * 0.8);
          vec4 mv = modelViewMatrix * vec4(p, 1.0); gl_Position = projectionMatrix * mv;
          gl_PointSize = clamp(uScale * (0.25 + age * 0.9) / -mv.z, 1.0, 140.0);
          vA = smoothstep(0.0, 0.12, age) * (1.0 - age); }`,
      fragmentShader: `uniform vec3 uColor; uniform float uAmt; varying float vA;
        void main(){ float d = length(gl_PointCoord - 0.5); float a = smoothstep(0.5, 0.0, d) * vA * uAmt * 0.45; gl_FragColor = vec4(uColor, a); }`,
    }));
    smoke.frustumCulled = false;
    scene.add(smoke);
    W.smokeU = U;
  }

  // ---------------------------------------------------------------- birds circling the tower
  {
    W.birds = [];
    const wingGeo = new THREE.BufferGeometry();
    wingGeo.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0.12, 0, 0, -0.08, 0.45, 0.02, 0], 3));
    wingGeo.computeVertexNormals();
    for (let i = 0; i < 9; i++) {
      const b = new THREE.Group();
      const body = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.3, 4), mat(0x1d2628));
      body.rotation.x = Math.PI / 2;
      const wl = new THREE.Mesh(wingGeo, mat(0x1d2628, { side: THREE.DoubleSide }));
      const wr = wl.clone(); wr.scale.x = -1;
      b.add(body, wl, wr);
      b.userData = { wl, wr, r: 9 + R() * 9, h: 20 + R() * 8, sp: 0.18 + R() * 0.12, ph: R() * TAU, flap: 7 + R() * 4 };
      scene.add(b);
      W.birds.push(b);
    }
  }

  // ---------------------------------------------------------------- trapdoor behind the mill
  {
    const T = new THREE.Group();
    T.position.set(15, 0.03, -15.8);
    T.add(box(1.5, 0.08, 1.5, C.stoneDark, 0, 0.02, 0));
    const hole = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 1.2), new THREE.MeshBasicMaterial({ color: 0x030405 }));
    hole.rotation.x = -Math.PI / 2;
    hole.position.y = 0.065;
    T.add(hole);
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(1.15, 1.15), new THREE.MeshBasicMaterial({ color: 0xffa14a, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    glow.rotation.x = -Math.PI / 2;
    glow.position.y = 0.07;
    T.add(glow);
    const hinge = new THREE.Group();
    hinge.position.set(0, 0.07, -0.6);
    const lid = box(1.2, 0.08, 1.2, 0x7a5638, 0, 0.04, 0.6);
    hinge.add(lid);
    for (const z of [0.25, 0.95]) hinge.add(box(1.22, 0.02, 0.08, C.iron, 0, 0.085, z));
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.014, 4, 10), mat(C.iron));
    ring.rotation.x = Math.PI / 2;
    ring.position.set(0, 0.09, 1.05);
    hinge.add(ring);
    const deco = chalkDecal(chalkCanvas(({ clock }) => clock(128, 128, 80, 9), 256, '3:08'), 0.72, 0.72);
    deco.rotation.x = -Math.PI / 2;
    deco.position.set(0, 0.086, 0.6);
    hinge.add(deco);
    T.add(hinge);
    T.visible = false;
    scene.add(T);
    W.hatch = T;
    W.hatchHinge = hinge;
    W.hatchGlow = glow;
  }

  // ---------------------------------------------------------------- the cellar of crossed-out clocks
  {
    const G = new THREE.Group();
    G.position.copy(CELLAR);
    const wallC = 0x9c8a70;
    G.add(box(9, 0.2, 7, 0x5a4a3a, 0, -0.1, 0));                 // floor
    G.add(box(9, 0.3, 7, 0x3a3027, 0, 3.15, 0));                 // ceiling
    G.add(box(9, 3.2, 0.3, C.stoneDark, 0, 1.6, -3.0));          // north wall (the last clock)
    G.add(box(9, 3.2, 0.3, C.stoneDark, 0, 1.6, 3.0));           // south wall
    G.add(box(0.3, 3.2, 6, C.stoneDark, -4.3, 1.6, 0));          // west
    G.add(box(0.3, 3.2, 6, C.stoneDark, 4.3, 1.6, 0));           // east
    for (let i = -3; i <= 3; i += 2) G.add(box(0.25, 0.25, 6.6, C.woodDark, i, 2.9, 0));
    // ladder up to the hatch
    for (const x of [-0.28, 0.28]) { const rail = box(0.07, 3.3, 0.07, C.wood, x, 1.6, 2.55); rail.rotation.x = -0.18; G.add(rail); }
    for (let k = 0; k < 8; k++) G.add(box(0.56, 0.05, 0.06, C.wood, 0, 0.3 + k * 0.38, 2.75 - k * 0.07));
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 1.1, 3.0, 4, 1, true), new THREE.MeshBasicMaterial({ color: 0xbfd6e0, transparent: true, opacity: 0.05, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    shaft.position.set(0, 1.7, 2.4);
    shaft.rotation.y = Math.PI / 4;
    G.add(shaft);
    // props
    G.add(box(1.4, 0.06, 0.7, C.wood, 2.6, 0.78, -1.8));
    for (const [x, z] of [[2.0, -2.05], [3.2, -2.05], [2.0, -1.55], [3.2, -1.55]]) G.add(box(0.06, 0.78, 0.06, C.woodDark, x, 0.39, z));
    for (let k = 0; k < 5; k++) {
      const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.11, 5), mat(C.chalk, { emissive: 0x5a0a0c }));
      stick.rotation.z = Math.PI / 2;
      stick.rotation.y = R() * 3;
      stick.position.set(2.3 + R() * 0.6, 0.83, -1.95 + R() * 0.3);
      G.add(stick);
    }
    for (let k = 0; k < 4; k++) G.add(box(0.6, 0.6, 0.6, C.wood, -3.4 + (k % 2) * 0.65, 0.3 + Math.floor(k / 2) * 0.6, 2.2));
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.9, 9), mat(C.wood));
    barrel.position.set(3.5, 0.45, 2.1);
    G.add(barrel);
    // candles + lantern
    const flames = [];
    for (const [x, z] of [[2.4, -1.75], [3.0, -1.7], [-3.6, -2.4], [-3.3, -2.55], [3.8, -2.5]]) {
      const y = x > 2 && z > -1.9 ? 0.81 : 0;
      G.add(box(0.06, 0.18, 0.06, C.cream, x, y + 0.09, z));
      const f = new THREE.Mesh(new THREE.ConeGeometry(0.025, 0.08, 5), new THREE.MeshBasicMaterial({ color: 0xffc070 }));
      f.position.set(x, y + 0.23, z);
      G.add(f);
      flames.push(f);
    }
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.3, 0.22), new THREE.MeshBasicMaterial({ color: 0xffc27a }));
    lamp.position.set(0.9, 2.35, -0.6);
    G.add(lamp);
    G.add(box(0.02, 0.5, 0.02, C.iron, 0.9, 2.75, -0.6));
    const L1 = new THREE.PointLight(0xffb062, 7, 10, 2); L1.position.set(0.9, 2.2, -0.6); G.add(L1);
    const L2 = new THREE.PointLight(0xff9a48, 3, 6, 2); L2.position.set(2.7, 1.2, -1.5); G.add(L2);
    const L3 = new THREE.PointLight(0x9cc4d4, 1.6, 6, 2); L3.position.set(0, 2.6, 2.3); G.add(L3);
    W.cellarLights = [L1, L2, L3];
    W.cellarFlames = flames;
    W.cellarLamp = lamp;

    // walls covered in crossed-out chalk clocks, all in Wren's hand (16 variants)
    const variants = [];
    for (let v = 0; v < 16; v++) {
      const hh = 1 + Math.floor(R() * 12), mm = Math.floor(R() * 60);
      const time = `${hh}:${String(mm).padStart(2, '0')}`;
      variants.push(chalkCanvas(({ clock, stroke, g, R: r2 }) => {
        clock(128, 120, 70 + r2() * 14, 7);
        stroke([[50, 40], [206, 200]], 9);
        stroke([[206, 40], [50, 200]], 9);
        g.globalAlpha = 0.85; g.fillStyle = 'rgb(205,38,44)';
        g.font = 'italic 30px "Homemade Apple", cursive';
        g.fillText('W', 196, 236);
      }, 256, time));
    }
    const plane = new THREE.PlaneGeometry(1, 1);
    const walls = [
      { n: new THREE.Vector3(0, 0, 1), o: new THREE.Vector3(0, 0, -2.84), u: new THREE.Vector3(1, 0, 0), half: 4.0, skipCenter: true },
      { n: new THREE.Vector3(1, 0, 0), o: new THREE.Vector3(-4.14, 0, 0), u: new THREE.Vector3(0, 0, -1), half: 2.7 },
      { n: new THREE.Vector3(-1, 0, 0), o: new THREE.Vector3(4.14, 0, 0), u: new THREE.Vector3(0, 0, 1), half: 2.7 },
      { n: new THREE.Vector3(0, 0, -1), o: new THREE.Vector3(0, 0, 2.84), u: new THREE.Vector3(-1, 0, 0), half: 4.0, skipLadder: true },
    ];
    const ims = variants.map((tex) => {
      const m = mat(C.chalk, { map: tex, transparent: true, emissive: 0x8a1016, emissiveIntensity: 0.55, emissiveMap: tex, depthWrite: false, polygonOffset: true, unique: true });
      m.color.set(0xffffff);
      const im = new THREE.InstancedMesh(plane, m, 40);
      im.count = 0;
      G.add(im);
      return im;
    });
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
    for (const w of walls) {
      const rot = new THREE.Matrix4().makeBasis(w.u, new THREE.Vector3(0, 1, 0), w.n);
      q.setFromRotationMatrix(rot);
      for (let a = -w.half + 0.35; a < w.half - 0.3; a += 0.52) {
        for (let y = 0.45; y < 2.75; y += 0.5) {
          if (w.skipCenter && Math.abs(a) < 0.85 && y > 0.6 && y < 2.4) continue;
          if (w.skipLadder && Math.abs(a) < 0.7) continue;
          const jx = (R() - 0.5) * 0.18, jy = (R() - 0.5) * 0.14;
          const sc = 0.34 + R() * 0.16;
          p.copy(w.o).addScaledVector(w.u, a + jx); p.y = y + jy;
          const qq = q.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), (R() - 0.5) * 0.4));
          const im = ims[Math.floor(R() * ims.length)];
          if (im.count >= 40) continue;
          im.setMatrixAt(im.count++, m4.compose(p, qq, s.setScalar(sc)));
        }
      }
    }
    ims.forEach((im) => { im.instanceMatrix.needsUpdate = true; });
    // the last clock: 3:08, not crossed out
    const last = chalkDecal(chalkCanvas(({ clock }) => clock(128, 128, 96, 10), 256, '3:08'), 1.05, 1.05);
    last.position.set(0, 1.75, -2.835);
    G.add(last);
    scene.add(G);
    W.cellar = G;
  }
}

function mergeGeos(geos) {
  const pos = [], nor = [];
  for (const g of geos) {
    const gg = g.index ? g.toNonIndexed() : g;
    pos.push(...gg.attributes.position.array);
    nor.push(...gg.attributes.normal.array);
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  return out;
}
