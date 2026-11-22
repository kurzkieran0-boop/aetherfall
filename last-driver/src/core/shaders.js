// GLSL for the city: procedural lit-window facades, wet asphalt with mirror
// reflections, sky dome, rain streaks, volumetric beams, final post pass.
import * as THREE from 'three';

const COMMON = /* glsl */ `
float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); return fract(p.x*p.y); }
float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
vec3 applyFog(vec3 col, float dist, float h, vec3 fogCol, float dens, vec3 hazeCol){
  float f = 1.0 - exp(-pow(dens*dist, 1.35));
  float low = exp(-max(h,0.0)*0.018);
  return mix(col, mix(fogCol, hazeCol, low*0.7), clamp(f,0.,1.));
}`;

export const fogUniforms = () => ({
  uFogCol: { value: new THREE.Color('#1a1238') },
  uHaze: { value: new THREE.Color('#7a2a6a') },
  uFogDens: { value: 0.0028 },
  uTime: { value: 0 },
});

// Instanced skyscraper facade: windows from world position, per-instance seed/tint.
export function buildingMaterial(shared) {
  return new THREE.ShaderMaterial({
    uniforms: { ...shared, uLit: { value: 1 }, uAllLit: { value: 0 }, uFace: { value: 0 } },
    vertexShader: /* glsl */ `
      attribute float aSeed; attribute vec3 aTint; attribute float aLitP;
      varying vec3 vW; varying vec3 vN; varying float vSeed; varying vec3 vTint; varying float vLitP; varying float vTopY; varying float vBaseY;
      void main(){
        vec4 w = modelMatrix * instanceMatrix * vec4(position,1.0);
        vW = w.xyz; vN = normalize(mat3(modelMatrix * instanceMatrix) * normal);
        vSeed = aSeed; vTint = aTint; vLitP = aLitP;
        vTopY = (modelMatrix * instanceMatrix * vec4(0.,0.5,0.,1.)).y;
        vBaseY = (modelMatrix * instanceMatrix * vec4(0.,-0.5,0.,1.)).y;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uFogCol; uniform vec3 uHaze; uniform float uFogDens; uniform float uTime; uniform float uLit; uniform float uAllLit;
      varying vec3 vW; varying vec3 vN; varying float vSeed; varying vec3 vTint; varying float vLitP; varying float vTopY; varying float vBaseY;
      ${COMMON}
      void main(){
        vec3 N = normalize(vN);
        vec3 V = normalize(cameraPosition - vW);
        float dist = length(cameraPosition - vW);
        vec3 col;
        vec2 f = vec2(abs(N.x) > 0.5 ? vW.z : vW.x, vW.y - vBaseY);
        vec2 cs = vec2(3.0 + vSeed*1.6, 3.7);
        float aa = smoothstep(450.0, 1400.0, dist);
        if (N.y > 0.5) {
          col = vTint*0.05 + vec3(0.02,0.02,0.04);
        } else {
          vec2 cell = floor(f/cs); vec2 fr = fract(f/cs);
          float win = step(0.16,fr.x)*step(fr.x,0.84)*step(0.22,fr.y)*step(fr.y,0.82);
          float r = hash(cell + vSeed*31.7);
          float band = step(0.82, hash(vec2(cell.y, vSeed*9.1)));      // fully dark floors
          float lit = step(1.0 - vLitP*uLit, r) * (1.0-band);
          lit = max(lit, uAllLit);
          float warm = step(0.55, hash(cell*1.31 + vSeed));
          vec3 wc = mix(vec3(0.45,0.75,1.25), vec3(1.35,0.85,0.5), warm);
          wc *= 0.75 + 0.5*hash(cell+3.1);
          float flick = 0.85 + 0.15*sin(uTime*(2.0+r*6.0) + r*40.0);
          vec3 dark = vec3(0.015,0.02,0.035) + vTint*0.03;
          vec3 wcol = mix(dark, wc*flick, lit);
          wcol = mix(wcol, dark*0.5 + wc*max(vLitP*uLit, uAllLit)*0.45, aa);
          vec3 wall = vTint*(0.035 + 0.03*max(dot(N, normalize(vec3(0.3,0.4,0.8))),0.0));
          col = mix(wall, wcol, win*(1.0-aa) + aa*0.6);
          // street-level neon spill and rim light
          float street = exp(-(vW.y)*0.08);
          col += vec3(0.6,0.08,0.45)*street*0.12 + vec3(0.05,0.35,0.6)*street*0.06;
          float fres = pow(1.0 - max(dot(N,V),0.0), 3.0);
          col += vec3(0.25,0.55,1.0)*fres*0.08;
          // glowing crown line
          float crown = smoothstep(1.2, 0.0, abs(vW.y - (vTopY-1.5)));
          col += mix(vec3(0.0,0.9,1.0), vec3(1.0,0.15,0.6), step(0.5, fract(vSeed*7.0))) * crown * step(0.62, fract(vSeed*13.0)) * 1.6;
        }
        col = applyFog(col, dist, vW.y, uFogCol, uFogDens, uHaze);
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
}

// Wet ground: asphalt, lane markings, sidewalks, mirror reflection with ripples.
export function groundMaterial(shared, reflTex, texMatrix) {
  return new THREE.ShaderMaterial({
    uniforms: { ...shared, tRefl: { value: reflTex }, uTexMat: { value: texMatrix }, uRain: { value: 1 } },
    vertexShader: /* glsl */ `
      uniform mat4 uTexMat; varying vec4 vRU; varying vec3 vW;
      void main(){ vec4 w = modelMatrix*vec4(position,1.0); vW=w.xyz; vRU = uTexMat*w; gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D tRefl; uniform vec3 uFogCol; uniform vec3 uHaze; uniform float uFogDens; uniform float uTime; uniform float uRain;
      varying vec4 vRU; varying vec3 vW;
      ${COMMON}
      void main(){
        float x = abs(vW.x), z = vW.z;
        float dist = length(cameraPosition - vW);
        vec3 asphalt = vec3(0.018,0.018,0.026) + noise(vW.xz*3.0)*0.012;
        vec3 col = asphalt;
        float road = step(x, 12.0);
        // lane markings
        float dash = step(0.5, fract(z/6.0));
        float lane = (smoothstep(0.12,0.0,abs(x-4.0)) * dash + smoothstep(0.1,0.0,abs(x-0.0))*0.0 + smoothstep(0.14,0.02,abs(x-11.3)));
        float center = smoothstep(0.12,0.0,abs(vW.x+0.15)) + smoothstep(0.12,0.0,abs(vW.x-0.15));
        col += vec3(0.7,0.7,0.65)*lane*road*0.35 + vec3(0.9,0.7,0.2)*center*road*0.35;
        // crosswalks every 80m
        float cz = mod(z, 80.0);
        float cross = step(cz, 5.0) * step(0.5, fract(vW.x/1.2)) * road;
        col += vec3(0.6)*cross*0.25;
        // sidewalk
        float side = step(12.0, x) * step(x, 16.0);
        col = mix(col, vec3(0.04,0.04,0.055) + noise(floor(vW.xz))*0.02, side);
        // reflection with rain ripples
        vec2 rip = vec2(noise(vW.xz*1.7 + uTime*0.9), noise(vW.xz*1.7 - uTime*0.7)) - 0.5;
        vec2 uv = vRU.xy / vRU.w + rip*0.012*uRain;
        vec3 refl = texture2D(tRefl, uv).rgb*0.5 + texture2D(tRefl, uv+vec2(0.0,0.006)).rgb*0.25 + texture2D(tRefl, uv-vec2(0.0,0.006)).rgb*0.25;
        vec3 V = normalize(cameraPosition - vW);
        float fres = 0.35 + 0.6*pow(1.0 - max(V.y,0.0), 4.0);
        float puddle = smoothstep(0.45,0.7, noise(vW.xz*0.12));
        float wet = mix(0.55, 1.0, puddle) * fres;
        col = col + refl*wet*(1.0 - side*0.4);
        col = applyFog(col, dist, 0.0, uFogCol, uFogDens, uHaze);
        gl_FragColor = vec4(col,1.0);
      }`,
  });
}

export function skyMaterial() {
  return new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false,
    uniforms: { uTime: { value: 0 }, uTop: { value: new THREE.Color('#05030f') }, uMid: { value: new THREE.Color('#1c0f3d') }, uHor: { value: new THREE.Color('#a0306e') }, uFlash: { value: 0 } },
    vertexShader: `varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); gl_Position.z = gl_Position.w; }`,
    fragmentShader: /* glsl */ `
      uniform vec3 uTop; uniform vec3 uMid; uniform vec3 uHor; uniform float uTime; uniform float uFlash; varying vec3 vD;
      ${COMMON}
      void main(){
        float y = vD.y;
        vec3 c = mix(uHor, uMid, smoothstep(-0.02, 0.25, y));
        c = mix(c, uTop, smoothstep(0.25, 0.8, y));
        // drifting cloud deck lit from below
        vec2 p = vD.xz/(max(y,0.05)+0.15)*1.5 + vec2(uTime*0.02, 0.0);
        float cl = noise(p) * 0.6 + noise(p*2.3)*0.3 + noise(p*5.1)*0.1;
        c += uHor*0.35*smoothstep(0.45,0.85,cl)*smoothstep(0.9,0.05,y);
        c += vec3(0.8,0.85,1.0)*uFlash*smoothstep(0.3,0.9,cl);
        gl_FragColor = vec4(c,1.0);
      }`,
  });
}

// Rain: line segments whose positions wrap around the camera (GPU only).
export function rainMaterial() {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uCam: { value: new THREE.Vector3() }, uVel: { value: new THREE.Vector3() }, uAmt: { value: 1 } },
    vertexShader: /* glsl */ `
      uniform float uTime; uniform vec3 uCam; uniform vec3 uVel; attribute float aEnd; attribute vec3 aSeed; varying float vA;
      void main(){
        vec3 box = vec3(60.0, 40.0, 60.0);
        vec3 p = aSeed*box;
        p.y -= uTime*28.0 + aSeed.x*7.0;
        p = mod(p - uCam + box*0.5, box) - box*0.5 + uCam;
        vec3 dir = normalize(vec3(0.0,-28.0,0.0) - uVel*0.6);
        p += dir * aEnd * (0.9 + length(uVel)*0.025);
        vA = (1.0 - aEnd*0.7);
        gl_Position = projectionMatrix*viewMatrix*vec4(p,1.0);
      }`,
    fragmentShader: `uniform float uAmt; varying float vA; void main(){ gl_FragColor = vec4(vec3(0.55,0.7,0.95)*vA*0.28*uAmt, 1.0); }`,
  });
}

// Soft additive volumetric cone / beam (headlights, street lamps, shafts).
export function beamMaterial(color, strength = 1) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    uniforms: { uCol: { value: new THREE.Color(color) }, uStr: { value: strength } },
    vertexShader: `varying vec2 vUv; varying vec3 vN; varying vec3 vV; void main(){ vUv=uv; vec4 w = modelMatrix*vec4(position,1.0); vN = normalize(mat3(modelMatrix)*normal); vV = normalize(cameraPosition - w.xyz); gl_Position = projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `uniform vec3 uCol; uniform float uStr; varying vec2 vUv; varying vec3 vN; varying vec3 vV;
      void main(){ float edge = pow(abs(dot(normalize(vN), normalize(vV))), 1.5); float a = pow(1.0 - vUv.y, 1.6) * edge * uStr; gl_FragColor = vec4(uCol*a*0.35, 1.0); }`,
  });
}

