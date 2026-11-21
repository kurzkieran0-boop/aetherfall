// Post-processing: HDR scene -> quarter-res screen-space god-rays -> composite
// (tone map, split-tone grade, chromatic aberration, vignette, film grain,
//  reset glitch: horizontal tear + rewind blur + flash, fades).
import * as THREE from 'three';

const quadGeo = new THREE.BufferGeometry();
quadGeo.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
const VERT = `varying vec2 vUv; void main(){ vUv = position.xy * 0.5 + 0.5; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

export class Post {
  constructor(renderer, w, h, { scale = 0.75, samples = 0 } = {}) {
    this.renderer = renderer;
    const sw = Math.round(w * scale), sh = Math.round(h * scale);
    this.rtScene = new THREE.WebGLRenderTarget(sw, sh, { type: THREE.HalfFloatType, samples, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
    this.rtRays = new THREE.WebGLRenderTarget(Math.ceil(w / 5), Math.ceil(h / 5), { type: THREE.HalfFloatType });
    // bloom: bright-pass + separable blur at 1/4 res
    const bw = Math.ceil(w / 4), bh = Math.ceil(h / 4);
    this.rtB1 = new THREE.WebGLRenderTarget(bw, bh, { type: THREE.HalfFloatType });
    this.rtB2 = new THREE.WebGLRenderTarget(bw, bh, { type: THREE.HalfFloatType });
    this.brightMat = new THREE.ShaderMaterial({
      uniforms: { tScene: { value: null }, thr: { value: 1.1 } }, vertexShader: VERT,
      fragmentShader: `uniform sampler2D tScene; uniform float thr; varying vec2 vUv;
        void main(){ vec3 c = texture2D(tScene, vUv).rgb; float l = dot(c, vec3(0.299,0.587,0.114));
          gl_FragColor = vec4(c * smoothstep(thr, thr + 1.2, l), 1.0); }`,
    });
    this.blurMat = new THREE.ShaderMaterial({
      uniforms: { tSrc: { value: null }, dir: { value: new THREE.Vector2() } }, vertexShader: VERT,
      fragmentShader: `uniform sampler2D tSrc; uniform vec2 dir; varying vec2 vUv;
        void main(){ vec3 a = texture2D(tSrc, vUv).rgb * 0.227;
          a += (texture2D(tSrc, vUv + dir * 1.385).rgb + texture2D(tSrc, vUv - dir * 1.385).rgb) * 0.316;
          a += (texture2D(tSrc, vUv + dir * 3.231).rgb + texture2D(tSrc, vUv - dir * 3.231).rgb) * 0.070;
          gl_FragColor = vec4(a, 1.0); }`,
    });
    this.bw = bw; this.bh = bh;
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    this.raysMat = new THREE.ShaderMaterial({
      uniforms: { tScene: { value: null }, sun: { value: new THREE.Vector2(0.5, 0.5) }, aspect: { value: w / h }, onScreen: { value: 1 } },
      vertexShader: VERT,
      fragmentShader: `uniform sampler2D tScene; uniform vec2 sun; uniform float aspect, onScreen; varying vec2 vUv;
        void main(){
          vec2 d = (vUv - sun);
          float dist = length(d * vec2(aspect, 1.0));
          vec2 stepv = d * (1.0 / 40.0) * 0.92;
          vec2 uv = vUv; float illum = 1.0; vec3 acc = vec3(0.0);
          for (int i = 0; i < 40; i++) {
            uv -= stepv;
            vec3 c = texture2D(tScene, uv).rgb;
            float l = dot(c, vec3(0.299, 0.587, 0.114));
            acc += c * smoothstep(1.05, 2.6, l) * illum;
            illum *= 0.965;
          }
          acc /= 40.0;
          gl_FragColor = vec4(acc * onScreen * exp(-dist * 1.1), 1.0);
        }`,
    });
    this.compMat = new THREE.ShaderMaterial({
      uniforms: {
        tScene: { value: null }, tRays: { value: null }, tBloom: { value: null }, bloom: { value: 0.55 }, whip: { value: 0 }, whipDir: { value: 1 }, res: { value: new THREE.Vector2(w, h) }, sceneTexel: { value: new THREE.Vector2(1 / sw, 1 / sh) },
        time: { value: 0 }, frame: { value: 0 }, exposure: { value: 1 },
        raysColor: { value: new THREE.Color(1, 0.8, 0.55) }, raysAmt: { value: 1 },
        glitch: { value: 0 }, rewind: { value: 0 }, seed: { value: 0 }, flash: { value: 0 },
        fade: { value: 0 }, shadowTint: { value: new THREE.Color(0x0f3a44) }, highlightTint: { value: new THREE.Color(0xffe9c7) },
        ca: { value: 0.0016 }, grain: { value: 0.06 }, vignette: { value: 0.55 },
      },
      vertexShader: VERT,
      fragmentShader: `uniform sampler2D tScene, tRays; uniform vec2 res; uniform float time, frame, exposure, raysAmt,
          glitch, rewind, seed, flash, fade, ca, grain, vignette, bloom, whip, whipDir; uniform sampler2D tBloom;
        uniform vec3 raysColor, shadowTint, highlightTint; uniform vec2 sceneTexel; varying vec2 vUv;
        float lumaT(vec3 c){ float l = dot(c, vec3(0.299, 0.587, 0.114)); return l / (1.0 + l); }
        vec3 fxaa(vec2 uv){
          vec3 cM = texture2D(tScene, uv).rgb;
          float lNW = lumaT(texture2D(tScene, uv + vec2(-1.0, -1.0) * sceneTexel).rgb);
          float lNE = lumaT(texture2D(tScene, uv + vec2(1.0, -1.0) * sceneTexel).rgb);
          float lSW = lumaT(texture2D(tScene, uv + vec2(-1.0, 1.0) * sceneTexel).rgb);
          float lSE = lumaT(texture2D(tScene, uv + vec2(1.0, 1.0) * sceneTexel).rgb);
          float lM = lumaT(cM);
          float lMin = min(lM, min(min(lNW, lNE), min(lSW, lSE)));
          float lMax = max(lM, max(max(lNW, lNE), max(lSW, lSE)));
          if (lMax - lMin < 0.04) return cM;
          vec2 dir = vec2(-((lNW + lNE) - (lSW + lSE)), (lNW + lSW) - (lNE + lSE));
          float red = max((lNW + lNE + lSW + lSE) * 0.03125, 1.0 / 128.0);
          dir = clamp(dir / (min(abs(dir.x), abs(dir.y)) + red), -8.0, 8.0) * sceneTexel;
          vec3 a = 0.5 * (texture2D(tScene, uv + dir * (1.0/3.0 - 0.5)).rgb + texture2D(tScene, uv + dir * (2.0/3.0 - 0.5)).rgb);
          vec3 b = a * 0.5 + 0.25 * (texture2D(tScene, uv - dir * 0.5).rgb + texture2D(tScene, uv + dir * 0.5).rgb);
          float lB = lumaT(b);
          return (lB < lMin || lB > lMax) ? a : b;
        }
        float hash(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
        vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0); }
        vec3 sampleCA(vec2 uv, float amt){
          vec2 dir = (uv - 0.5);
          return vec3(texture2D(tScene, uv + dir * amt).r, texture2D(tScene, uv).g, texture2D(tScene, uv - dir * amt).b);
        }
        void main(){
          vec2 uv = vUv;
          // --- reset glitch: horizontal tear
          if (glitch > 0.001) {
            float rows = 18.0 + 30.0 * hash(vec2(seed, 1.0));
            float band = floor(uv.y * rows);
            float r = hash(vec2(band, seed));
            float on = step(1.0 - 0.55 * glitch, r);
            uv.x += on * (hash(vec2(band, seed + 3.1)) - 0.5) * 0.22 * glitch;
            uv.y += on * (hash(vec2(band, seed + 7.7)) - 0.5) * 0.01 * glitch;
            // big tear line
            float tearY = fract(seed * 0.618);
            float tear = smoothstep(0.02, 0.0, abs(uv.y - tearY)) * glitch;
            uv.x += tear * 0.12;
          }
          // --- rewind: vertical roll + streak blur
          uv.y = fract(uv.y + rewind * rewind * 0.35 * sin(time * 9.0));
          vec3 col;
          float amt = ca + glitch * 0.02 + rewind * 0.01;
          if (whip > 0.01) {
            col = vec3(0.0);
            for (int i = 0; i < 11; i++) {
              float o = (float(i) - 5.0) / 5.0;
              col += texture2D(tScene, uv + vec2(o * 0.14 * whip * whipDir, o * 0.01 * whip)).rgb;
            }
            col /= 11.0;
          } else if (rewind > 0.01) {
            col = vec3(0.0);
            for (int i = 0; i < 9; i++) {
              float o = (float(i) - 4.0) / 4.0;
              col += sampleCA(uv + vec2(o * 0.025 * rewind, o * 0.06 * rewind), amt);
            }
            col /= 9.0;
          } else {
            col = fxaa(uv);
            vec2 cd = (uv - 0.5) * amt;
            col.r = mix(col.r, texture2D(tScene, uv + cd).r, 0.65);
            col.b = mix(col.b, texture2D(tScene, uv - cd).b, 0.65);
          }
          col += texture2D(tRays, uv).rgb * raysColor * raysAmt * 1.6;
          col += texture2D(tBloom, uv).rgb * bloom;
          // tone map + grade (split toning: teal shadows, cream/amber highlights)
          col = aces(col * exposure);
          col = pow(col, vec3(1.0 / 2.2));
          float l = dot(col, vec3(0.299, 0.587, 0.114));
          col = mix(col, col * (shadowTint * 1.9 + 0.35), (1.0 - smoothstep(0.0, 0.45, l)) * 0.38);
          col = mix(col, col * highlightTint * 1.08, smoothstep(0.45, 1.0, l) * 0.3);
          col = mix(vec3(l), col, 1.08); // slight saturation boost
          // rewind/glitch colour bleed + scanlines
          if (glitch + rewind > 0.01) {
            float g = max(glitch, rewind);
            col = mix(col, vec3(l) * vec3(0.8, 1.0, 1.05), 0.35 * g);
            col *= 1.0 - 0.18 * g * step(0.5, fract(vUv.y * res.y * 0.25));
            float trk = smoothstep(0.04, 0.0, abs(fract(vUv.y - time * 1.7) - 0.5)) * rewind;
            col += trk * (hash(vec2(floor(vUv.x * 160.0), frame)) * 0.6);
          }
          // vignette
          vec2 v = (vUv - 0.5) * vec2(res.x / min(res.x, res.y), res.y / min(res.x, res.y));
          float vig = smoothstep(1.05, 0.25, length(v * vec2(0.9, 0.75)));
          col *= mix(1.0, vig, vignette);
          // flash + fades (grain stays alive over black)
          col = mix(col, vec3(1.0, 0.93, 0.82), flash);
          col *= 1.0 - fade;
          // film grain (luma-weighted, per-frame deterministic)
          float n = hash(vUv * res + vec2(frame * 1.37, frame * 2.11)) - 0.5;
          col += n * grain * (0.6 + 0.4 * (1.0 - l)) * (1.0 - 0.6 * fade);
          gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
        }`,
    });
    this.quad = new THREE.Mesh(quadGeo, this.raysMat);
    this.quad.frustumCulled = false;
    this.qscene = new THREE.Scene();
    this.qscene.add(this.quad);
  }

  render(scene, camera, sunWorld) {
    const r = this.renderer;
    r.setRenderTarget(this.rtScene);
    r.render(scene, camera);
    // sun screen position
    const p = sunWorld.clone().project(camera);
    const behind = p.z > 1 || p.z < -1;
    const sun = new THREE.Vector2(p.x * 0.5 + 0.5, p.y * 0.5 + 0.5);
    const off = Math.max(0, Math.max(Math.abs(p.x), Math.abs(p.y)) - 1);
    this.raysMat.uniforms.sun.value.copy(sun);
    this.raysMat.uniforms.onScreen.value = behind ? 0 : Math.exp(-off * 1.4);
    this.raysMat.uniforms.tScene.value = this.rtScene.texture;
    this.quad.material = this.raysMat;
    // bloom chain
    this.brightMat.uniforms.tScene.value = this.rtScene.texture;
    this.quad.material = this.brightMat;
    r.setRenderTarget(this.rtB1); r.render(this.qscene, this.cam);
    this.blurMat.uniforms.tSrc.value = this.rtB1.texture; this.blurMat.uniforms.dir.value.set(1.6 / this.bw, 0);
    this.quad.material = this.blurMat;
    r.setRenderTarget(this.rtB2); r.render(this.qscene, this.cam);
    this.blurMat.uniforms.tSrc.value = this.rtB2.texture; this.blurMat.uniforms.dir.value.set(0, 1.6 / this.bh);
    r.setRenderTarget(this.rtB1); r.render(this.qscene, this.cam);
    this.compMat.uniforms.tBloom.value = this.rtB1.texture;
    this.quad.material = this.raysMat;
    r.setRenderTarget(this.rtRays);
    r.render(this.qscene, this.cam);
    this.compMat.uniforms.tScene.value = this.rtScene.texture;
    this.compMat.uniforms.tRays.value = this.rtRays.texture;
    this.quad.material = this.compMat;
    r.setRenderTarget(null);
    r.render(this.qscene, this.cam);
  }
}
