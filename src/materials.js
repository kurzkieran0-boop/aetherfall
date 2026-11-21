// Shared material factory: Lambert + flat shading with a custom GLSL height fog
// (animated, ground-hugging) and an optional "shadow sweep" darkening used for
// characters (a shadow falling across them from behind).
import * as THREE from 'three';

export const shared = {
  uTime: { value: 0 },
  uFogHeight: { value: 0.16 },
  uSweep: { value: -1e4 },
  uSweepDir: { value: new THREE.Vector3(0, 0, 1) },
  uSweepDark: { value: 0 },
};

const FOG_FRAG = /* glsl */ `
#ifdef USE_FOG
  float fogH = exp(-max(vWPos.y, 0.0) * uFogHeight);
  float fogN = 0.8 + 0.2 * sin(vWPos.x * 0.21 + uTime * 0.23) * sin(vWPos.z * 0.17 - uTime * 0.19 + 1.3);
  float fogD = fogDensity * vFogDepth;
  float fogF = 1.0 - exp(-fogD * fogD * (0.45 + 0.8 * fogH) * fogN);
  gl_FragColor.rgb = mix(gl_FragColor.rgb, fogColor, clamp(fogF, 0.0, 1.0));
#endif
`;
const SWEEP_FRAG = /* glsl */ `
  float swp = 1.0 - smoothstep(uSweep - 0.25, uSweep + 0.25, dot(vWPos, uSweepDir));
  gl_FragColor.rgb *= 1.0 - uSweepDark * swp;
`;

function patch(m, kind) {
  const isChar = kind === 'char';
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = shared.uTime;
    sh.uniforms.uFogHeight = shared.uFogHeight;
    if (isChar) {
      sh.uniforms.uSweep = shared.uSweep;
      sh.uniforms.uSweepDir = shared.uSweepDir;
      sh.uniforms.uSweepDark = shared.uSweepDark;
    }
    sh.vertexShader = 'varying vec3 vWPos;\n' + sh.vertexShader.replace(
      '#include <fog_vertex>',
      `#include <fog_vertex>
      #ifdef USE_INSTANCING
        vWPos = (modelMatrix * instanceMatrix * vec4(transformed, 1.0)).xyz;
      #else
        vWPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
      #endif`
    );
    sh.fragmentShader =
      'varying vec3 vWPos;\nuniform float uTime;\nuniform float uFogHeight;\n' +
      (isChar ? 'uniform float uSweep;\nuniform vec3 uSweepDir;\nuniform float uSweepDark;\n' : '') +
      sh.fragmentShader.replace('#include <fog_fragment>', (isChar ? SWEEP_FRAG : '') + FOG_FRAG);
  };
  m.customProgramCacheKey = () => 'vtr-' + kind;
  return m;
}

const cache = new Map();
export function mat(color, opts = {}) {
  const key = JSON.stringify([color, opts.char, opts.emissive, opts.emissiveIntensity, opts.side, opts.flat]);
  if (!opts.unique && cache.has(key)) return cache.get(key);
  const m = new THREE.MeshLambertMaterial({
    color,
    flatShading: opts.flat !== false,
    side: opts.side ?? THREE.FrontSide,
    emissive: opts.emissive ?? 0x000000,
    emissiveIntensity: opts.emissiveIntensity ?? 1,
    transparent: !!opts.transparent,
    opacity: opts.opacity ?? 1,
    map: opts.map ?? null,
    emissiveMap: opts.emissiveMap ?? null,
    alphaTest: opts.alphaTest ?? 0,
    depthWrite: opts.depthWrite ?? true,
    polygonOffset: !!opts.polygonOffset,
    polygonOffsetFactor: opts.polygonOffset ? -2 : 0,
    polygonOffsetUnits: opts.polygonOffset ? -2 : 0,
  });
  patch(m, opts.char ? 'char' : 'std');
  if (!opts.unique) cache.set(key, m);
  return m;
}

// Deterministic PRNG (mulberry32)
export function rng(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const C = {
  stone: 0xd8c6a3, stoneDark: 0xa48f72, stoneWarm: 0xcdb08a, plaster: 0xe7d8ba,
  roofTeal: 0x2f4c53, roofSlate: 0x3b585e, roofThatch: 0x8d6a45,
  wood: 0x6a4a32, woodDark: 0x43301f, iron: 0x2a2f31,
  earth: 0x8a7458, road: 0xa98f6b, cobble: 0xb8a385, grass: 0x6e7a52,
  tree: 0x2e5148, treeDark: 0x24423c, trunk: 0x5a4130,
  cream: 0xf1e4c8, skin: 0xe7b892, bronze: 0x9a7642, chalk: 0xc9282d,
};
