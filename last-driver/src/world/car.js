// Hero car (sculpted sports coupe: extruded profile, clearcoat paint, glass,
// light bars, volumetric headlight beams) and a lightweight traffic car.
import * as THREE from 'three';
import { beamMaterial } from '../core/shaders.js';

function profileShape() {
  // side profile, x = forward (m), y = up
  const s = new THREE.Shape();
  s.moveTo(-2.3, 0.32);
  s.lineTo(-2.38, 0.62);
  s.quadraticCurveTo(-2.35, 0.9, -1.95, 0.95);
  s.lineTo(-1.15, 1.02);
  s.quadraticCurveTo(-0.55, 1.32, 0.15, 1.3);
  s.quadraticCurveTo(0.75, 1.27, 1.15, 0.98);
  s.lineTo(2.05, 0.78);
  s.quadraticCurveTo(2.42, 0.7, 2.4, 0.45);
  s.lineTo(2.3, 0.3);
  s.lineTo(-2.3, 0.32);
  return s;
}
function cabinShape() {
  const s = new THREE.Shape();
  s.moveTo(-1.05, 1.03);
  s.quadraticCurveTo(-0.5, 1.3, 0.15, 1.28);
  s.quadraticCurveTo(0.72, 1.25, 1.08, 0.99);
  s.lineTo(-1.05, 1.03);
  return s;
}

export function heroCar(envMap, paint = '#c4122f') {
  const g = new THREE.Group();
  const body = new THREE.ExtrudeGeometry(profileShape(), { depth: 1.7, bevelEnabled: true, bevelThickness: 0.16, bevelSize: 0.12, bevelSegments: 4, curveSegments: 16 });
  body.translate(0, 0, -0.85);
  {
    // tumblehome: the upper body and the nose/tail pinch inward
    const p = body.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
      let k = 1 - Math.max(0, y - 0.7) * 0.32;
      k *= 1 - Math.pow(Math.max(0, Math.abs(x) - 1.6) / 0.8, 2) * 0.16;
      p.setZ(i, z * k);
    }
    body.computeVertexNormals();
  }
  const paintMat = new THREE.MeshPhysicalMaterial({ color: paint, metalness: 0.55, roughness: 0.28, clearcoat: 1, clearcoatRoughness: 0.06, envMap, envMapIntensity: 1.6 });
  const bm = new THREE.Mesh(body, paintMat);
  g.add(bm);
  const cab = new THREE.ExtrudeGeometry(cabinShape(), { depth: 1.5, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.06, bevelSegments: 3, curveSegments: 12 });
  cab.translate(0, 0.03, -0.75);
  {
    const p = cab.attributes.position;
    for (let i = 0; i < p.count; i++) p.setZ(i, p.getZ(i) * (1 - Math.max(0, p.getY(i) - 1.0) * 0.9));
    cab.computeVertexNormals();
  }
  const glass = new THREE.MeshPhysicalMaterial({ color: '#05060a', metalness: 0.9, roughness: 0.05, envMap, envMapIntensity: 2.2 });
  g.add(new THREE.Mesh(cab, glass));
  // wheels
  const tire = new THREE.MeshStandardMaterial({ color: '#0a0a0c', roughness: 0.7, envMap, envMapIntensity: 0.4 });
  const rim = new THREE.MeshStandardMaterial({ color: '#8890a0', metalness: 1, roughness: 0.25, envMap });
  const wheels = [];
  for (const [x, z] of [[1.45, 0.92], [1.45, -0.92], [-1.45, 0.92], [-1.45, -0.92]]) {
    const w = new THREE.Group();
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.37, 0.37, 0.3, 24), tire);
    t.rotation.x = Math.PI / 2;
    const r = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.31, 6), rim);
    r.rotation.x = Math.PI / 2;
    w.add(t, r);
    w.position.set(x, 0.37, z);
    g.add(w);
    wheels.push(w);
  }
  // light bars (emissive, bloom)
  const head = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 1.6), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.6, 3.0), toneMapped: false }));
  head.position.set(2.36, 0.62, 0);
  const tail = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.07, 1.75), new THREE.MeshBasicMaterial({ color: new THREE.Color(4.0, 0.15, 0.25), toneMapped: false }));
  tail.position.set(-2.4, 0.74, 0);
  const under = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 1.9), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.9, 0.1, 0.7), transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false }));
  under.rotation.x = -Math.PI / 2;
  under.position.y = 0.03;
  const trim = new THREE.MeshStandardMaterial({ color: '#07070a', metalness: 0.6, roughness: 0.35, envMap });
  const diff = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.22, 1.6), trim);
  diff.position.set(-2.22, 0.36, 0);
  const lip = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 1.75), trim);
  lip.position.set(2.2, 0.3, 0);
  const wing = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.05, 1.8), trim);
  wing.position.set(-2.1, 1.08, 0);
  const tailGlow = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.03, 1.5), new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 0.3, 0.4), toneMapped: false }));
  tailGlow.position.set(-2.43, 0.52, 0);
  for (const s of [-1, 1]) {
    const skirt = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.03, 0.03), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.3, 2.2, 2.8), toneMapped: false }));
    skirt.position.set(0, 0.33, s * 0.98);
    g.add(skirt);
  }
  g.add(head, tail, under, diff, lip, wing, tailGlow);
  // headlight cones
  const beams = [];
  for (const z of [0.6, -0.6]) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(2.6, 18, 20, 1, true), beamMaterial('#bfe4ff', 0.22));
    cone.rotation.z = Math.PI / 2;
    cone.position.set(2.4 + 9, 0.35, z);
    cone.geometry.translate(0, 0, 0);
    g.add(cone);
    beams.push(cone);
  }
  // car is modelled facing +x; world forward is -Z
  const root = new THREE.Group();
  g.rotation.y = Math.PI / 2;
  root.add(g);
  root.userData = { wheels, beams, body: g, tail, head };
  return root;
}

export function trafficGeometry() {
  const a = new THREE.BoxGeometry(1.9, 0.7, 4.4);
  a.translate(0, 0.55, 0);
  const b = new THREE.BoxGeometry(1.6, 0.55, 2.2);
  b.translate(0, 1.15, 0.2);
  return mergeSimple([a, b]);
}

export function mergeSimple(geos) {
  const pos = [], nor = [], idx = [];
  let off = 0;
  for (const g of geos) {
    const gi = g.index ? g.toNonIndexed() : g;
    const p = gi.attributes.position.array, n = gi.attributes.normal.array;
    for (let i = 0; i < p.length; i++) { pos.push(p[i]); nor.push(n[i]); }
    for (let i = 0; i < p.length / 3; i++) idx.push(off + i);
    off += p.length / 3;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  out.setIndex(idx);
  return out;
}
