// Low-poly procedural characters + deterministic, time-driven actions.
import * as THREE from 'three';
import { mat, rng, C } from './materials.js';

const TAU = Math.PI * 2;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const easeOut = (x) => 1 - Math.pow(1 - clamp(x), 3);

function mesh(geo, color, opts) {
  const m = new THREE.Mesh(geo, mat(color, { char: true, ...opts }));
  return m;
}

// ------------------------------------------------------------------ humanoid rig
export function humanoid(o = {}) {
  const s = (o.height ?? 1.45) / 1.45;
  const legLen = 0.62, torsoH = 0.42, headR = 0.15, armLen = 0.44;
  const root = new THREE.Group();
  const body = new THREE.Group(); // scaled container
  body.scale.setScalar(s);
  root.add(body);

  const hips = new THREE.Group();
  hips.position.y = legLen;
  body.add(hips);

  const legs = [];
  for (const side of [1, -1]) {
    const leg = new THREE.Group();
    leg.position.set(0.075 * side, 0, 0);
    const lm = mesh(new THREE.CylinderGeometry(0.055, 0.045, legLen, 6), o.legs ?? 0x3a3530);
    lm.position.y = -legLen / 2;
    const shoe = mesh(new THREE.BoxGeometry(0.1, 0.07, 0.17), o.shoes ?? C.woodDark);
    shoe.position.set(0, -legLen + 0.03, 0.03);
    leg.add(lm, shoe);
    hips.add(leg);
    legs.push(leg);
  }
  const upper = new THREE.Group();
  hips.add(upper);
  const torso = mesh(new THREE.CylinderGeometry(o.chest ?? 0.13, o.waist ?? 0.17, torsoH, 7), o.top ?? 0x3f6f73);
  torso.position.y = torsoH / 2;
  upper.add(torso);
  if (o.skirt !== false) {
    const skirt = mesh(new THREE.CylinderGeometry(0.17, o.skirtR ?? 0.27, o.skirtLen ?? 0.36, 8), o.skirt ?? o.top ?? 0x3f6f73);
    skirt.position.y = -(o.skirtLen ?? 0.36) / 2 + 0.04;
    hips.add(skirt);
  }
  if (o.apron) {
    const ap = mesh(new THREE.BoxGeometry(0.22, 0.5, 0.03), o.apron);
    ap.position.set(0, 0.02, 0.155);
    ap.rotation.x = -0.06;
    upper.add(ap);
  }
  if (o.belly) {
    const b = mesh(new THREE.IcosahedronGeometry(0.19, 1), o.top);
    b.scale.set(1, 1.05, 0.95);
    b.position.set(0, 0.17, 0.05);
    upper.add(b);
  }
  if (o.scarf) {
    const sc = mesh(new THREE.TorusGeometry(0.1, 0.035, 5, 10), o.scarf);
    sc.rotation.x = Math.PI / 2;
    sc.position.y = torsoH - 0.01;
    upper.add(sc);
  }
  const arms = [];
  for (const side of [1, -1]) {
    const arm = new THREE.Group();
    arm.position.set(0.165 * side, torsoH - 0.04, 0);
    const am = mesh(new THREE.BoxGeometry(0.075, armLen, 0.075), o.sleeves ?? o.top ?? 0x3f6f73);
    am.position.y = -armLen / 2;
    const hand = mesh(new THREE.IcosahedronGeometry(0.045, 0), o.skin ?? C.skin);
    hand.position.y = -armLen - 0.02;
    arm.add(am, hand);
    arm.userData.hand = hand;
    upper.add(arm);
    arms.push(arm);
  }
  const neck = new THREE.Group();
  neck.position.y = torsoH + 0.02;
  upper.add(neck);
  const head = new THREE.Group();
  neck.add(head);
  const headM = mesh(new THREE.IcosahedronGeometry(headR, 1), o.skin ?? C.skin);
  headM.position.y = headR + 0.02;
  headM.scale.set(1, 1.08, 1);
  head.add(headM);
  const hy = headR + 0.02;
  if (o.face !== false) {
    for (const side of [1, -1]) {
      const eye = mesh(new THREE.IcosahedronGeometry(0.019, 0), 0x1b1512);
      eye.position.set(0.052 * side, hy + 0.015, headR * 0.9);
      head.add(eye);
      const brow = mesh(new THREE.BoxGeometry(0.05, 0.01, 0.01), o.hair ?? 0x3a2a20);
      brow.position.set(0.052 * side, hy + 0.06, headR * 0.92);
      brow.rotation.z = -0.12 * side;
      head.add(brow);
    }
    const nose = mesh(new THREE.ConeGeometry(0.02, 0.05, 4), o.skin ?? C.skin);
    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, hy - 0.01, headR * 1.0);
    head.add(nose);
    const cheek = 0xe9a083;
    for (const side of [1, -1]) {
      const c = mesh(new THREE.CircleGeometry(0.022, 6), cheek, { transparent: true, opacity: 0.55 });
      c.position.set(0.085 * side, hy - 0.025, headR * 0.86);
      c.rotation.y = 0.5 * side;
      head.add(c);
    }
    const mouth = mesh(new THREE.BoxGeometry(0.04, 0.008, 0.01), 0x7a3e33);
    mouth.position.set(0, hy - 0.06, headR * 0.93);
    head.add(mouth);
    head.userData.mouth = mouth;
  }
  // hair styles
  const hairC = o.hair ?? 0x4a2f22;
  if (o.hairStyle === 'bob') {
    const cap = mesh(new THREE.SphereGeometry(headR * 1.12, 10, 7, 0, TAU, 0, Math.PI * 0.5), hairC);
    cap.position.y = hy + 0.01;
    cap.rotation.x = -0.42;
    head.add(cap);
    const back = mesh(new THREE.CylinderGeometry(headR * 1.05, headR * 1.15, 0.17, 9, 1, true, Math.PI / 2 - 0.35, Math.PI + 0.7), hairC, { side: THREE.DoubleSide });
    back.position.set(0, hy - 0.05, -0.02);
    head.add(back);
    const fringe = mesh(new THREE.BoxGeometry(0.2, 0.045, 0.04), hairC);
    fringe.position.set(0, hy + 0.085, headR * 0.9);
    fringe.rotation.x = 0.35;
    head.add(fringe);
  } else if (o.hairStyle === 'bun') {
    const cap = mesh(new THREE.SphereGeometry(headR * 1.08, 10, 7, 0, TAU, 0, Math.PI * 0.55), hairC);
    cap.position.y = hy + 0.01;
    cap.rotation.x = -0.3;
    head.add(cap);
    const bun = mesh(new THREE.IcosahedronGeometry(0.075, 1), hairC);
    bun.position.set(0, hy + 0.1, -0.12);
    head.add(bun);
  } else if (o.hairStyle === 'bald') {
    const ring = mesh(new THREE.TorusGeometry(headR * 0.95, 0.03, 4, 12, Math.PI * 1.3), hairC);
    ring.rotation.set(Math.PI / 2, 0, Math.PI * -0.15 + Math.PI);
    ring.position.y = hy - 0.01;
    head.add(ring);
  } else if (o.hairStyle === 'cap') {
    const cap = mesh(new THREE.CylinderGeometry(headR * 1.05, headR * 1.1, 0.07, 9), o.capColor ?? C.wood);
    cap.position.y = hy + 0.09;
    head.add(cap);
    const brim = mesh(new THREE.BoxGeometry(0.2, 0.02, 0.1), o.capColor ?? C.wood);
    brim.position.set(0, hy + 0.06, 0.15);
    head.add(brim);
  } else if (o.hairStyle === 'toque') {
    const band = mesh(new THREE.CylinderGeometry(headR * 1.02, headR * 1.02, 0.08, 9), C.cream);
    band.position.y = hy + 0.1;
    const puff = mesh(new THREE.IcosahedronGeometry(0.17, 1), C.cream);
    puff.scale.set(1, 0.75, 1);
    puff.position.y = hy + 0.22;
    head.add(band, puff);
  } else if (o.hairStyle === 'scarf') {
    const sc = mesh(new THREE.SphereGeometry(headR * 1.15, 10, 7, 0, TAU, 0, Math.PI * 0.6), o.scarfColor ?? C.roofTeal);
    sc.position.y = hy + 0.005;
    sc.rotation.x = -0.35;
    head.add(sc);
  } else if (o.hairStyle === 'hood') {
    const hood = mesh(new THREE.ConeGeometry(0.24, 0.52, 7, 1, true), o.top, { side: THREE.DoubleSide });
    hood.position.set(0, hy + 0.06, -0.03);
    head.add(hood);
  }
  if (o.beard) {
    const b = mesh(new THREE.ConeGeometry(0.1, 0.24, 6), o.beard);
    b.rotation.x = Math.PI;
    b.position.set(0, hy - 0.13, headR * 0.6);
    head.add(b);
  }
  if (o.mustache) {
    const m = mesh(new THREE.BoxGeometry(0.11, 0.025, 0.03), o.mustache);
    m.position.set(0, hy - 0.04, headR * 0.95);
    head.add(m);
  }
  const blob = new THREE.Mesh(new THREE.CircleGeometry(0.34, 14), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28, depthWrite: false }));
  blob.rotation.x = -Math.PI / 2;
  blob.position.y = 0.015;
  root.add(blob);

  return { root, body, hips, upper, legs, arms, neck, head, s, legLen, torsoH, blob };
}

