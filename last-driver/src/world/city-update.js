// Per-frame animation of the city: hero car on the route, traffic (flow /
// stop / turn-to-face), drones, drawbridge, elevator, signs and screens.
import * as THREE from 'three';
import gsap from 'gsap';
import { h1, clamp, noise1 } from '../core/util.js';
import { ROUTE, routeY } from './city.js';
import { poseKira } from './human.js';

const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v = new THREE.Vector3(), one = new THREE.Vector3(1, 1, 1);
export const win = (p, a = 0, b = 1, ease = 'power2.inOut') => gsap.parseEase(ease)(clamp((p - a) / Math.max(1e-4, b - a)));

// hero car state for a shot at local progress p
export function carState(shot, p) {
  const c = shot.car || {};
  const [s0, s1] = c.s || [0, 0];
  const ez = gsap.parseEase(c.ease || 'none');
  const s = s0 + (s1 - s0) * ez(clamp(p));
  const dp = 1e-3;
  const sN = s0 + (s1 - s0) * ez(clamp(p + dp));
  const speed = ((sN - s) / (dp * shot.dur)) || 0;
  let y = routeY(s);
  let pitch = 0;
  if (c.jump && s > ROUTE.bridge[0] - 8 && s < ROUTE.bridge[1] + 4) {
    const u = clamp((s - (ROUTE.bridge[0] - 8)) / (ROUTE.bridge[1] + 4 - (ROUTE.bridge[0] - 8)));
    y += Math.sin(u * Math.PI) * 13;
    pitch = Math.cos(u * Math.PI) * 0.22;
  } else {
    const y2 = routeY(s + 2);
    pitch = Math.atan2(y2 - y, 2);
  }
  const lane = c.lane ?? 5.5;
  const sway = c.weave ? Math.sin(s * 0.06) * c.weave : 0;
  return { s, speed, pos: new THREE.Vector3(lane + sway, y, -s), pitch, yaw: c.weave ? -Math.cos(s * 0.06) * c.weave * 0.06 : 0 };
}

