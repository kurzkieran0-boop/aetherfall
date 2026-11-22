// Kira: a stylised but solid 3D figure (capsule anatomy, hooded jacket with a
// cyan light seam), with a procedural walk cycle and a reach pose.
import * as THREE from 'three';

export function kira(envMap) {
  const jacket = new THREE.MeshStandardMaterial({ color: '#16161e', roughness: 0.55, metalness: 0.1, envMap, envMapIntensity: 0.8 });
  const pants = new THREE.MeshStandardMaterial({ color: '#0d0d12', roughness: 0.8, envMap, envMapIntensity: 0.5 });
  const skin = new THREE.MeshStandardMaterial({ color: '#8a5a48', roughness: 0.6, envMap, envMapIntensity: 0.5 });
  const seam = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.2, 2.2, 2.6), toneMapped: false });
  const root = new THREE.Group();
  const hips = new THREE.Group();
  hips.position.y = 0.95;
  root.add(hips);
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, 0.42, 6, 12), jacket);
  torso.position.y = 0.33;
  torso.scale.set(1.0, 1, 0.72);
  hips.add(torso);
  const strip = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.5, 0.03), seam);
  strip.position.set(0, 0.36, -0.17);
  hips.add(strip);
  const neck = new THREE.Group();
  neck.position.y = 0.68;
  hips.add(neck);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 20, 16), skin);
  head.position.y = 0.14;
  head.scale.set(0.9, 1.08, 0.95);
  neck.add(head);
  const hood = new THREE.Mesh(new THREE.SphereGeometry(0.135, 20, 16, 0, Math.PI * 2, 0, Math.PI * 0.55), jacket);
  hood.position.set(0, 0.15, -0.02);
  hood.rotation.x = -0.35;
  neck.add(hood);
  const limb = (r, l, mat) => {
    const g = new THREE.Group();
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, l, 4, 10), mat);
    m.position.y = -l / 2 - r;
    g.add(m);
    const lower = new THREE.Group();
    lower.position.y = -l - r * 1.6;
    g.add(lower);
    const m2 = new THREE.Mesh(new THREE.CapsuleGeometry(r * 0.85, l, 4, 10), mat);
    m2.position.y = -l / 2 - r;
    lower.add(m2);
    return { g, lower };
  };
  const legs = [limb(0.085, 0.34, pants), limb(0.085, 0.34, pants)];
  legs[0].g.position.set(0.11, 0, 0);
  legs[1].g.position.set(-0.11, 0, 0);
  hips.add(legs[0].g, legs[1].g);
  const arms = [limb(0.06, 0.24, jacket), limb(0.06, 0.24, jacket)];
  arms[0].g.position.set(0.27, 0.6, 0);
  arms[1].g.position.set(-0.27, 0.6, 0);
  hips.add(arms[0].g, arms[1].g);
  // the drive: tiny glowing chip in the right hand
  const chip = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.012, 0.06), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.4, 3, 3.2), toneMapped: false }));
  chip.position.y = -0.3;
  arms[0].lower.add(chip);
  root.userData = { hips, legs, arms, neck, chip };
  return root;
}

// mode: 'walk' | 'stand' | 'reach'; phase in radians; k = reach amount
export function poseKira(k, mode, phase, amt = 1) {
  const { hips, legs, arms, neck } = k.userData;
  if (mode === 'walk' || mode === 'run') {
    const a = mode === 'run' ? 0.9 : 0.5;
    for (let i = 0; i < 2; i++) {
      const p = phase + i * Math.PI;
      legs[i].g.rotation.x = Math.sin(p) * a;
      legs[i].lower.rotation.x = Math.max(0, -Math.cos(p)) * a * 1.4;
      arms[i].g.rotation.x = -Math.sin(p) * a * 0.8;
      arms[i].lower.rotation.x = -0.4 - (mode === 'run' ? 0.8 : 0);
    }
    hips.position.y = 0.95 + Math.abs(Math.cos(phase)) * 0.04;
    hips.rotation.x = mode === 'run' ? -0.2 : -0.05;
  } else {
    legs.forEach((l) => { l.g.rotation.x = 0; l.lower.rotation.x = 0; });
    arms[1].g.rotation.x = 0.05; arms[1].lower.rotation.x = -0.15;
    arms[0].g.rotation.x = mode === 'reach' ? -1.35 * amt : 0.05;
    arms[0].lower.rotation.x = mode === 'reach' ? -0.2 * amt : -0.15;
    hips.position.y = 0.95 + Math.sin(phase * 0.3) * 0.006;
    hips.rotation.x = 0;
  }
  neck.rotation.x = mode === 'reach' ? 0.15 : 0;
}