function resetPose(r) {
  r.hips.position.set(0, r.legLen, 0);
  r.hips.rotation.set(0, 0, 0);
  r.upper.rotation.set(0, 0, 0);
  r.legs.forEach((l) => l.rotation.set(0, 0, 0));
  r.arms.forEach((a) => a.rotation.set(0, 0, 0));
  r.head.rotation.set(0, 0, 0);
  r.body.position.set(0, 0, 0);
  r.body.rotation.set(0, 0, 0);
  r.blob.visible = true;
}

function breathe(r, t, k = 1) {
  r.upper.rotation.x = 0.02 * Math.sin(t * 1.6) * k;
  r.head.rotation.x = 0.03 * Math.sin(t * 0.9 + 1) * k;
  r.head.rotation.y = 0.06 * Math.sin(t * 0.43) * k;
  r.arms[0].rotation.z = 0.06; r.arms[1].rotation.z = -0.06;
}

function walk(r, t, speed = 1) {
  const ph = t * 5.4 * speed;
  r.legs[0].rotation.x = Math.sin(ph) * 0.5;
  r.legs[1].rotation.x = -Math.sin(ph) * 0.5;
  r.arms[0].rotation.x = -Math.sin(ph) * 0.4;
  r.arms[1].rotation.x = Math.sin(ph) * 0.4;
  r.arms[0].rotation.z = 0.08; r.arms[1].rotation.z = -0.08;
  r.hips.position.y = r.legLen + Math.abs(Math.cos(ph)) * 0.025;
  r.upper.rotation.y = Math.sin(ph) * 0.06;
  r.head.rotation.y = -Math.sin(ph) * 0.05;
}