export function updateCity(W, f, car) {
  const { t, fx, p } = f;
  W.shared.uTime.value = t;
  W.sky.material.uniforms.uTime.value = t;
  W.sky.material.uniforms.uFlash.value = fx.lightning ? Math.max(0, Math.sin(t * 3.1) * Math.sin(t * 7.7)) * 0.8 : 0;
  W.sky.position.copy(f.camera.position);
  // hero car
  const C = W.car;
  C.visible = fx.car !== false;
  C.position.copy(car.pos);
  C.rotation.set(car.pitch, car.yaw, 0, 'YXZ');
  for (const w of C.userData.wheels) w.rotation.z = -car.s / 0.37;
  for (const b of C.userData.beams) b.visible = fx.beams !== false;
  // traffic lights
  const red = fx.red !== undefined ? f.p >= fx.red : false;
  W.trafficLightMat.color.setRGB(red ? 4 : 0.2, red ? 0.15 : 3, red ? 0.2 : 0.6);
  // traffic
  const { traffic, tails, heads } = W.traffic;
  const stop = fx.trafficStop !== undefined ? win(p, fx.trafficStop, fx.trafficStop + 0.25, 'power2.out') : 0;
  const turn = fx.trafficTurn !== undefined ? win(p, fx.trafficTurn[0], fx.trafficTurn[1]) : 0;
  W.trafficData.forEach((d, i) => {
    let s = d.s0 + d.v * d.dir * -1 * t * (1 - stop) * (1 - turn);
    const span = d.skyway ? 900 : 600;
    const base = d.skyway ? 1000 : 0;
    s = base + (((s - base) % span) + span) % span;
    const y = routeY(s) + (d.skyway ? 0 : 0);
    let yaw = d.dir > 0 ? Math.PI : 0;
    // turn to face the hero: rotate so they face the camera / the car
    if (turn > 0 && d.dir < 0) yaw += turn * Math.PI * (h1(i, 43) < 0.5 ? 1 : -1);
    v.set(d.lane, y, -s);
    if (Math.abs(s - car.s) < 7 && Math.abs(d.lane - car.pos.x) < 3) v.y = -50; // never overlap the hero
    if (v.distanceTo(f.camera.position) < 6) v.y = -50; // never put the lens inside a car
    e.set(0, yaw, 0);
    q.setFromEuler(e);
    m4.compose(v, q, one);
    traffic.setMatrixAt(i, m4);
    const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
    const tp = v.clone().addScaledVector(fwd, -2.22); tp.y += 0.75;
    const hp = v.clone().addScaledVector(fwd, 2.22); hp.y += 0.6;
    m4.compose(tp, q, one); tails.setMatrixAt(i, m4);
    m4.compose(hp, q, new THREE.Vector3(1, 1 + turn * 1.5, 1)); heads.setMatrixAt(i, m4);
  });
  traffic.instanceMatrix.needsUpdate = tails.instanceMatrix.needsUpdate = heads.instanceMatrix.needsUpdate = true;
  heads.material.color.setRGB(2.5 + turn * 1.2, 2.8 + turn * 1.2, 3.2 + turn * 1.2);
  // the river of headlights below the bridge also turns toward the tower
  W.riverLights.uniforms.uTurn.value = fx.riverTurn ? win(p, fx.riverTurn[0], fx.riverTurn[1]) : 0;
  // drones swarm around the car (or hover in formation)
  const D = W.drones;
  const dn = fx.drones ?? 0;
  for (let i = 0; i < D.n; i++) {
    if (i >= dn) { m4.compose(v.set(0, -100, 0), q.identity(), one); D.drone.setMatrixAt(i, m4); D.droneEye.setMatrixAt(i, m4); continue; }
    const a = h1(i, 80) * Math.PI * 2 + t * (0.3 + h1(i, 81) * 0.4);
    const rad = 10 + h1(i, 82) * 30;
    const c = fx.droneCenter ? new THREE.Vector3(...fx.droneCenter) : car.pos.clone().add(new THREE.Vector3(0, 0, -10));
    v.set(c.x + Math.cos(a) * rad, c.y + 8 + h1(i, 83) * 22 + Math.sin(t * 2 + i) * 1.5, c.z + Math.sin(a) * rad * 0.6 - h1(i, 84) * 20);
    e.set(Math.sin(t * 3 + i) * 0.15, a, Math.cos(t * 3 + i) * 0.15);
    q.setFromEuler(e);
    m4.compose(v, q, one);
    D.drone.setMatrixAt(i, m4);
    const blink = Math.sin(t * 9 + i) > 0 ? 1 : 0.2;
    v.y -= 0.25;
    m4.compose(v, q, new THREE.Vector3(blink, blink, blink));
    D.droneEye.setMatrixAt(i, m4);
  }
  D.drone.instanceMatrix.needsUpdate = D.droneEye.instanceMatrix.needsUpdate = true;
  // drawbridge leaves rising
  const lift = fx.bridgeLift !== undefined ? fx.bridgeLift[0] + (fx.bridgeLift[1] - fx.bridgeLift[0]) * win(p, 0, 1, 'power1.inOut') : 0;
  for (const L of W.leaves) L.pivot.rotation.x = (L.end === 0 ? 1 : -1) * lift;
  // elevator capsule
  const el = fx.elevator ? win(p, 0, 1, fx.elevator[2] || 'power2.inOut') * (fx.elevator[1] - fx.elevator[0]) + fx.elevator[0] : 0;
  W.capsule.position.y = ROUTE.skyY + 4 + el;
  // windows, signs, screens
  W.buildingMat.uniforms.uAllLit.value = fx.allLit !== undefined ? (p >= fx.allLit ? 1 : 0) : 0;
  W.buildingMat.uniforms.uLit.value = fx.blackout !== undefined ? (p >= fx.blackout ? 0.05 : 1) : 1;
  const sf = fx.face !== undefined ? clamp((p - fx.face) / 0.08) : 0;
  W.boardMat.uniforms.uFace.value = sf;
  const flick = 0.75 + 0.25 * noise1(t * 6, 3);
  W.signMats.forEach((m, i) => { const k = (i % 3 === 0 ? flick : 1) * (fx.blackout !== undefined && p >= fx.blackout ? 0.05 : 1); m.color.setRGB(2.2 * k, 2.2 * k, 2.2 * k); });
  // rain follows the camera
  const ru = W.rain.material.uniforms;
  ru.uTime.value = t;
  ru.uCam.value.copy(f.camera.position);
  ru.uVel.value.set(0, 0, -car.speed * (fx.rainRel ?? 1));
  ru.uAmt.value = fx.rain ?? 1;
  // Kira on foot
  const K = W.kira;
  K.visible = !!fx.kira;
  if (fx.kira) {
    const k = fx.kira;
    const pos = k.from ? new THREE.Vector3(...k.from).lerp(new THREE.Vector3(...k.to), win(p, k.a ?? 0, k.b ?? 1, 'none')) : new THREE.Vector3(...k.pos);
    K.position.copy(pos);
    K.rotation.y = k.yaw ?? 0;
    const walking = k.from && p > (k.a ?? 0) && p < (k.b ?? 1);
    poseKira(K, walking ? k.mode || 'walk' : k.pose || 'stand', t * 7, k.reach ? win(p, k.reach[0], k.reach[1]) : 1);
  }
}
