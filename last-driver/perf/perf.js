import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
window.run = async (w, h, bloom, shadows, nl = 8, lambert = false) => {
  const r = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  r.setSize(w, h, false); r.shadowMap.enabled = shadows;
  r.toneMapping = THREE.ACESFilmicToneMapping;
  document.body.appendChild(r.domElement);
  const s = new THREE.Scene(); s.fog = new THREE.FogExp2(0x0a0820, 0.004);
  const cam = new THREE.PerspectiveCamera(50, w / h, 0.5, 2000); cam.position.set(0, 20, 80);
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const mat = lambert === 'basic' ? new THREE.MeshBasicMaterial({ color: 0x334455 }) : lambert ? new THREE.MeshLambertMaterial({ color: 0x223344, emissive: 0x332200 }) : new THREE.MeshStandardMaterial({ color: 0x223344, roughness: 0.6, emissive: 0x332200 });
  const inst = new THREE.InstancedMesh(geo, mat, 600);
  const m = new THREE.Matrix4();
  for (let i = 0; i < 600; i++) { const hh = 20 + Math.random() * 120; m.compose(new THREE.Vector3((i % 30 - 15) * 18, hh / 2, -Math.floor(i / 30) * 18), new THREE.Quaternion(), new THREE.Vector3(12, hh, 12)); inst.setMatrixAt(i, m); }
  inst.castShadow = inst.receiveShadow = true; s.add(inst);
  const g = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.2, metalness: 0.6 }));
  g.rotation.x = -Math.PI / 2; g.receiveShadow = true; s.add(g);
  const dl = new THREE.DirectionalLight(0x8899ff, 1); dl.position.set(50, 100, 50); dl.castShadow = shadows; s.add(dl); s.add(new THREE.AmbientLight(0x404060, 0.5));
  for (let i = 0; i < nl; i++) { const p = new THREE.PointLight(0xff3366, 50, 100); p.position.set(i * 20 - 80, 5, 20); s.add(p); }
  const comp = new EffectComposer(r); comp.addPass(new RenderPass(s, cam));
  if (bloom) comp.addPass(new UnrealBloomPass(new THREE.Vector2(w, h), 1, 0.4, 0.8));
  comp.render();
  const t = performance.now();
  for (let i = 0; i < 5; i++) { cam.position.z -= 1; comp.render(); }
  const rt = (performance.now() - t) / 5;
  const t2 = performance.now(); await new Promise((res) => r.domElement.toBlob(res, 'image/jpeg', 0.9)); const bt = performance.now() - t2;
  r.dispose(); r.domElement.remove();
  return { w, h, bloom, shadows, nl, lambert, render: Math.round(rt), blob: Math.round(bt) };
};
window.READY = true;