// ------------------------------------------------------------------ actor factories
function tray() {
  const g = new THREE.Group();
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.035, 0.4), mat(C.wood, { char: true }));
  g.add(board);
  const loaves = [];
  const R = rng(11);
  for (let i = 0; i < 6; i++) {
    const l = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.12, 3, 7), mat(0xc58a44, { char: true }));
    l.rotation.z = Math.PI / 2;
    l.userData.home = new THREE.Vector3(-0.2 + (i % 3) * 0.2, 0.06, -0.09 + Math.floor(i / 3) * 0.18);
    l.userData.v = new THREE.Vector3((R() - 0.5) * 1.6, 0.6 + R() * 1.2, 0.4 + R() * 1.4);
    l.userData.spin = (R() - 0.5) * 14;
    l.position.copy(l.userData.home);
    loaves.push(l);
  }
  return { g, board, loaves };
}

const makers = {
  wren: () => humanoid({ height: 1.45, top: 0x3f6f73, skirt: 0x3a6266, sleeves: 0xe9dcc2, hair: 0x4a2b1e, hairStyle: 'bob', scarf: 0xefe2c6, legs: 0xd9cbb0 }),
  mother: () => humanoid({ height: 1.74, top: 0xa66a3d, skirt: 0x8d5733, apron: 0xf1e6cc, hair: 0x5b3a26, hairStyle: 'bun', skirtLen: 0.5, skirtR: 0.3 }),
  baker: () => humanoid({ height: 1.78, top: 0xefe5cf, belly: true, apron: 0xfaf4e6, skirt: false, legs: 0x5b4632, hairStyle: 'toque', mustache: 0x4a3324, waist: 0.2 }),
  oldman: () => humanoid({ height: 1.6, top: 0x56676a, skirt: false, legs: 0x4a4038, hair: 0xe9e1cf, hairStyle: 'cap', capColor: 0x6b5139, beard: 0xefe7d6 }),
  sweeper: () => humanoid({ height: 1.65, top: 0xb7873f, skirt: 0x9b6f33, hairStyle: 'scarf', scarfColor: 0x2f5a5d, skirtLen: 0.5 }),
  bucketman: () => humanoid({ height: 1.72, top: 0x6c4a30, sleeves: 0xe8dcc0, skirt: false, legs: 0x3f3b36, hair: 0x3d2b1f, hairStyle: 'cap', capColor: 0x3b585e }),
  stranger: () => humanoid({ height: 1.8, top: 0x1d3439, skirt: 0x1a2f33, skirtLen: 0.6, skirtR: 0.33, hairStyle: 'hood', face: false, skin: 0x161616 }),
  shadow: () => humanoid({ height: 2.05, top: 0x0a0d0e, skirt: 0x08090a, sleeves: 0x0a0d0e, skirtLen: 0.62, skirtR: 0.36, hairStyle: 'hood', face: false, skin: 0x050505, legs: 0x050505, shoes: 0x050505 }),
};