// Final pass: upscale, directional motion blur, chromatic split, grain,
// vignette, flash, glitch, caption overlay.
export const FinalShader = {
  uniforms: {
    tDiffuse: { value: null }, tOv: { value: null }, uHasOv: { value: 0 },
    uRes: { value: new THREE.Vector2(1080, 1920) }, uBlur: { value: new THREE.Vector2() }, uTime: { value: 0 },
    uFlash: { value: 0 }, uFlashCol: { value: new THREE.Color(1, 1, 1) }, uGlitch: { value: 0 }, uSat: { value: 1.1 }, uVig: { value: 0.9 }, uCA: { value: 1 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse; uniform sampler2D tOv; uniform float uHasOv; uniform vec2 uRes; uniform vec2 uBlur; uniform float uTime;
    uniform float uFlash; uniform vec3 uFlashCol; uniform float uGlitch; uniform float uSat; uniform float uVig; uniform float uCA;
    varying vec2 vUv;
    float hash(vec2 p){ p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); return fract(p.x*p.y); }
    void main(){
      vec2 uv = vUv;
      if (uGlitch > 0.0) {
        float row = floor(uv.y*60.0);
        float g = step(1.0 - uGlitch*0.35, hash(vec2(row, floor(uTime*24.0))));
        uv.x += (hash(vec2(row, uTime)) - 0.5) * 0.08 * g * uGlitch;
      }
      vec2 d = uBlur / uRes;
      vec2 ca = (uv - 0.5) * 0.004 * uCA + d*0.15;
      vec3 col = vec3(0.0);
      float amt = length(uBlur);
      int N = amt > 1.5 ? 12 : 1;
      float j = 0.0;
      for (int i = 0; i < 12; i++) {
        if (i >= N) break;
        float f = N == 1 ? 0.0 : ((float(i)+j)/11.0 - 0.5);
        vec2 o = d*f;
        col.r += texture2D(tDiffuse, uv + o + ca).r;
        col.g += texture2D(tDiffuse, uv + o).g;
        col.b += texture2D(tDiffuse, uv + o - ca).b;
      }
      col /= float(N);
      float l = dot(col, vec3(0.299,0.587,0.114));
      col = mix(vec3(l), col, uSat);
      // filmic grain + vignette
      col += (hash(uv*uRes + fract(uTime*7.13)*100.0) - 0.5)*0.035;
      vec2 q = (uv-0.5)*vec2(1.0,0.75);
      col *= mix(1.0, smoothstep(0.85, 0.2, length(q)), uVig*0.55);
      col = mix(col, uFlashCol, uFlash);
      if (uHasOv > 0.5) { vec4 ov = texture2D(tOv, vUv); col = col*(1.0-ov.a) + ov.rgb*ov.a; }
      gl_FragColor = vec4(col, 1.0);
    }`,
};