export function createActor(name, world) {
  const R = rng(name.length * 97 + 3);
  if (name === 'goat') return goat();
  if (name === 'cart') return cart();
  if (name === 'bell') return bellActor(world);
  const rig = makers[name]();
  const actor = { name, root: rig.root, rig };
  if (name === 'baker') {
    const tr = tray();
    rig.root.add(tr.g);
    tr.loaves.forEach((l) => rig.root.add(l));
    actor.tray = tr;
  }
  if (name === 'sweeper') {
    const broom = new THREE.Group();
    const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 1.3, 5), mat(C.wood, { char: true }));
    stick.position.y = -0.3;
    const head = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.3, 6), mat(0xc9a65a, { char: true }));
    head.position.y = -0.98;
    broom.add(stick, head);
    broom.rotation.x = 0.5;
    rig.arms[1].userData.hand.add(broom);
  }
  if (name === 'oldman') {
    const cane = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.9, 5), mat(C.woodDark, { char: true }));
    cane.position.y = -0.4;
    rig.arms[0].userData.hand.add(cane);
  }
  if (name === 'mother') {
    const spoon = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 0.3, 4), mat(C.wood, { char: true }));
    spoon.position.y = -0.1;
    rig.arms[1].userData.hand.add(spoon);
    actor.spoon = spoon;
  }
  actor.seed = R();
  return actor;
}

function goat() {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.3, 0.6), mat(0xd3c7b1, { char: true }));
  body.position.y = 0.48;
  g.add(body);
  const head = new THREE.Group();
  head.position.set(0, 0.62, 0.32);
  const hm = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.18, 0.26), mat(0xd3c7b1, { char: true }));
  hm.position.z = 0.1;
  head.add(hm);
  for (const sd of [1, -1]) {
    const horn = new THREE.Mesh(new THREE.ConeGeometry(0.025, 0.16, 4), mat(0x3b3329, { char: true }));
    horn.position.set(0.05 * sd, 0.12, 0.02);
    horn.rotation.x = -0.6;
    head.add(horn);
    const eye = new THREE.Mesh(new THREE.IcosahedronGeometry(0.015, 0), mat(0x1a1a1a, { char: true }));
    eye.position.set(0.08 * sd, 0.04, 0.12);
    head.add(eye);
  }
  const beard = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.1, 4), mat(0xefe7d6, { char: true }));
  beard.rotation.x = Math.PI;
  beard.position.set(0, -0.11, 0.18);
  head.add(beard);
  g.add(head);
  const legs = [];
  for (const [x, z] of [[0.11, 0.22], [-0.11, 0.22], [0.11, -0.22], [-0.11, -0.22]]) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.36, 0.06), mat(0xb9ad96, { char: true }));
    l.position.set(x, 0.18, z);
    g.add(l);
    legs.push(l);
  }
  const tail = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.12, 0.04), mat(0xd3c7b1, { char: true }));
  tail.position.set(0, 0.64, -0.31);
  g.add(tail);
  const blob = new THREE.Mesh(new THREE.CircleGeometry(0.4, 12), new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: 0.25, depthWrite: false }));
  blob.rotation.x = -Math.PI / 2; blob.position.y = 0.015;
  g.add(blob);
  return { name: 'goat', root: g, head, tail, legs };
}

function cart() {
  const g = new THREE.Group();
  const bed = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.35, 1.9), mat(C.wood, { char: true }));
  bed.position.y = 0.72;
  g.add(bed);
  for (const [x, z, sx] of [[0, 0.9, 1.2], [0, -0.9, 1.2]]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(sx, 0.08, 0.06), mat(C.woodDark, { char: true }));
    rail.position.set(x, 0.95, z);
    g.add(rail);
  }
  const R = rng(5);
  for (let i = 0; i < 4; i++) {
    const sack = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28, 1), mat(i % 2 ? 0xcdb88f : 0x9c8a66, { char: true }));
    sack.scale.set(1, 0.75, 1.1);
    sack.position.set((R() - 0.5) * 0.6, 1.05, -0.6 + i * 0.38);
    g.add(sack);
  }
  const wheels = [];
  for (const sd of [1, -1]) {
    const w = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 0.08, 10), mat(C.woodDark, { char: true }));
    w.rotation.z = Math.PI / 2;
    w.position.set(0.66 * sd, 0.45, -0.1);
    g.add(w);
    wheels.push(w);
  }
  for (const sd of [1, -1]) {
    const h = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.05, 1.4), mat(C.woodDark, { char: true }));
    h.position.set(0.4 * sd, 0.8, 1.55);
    g.add(h);
  }
  const puller = humanoid({ height: 1.8, top: 0x1d3439, skirt: 0x1a2f33, skirtLen: 0.6, skirtR: 0.33, hairStyle: 'hood', face: false, skin: 0x161616 });
  puller.root.position.set(0, 0, 2.25);
  g.add(puller.root);
  const blob = new THREE.Mesh(new THREE.CircleGeometry(1.2, 14), new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: 0.25, depthWrite: false }));
  blob.rotation.x = -Math.PI / 2; blob.position.y = 0.015; blob.scale.set(0.7, 1.3, 1);
  g.add(blob);
  return { name: 'cart', root: g, wheels, puller };
}

function bellActor(world) {
  // the bell lives in the tower; this actor only drives its swing
  return { name: 'bell', root: null, pivot: world.bellPivot, alwaysVisible: true };
}

// ------------------------------------------------------------------ actions
// ctx: { t (abs), lt (since key), loopT (since key or last reset), key, world, dt }
export function applyAction(actor, action, ctx) {
  const { lt, loopT, key, world, t } = ctx;
  if (actor.name === 'bell') {
    const p = actor.pivot;
    if (action === 'swing') p.rotation.z = (key.amp ?? 0.5) * Math.sin(t * TAU / 2.4) * (0.75 + 0.25 * Math.cos(t * 0.7));
    else if (action === 'swingWrong') {
      const a = (key.amp ?? 0.7) * Math.min(1, lt / 0.6);
      p.rotation.z = a * Math.sin(lt * TAU / 1.7 + Math.sin(lt * 5.3) * 0.9) * Math.exp(-Math.max(0, lt - 3) * 0.4);
      p.rotation.x = 0.12 * Math.sin(lt * 3.1) * Math.exp(-lt * 0.3);
    } else p.rotation.z *= 0.0;
    return;
  }
  if (actor.name === 'goat') {
    const ph = loopT;
    actor.head.rotation.x = 0.55 + 0.35 * Math.sin(ph * 1.3);
    actor.head.rotation.y = 0.2 * Math.sin(ph * 0.7);
    actor.tail.rotation.x = 0.4 * Math.sin(ph * 9);
    return;
  }
  if (actor.name === 'cart') {
    const ang = -t * 2.4;
    actor.wheels.forEach((w) => (w.rotation.x = ang));
    resetPose(actor.puller);
    walk(actor.puller, t, 0.85);
    actor.puller.arms.forEach((a) => (a.rotation.x = -0.6));
    actor.puller.upper.rotation.x = 0.25;
    return;
  }
  const r = actor.rig;
  resetPose(r);
  switch (action) {
    case 'idle':
    case 'smile':
      breathe(r, t);
      if (action === 'smile') { r.head.rotation.z = 0.12; r.head.rotation.x = 0.08; }
      break;
    case 'walk':
      walk(r, t);
      break;
    case 'lean':
      breathe(r, t, 0.6);
      r.upper.rotation.x = 0.18 * ease(lt / 1.2);
      r.head.rotation.x = 0.1;
      r.head.rotation.z = 0.12 * ease(lt / 1.5);
      break;
    case 'stiffen': {
      const k = ease(lt / 0.5);
      r.upper.rotation.x = -0.05 * k;
      r.arms[0].rotation.z = 0.02; r.arms[1].rotation.z = -0.02;
      r.hips.position.y = r.legLen + 0.015 * k;
      r.head.rotation.y = 0.55 * ease((lt - 1.4) / 2.5);
      r.head.rotation.x = -0.05 * k;
      break;
    }
    case 'watchWindow':
      breathe(r, t, 0.7);
      r.head.rotation.x = 0.05 + 0.25 * Math.max(0, Math.sin(lt * 0.8)) ** 4; // nodding off
      r.upper.rotation.z = 0.04 * Math.sin(lt * 0.5);
      r.arms[0].rotation.x = -0.5; r.arms[1].rotation.x = -0.5;
      break;
    case 'sitUpInBed': {
      r.body.position.y = -0.04;
      r.legs.forEach((l) => (l.rotation.x = -Math.PI / 2));
      r.blob.visible = false;
      const k = easeOut((lt - 0.25) / 0.45);
      r.upper.rotation.x = -Math.PI / 2 * (1 - k) + 0.12 * k;
      r.head.rotation.x = 0.3 * (1 - k) - 0.1 * k;
      r.head.rotation.y = k > 0.9 ? 0.35 * Math.sin((lt - 0.7) * 1.4) : 0;
      r.arms.forEach((a, i) => { a.rotation.x = -0.4 * k; a.rotation.z = (i ? -1 : 1) * 0.3 * k; });
      r.upper.position.y = 0;
      break;
    }
    case 'carryTray':
      breathe(r, t, 0.5);
      r.arms.forEach((a, i) => { a.rotation.x = -1.25; a.rotation.z = (i ? 1 : -1) * 0.25; });
      trayPose(actor, -1, t);
      break;
    case 'dropTray':
      dropPose(actor, lt, t);
      break;
    case 'dropLoop': {
      const P = key.period ?? 5;
      const ph = loopT % P;
      if (ph < 1.4) {
        walk(r, t, 0.6);
        r.arms.forEach((a, i) => { a.rotation.x = -1.25; a.rotation.z = (i ? 1 : -1) * 0.25; });
        trayPose(actor, -1, t);
      } else dropPose(actor, ph - 1.4, t);
      break;
    }
    case 'sweep': {
      const ph = loopT * 2.6;
      r.upper.rotation.y = 0.35 * Math.sin(ph);
      r.upper.rotation.x = 0.25;
      r.arms[1].rotation.x = -0.6 + 0.3 * Math.sin(ph);
      r.arms[0].rotation.x = -0.9 + 0.3 * Math.sin(ph);
      r.arms[0].rotation.z = -0.4;
      r.head.rotation.x = 0.25;
      break;
    }
    case 'bucket': {
      const ph = (loopT % 3.2) / 3.2;
      const pull = Math.sin(ph * TAU * 2);
      r.arms[0].rotation.x = -1.6 - 0.5 * pull;
      r.arms[1].rotation.x = -1.6 + 0.5 * pull;
      r.upper.rotation.x = 0.15 + 0.05 * pull;
      if (world.wellBucket) world.wellBucket.position.y = 0.3 + 1.1 * ease(ph * 1.25);
      break;
    }
    case 'joke':
    case 'walkJoke': {
      if (action === 'walkJoke') walk(r, t, 0.55); else breathe(r, t);
      r.upper.rotation.x += 0.22;
      const ph = (loopT % 3.4) / 3.4;
      const g = Math.sin(ph * TAU * 2);
      r.arms[1].rotation.x = -0.9 - 0.4 * g;
      r.arms[1].rotation.z = -0.3 - 0.2 * Math.abs(g);
      r.arms[0].rotation.x = -0.2;
      r.head.rotation.x = -0.1 + 0.1 * g;
      if (ph > 0.75) { // laughing at his own joke
        const l = Math.sin((ph - 0.75) * 60);
        r.hips.position.y += 0.012 * l;
        r.head.rotation.x = -0.25;
      }
      if (r.head.userData.mouth) r.head.userData.mouth.scale.y = 1 + 2.5 * Math.max(0, Math.sin(loopT * 13));
      break;
    }
    case 'freeze':
      // mid-joke, frozen, head turned toward the tower
      r.upper.rotation.x = 0.22;
      r.arms[1].rotation.x = -1.1; r.arms[1].rotation.z = -0.35;
      r.arms[0].rotation.x = -0.2;
      r.legs[0].rotation.x = 0.25; r.legs[1].rotation.x = -0.25;
      r.head.rotation.y = 1.25 * ease(lt / 0.5);
      r.head.rotation.x = -0.15;
      break;
    case 'stir':
      breathe(r, t);
      r.arms[1].rotation.x = -0.9 + 0.1 * Math.sin(t * 4);
      r.arms[1].rotation.z = -0.2 + 0.15 * Math.cos(t * 4);
      r.arms[0].rotation.x = -0.6;
      r.head.rotation.x = 0.2;
      break;
    case 'patHair': {
      breathe(r, t, 0.5);
      const up = ease(lt / 0.6) * (1 - ease((lt - 2.6) / 0.6));
      r.upper.rotation.x = 0.22 * up;
      r.arms[1].rotation.x = -2.15 * up + (up > 0.95 ? 0.12 * Math.sin((lt - 0.6) * 18) : 0);
      r.arms[1].rotation.z = 0.15 * up;
      r.head.rotation.z = 0.15 * up;
      r.head.rotation.x = 0.15 * up;
      break;
    }
    case 'loom':
      breathe(r, t, 0.4);
      r.upper.rotation.x = 0.1;
      r.head.rotation.x = 0.2;
      r.arms.forEach((a) => (a.rotation.x = -0.15));
      break;
    default:
      breathe(r, t);
  }
}

function trayPose(actor, _drop, t) {
  const tr = actor.tray;
  tr.g.visible = true;
  tr.g.position.set(0, 1.02 * actor.rig.s, 0.42);
  tr.g.rotation.set(0, 0, 0.02 * Math.sin(t * 2));
  tr.loaves.forEach((l) => {
    l.position.copy(l.userData.home).add(tr.g.position);
    l.rotation.set(0, 0, Math.PI / 2);
  });
}

function dropPose(actor, dt, t) {
  const r = actor.rig;
  breathe(r, t, 0.5);
  const k = ease(dt / 0.25);
  r.arms.forEach((a, i) => { a.rotation.x = -1.25 + 0.9 * k; a.rotation.z = (i ? 1 : -1) * 0.5 * k; });
  r.head.rotation.x = 0.35 * k;
  r.upper.rotation.x = 0.12 * k;
  const tr = actor.tray;
  const g = 9.8;
  const y0 = 1.02 * r.s;
  // tray: falls, tips and lands
  const tf = Math.sqrt((2 * (y0 - 0.02)) / g);
  const tt = Math.min(dt, tf);
  tr.g.position.set(0, Math.max(0.02, y0 - 0.5 * g * tt * tt), 0.42 + 0.35 * tt);
  tr.g.rotation.set(0.5 * Math.min(1, dt / tf), 0, dt > tf ? 0.08 : 0.3 * dt);
  tr.loaves.forEach((l) => {
    const v = l.userData.v;
    const p0 = l.userData.home.clone().add(new THREE.Vector3(0, y0, 0.42));
    // ballistic with one bounce
    const T1 = (v.y + Math.sqrt(v.y * v.y + 2 * g * (p0.y - 0.045))) / g;
    let p;
    if (dt < T1) p = new THREE.Vector3(p0.x + v.x * dt, p0.y + v.y * dt - 0.5 * g * dt * dt, p0.z + v.z * dt);
    else {
      const d2 = dt - T1;
      const vb = v.y * 0.0 + (g * T1 - v.y) * 0.3;
      const T2 = (2 * vb) / g;
      const d = Math.min(d2, T2);
      const fr = 0.35;
      p = new THREE.Vector3(p0.x + v.x * (T1 + fr * d), Math.max(0.045, 0.045 + vb * d - 0.5 * g * d * d), p0.z + v.z * (T1 + fr * d));
    }
    l.position.copy(p);
    const spin = l.userData.spin * Math.min(dt, T1 + 0.25);
    l.rotation.set(spin * 0.5, spin, Math.PI / 2);
  });
}
