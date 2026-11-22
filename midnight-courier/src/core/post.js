// WebGL2 post pass: directional + zoom motion blur, slight chromatic split on
// fast moves, paper grain, vignette, flash and a simple grade (saturation,
// lift). Falls back to a pass-through 2D copy if WebGL2 is unavailable.
import { W, H } from './util.js';

const VS = `#version 300 es
in vec2 p; out vec2 vUv;
void main(){ vUv = p*0.5+0.5; gl_Position = vec4(p,0.,1.); }`;

const FS = `#version 300 es
precision highp float;
uniform sampler2D uTex; uniform sampler2D uPaper; uniform sampler2D uOv; uniform float uHasOv;
uniform vec2 uRes; uniform vec2 uBlur; uniform float uZoom; uniform float uTime;
uniform float uFlash; uniform vec3 uFlashCol; uniform float uSat; uniform vec3 uTint; uniform float uTintAmt;
uniform float uVig; uniform float uGrain;
in vec2 vUv; out vec4 o;
float hash(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
void main(){
  vec2 uv = vec2(vUv.x, 1.0 - vUv.y);
  vec2 dir = uBlur / uRes;
  vec2 zc = (uv - 0.5) * uZoom;
  float amt = length(uBlur) + uZoom*800.0;
  vec3 col;
  if (amt < 1.5) {
    col = texture(uTex, uv).rgb;
  } else {
    col = vec3(0.0);
    float jitter = hash(uv*uRes + uTime) - 0.5;
    for (int i = 0; i < 14; i++) {
      float f = (float(i) + jitter) / 13.0 - 0.5;
      vec2 off = dir*f + zc*f;
      vec2 ca = dir * 0.12;
      col.r += texture(uTex, uv + off + ca).r;
      col.g += texture(uTex, uv + off).g;
      col.b += texture(uTex, uv + off - ca).b;
    }
    col /= 14.0;
  }
  // grade
  float l = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(vec3(l), col, uSat);
  col = mix(col, col * uTint * 1.6, uTintAmt);
  // paper grain: static fibre texture + animated fine grain
  vec3 paper = texture(uPaper, uv * vec2(uRes.x/512.0, uRes.y/512.0)).rgb;
  col *= mix(1.0, 0.86 + paper.r*0.22, uGrain);
  col += (hash(uv*uRes + fract(uTime*7.13)*100.0) - 0.5) * 0.045 * uGrain;
  // vignette
  vec2 q = (uv - 0.5) * vec2(1.0, 0.72);
  float v = smoothstep(0.78, 0.18, length(q));
  col *= mix(1.0, 0.55 + 0.45*v, uVig);
  col = mix(col, uFlashCol, uFlash);
  if (uHasOv > 0.5) { vec4 ov = texture(uOv, uv); col = col * (1.0 - ov.a) + ov.rgb * ov.a; }
  o = vec4(col, 1.0);
}`;

export class Post {
  constructor() {
    this.canvas = document.createElement('canvas');
    this.canvas.width = W;
    this.canvas.height = H;
    const gl = this.canvas.getContext('webgl2', { preserveDrawingBuffer: true, antialias: false, premultipliedAlpha: false });
    this.gl = gl;
    if (!gl) { this.fallback = true; this.ctx = this.canvas.getContext('2d'); return; }
    const sh = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
      return s;
    };
    const pr = gl.createProgram();
    gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS));
    gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(pr);
    gl.useProgram(pr);
    this.pr = pr;
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(pr, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    this.tex = this.mkTex(0);
    this.paper = this.mkTex(1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, paperTexture());
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    this.ov = this.mkTex(2);
    this.u = {};
    for (const n of ['uOv', 'uHasOv', 'uTex', 'uPaper', 'uRes', 'uBlur', 'uZoom', 'uTime', 'uFlash', 'uFlashCol', 'uSat', 'uTint', 'uTintAmt', 'uVig', 'uGrain']) this.u[n] = gl.getUniformLocation(pr, n);
    gl.uniform1i(this.u.uTex, 0);
    gl.uniform1i(this.u.uPaper, 1);
    gl.uniform1i(this.u.uOv, 2);
    gl.uniform2f(this.u.uRes, W, H);
    gl.viewport(0, 0, W, H);
  }
  mkTex(unit) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }
  apply(src, p, overlay = null) {
    if (this.fallback) { this.ctx.drawImage(src, 0, 0); if (overlay) this.ctx.drawImage(overlay, 0, 0); return this.canvas; }
    const gl = this.gl;
    gl.uniform1f(this.u.uHasOv, overlay ? 1 : 0);
    if (overlay) {
      gl.activeTexture(gl.TEXTURE2);
      gl.bindTexture(gl.TEXTURE_2D, this.ov);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, overlay);
    }
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src);
    gl.uniform2f(this.u.uBlur, p.bx || 0, p.by || 0);
    gl.uniform1f(this.u.uZoom, p.zoom || 0);
    gl.uniform1f(this.u.uTime, p.time || 0);
    gl.uniform1f(this.u.uFlash, p.flash || 0);
    const fc = p.flashCol || [1, 0.92, 0.7];
    gl.uniform3f(this.u.uFlashCol, fc[0], fc[1], fc[2]);
    gl.uniform1f(this.u.uSat, p.sat ?? 1.05);
    const tc = p.tint || [1, 1, 1];
    gl.uniform3f(this.u.uTint, tc[0], tc[1], tc[2]);
    gl.uniform1f(this.u.uTintAmt, p.tintAmt || 0);
    gl.uniform1f(this.u.uVig, p.vig ?? 0.8);
    gl.uniform1f(this.u.uGrain, p.grain ?? 1);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    return this.canvas;
  }
}

function paperTexture() {
  const S = 512;
  const c = document.createElement('canvas');
  c.width = c.height = S;
  const g = c.getContext('2d');
  const img = g.createImageData(S, S);
  // tileable value noise at a few octaves -> soft paper tooth
  const grid = (n, seed) => {
    const a = new Float32Array(n * n);
    let s = seed;
    for (let i = 0; i < a.length; i++) { s = (s * 1664525 + 1013904223) >>> 0; a[i] = s / 4294967296; }
    return a;
  };
  const octs = [[8, 0.35, grid(8, 1)], [32, 0.3, grid(32, 2)], [128, 0.2, grid(128, 3)], [512, 0.15, grid(512, 4)]];
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    let v = 0;
    for (const [n, amp, a] of octs) {
      const fx = (x / S) * n, fy = (y / S) * n;
      const ix = Math.floor(fx), iy = Math.floor(fy), tx = fx - ix, ty = fy - iy;
      const ux = tx * tx * (3 - 2 * tx), uy = ty * ty * (3 - 2 * ty);
      const g00 = a[(iy % n) * n + (ix % n)], g10 = a[(iy % n) * n + ((ix + 1) % n)];
      const g01 = a[((iy + 1) % n) * n + (ix % n)], g11 = a[((iy + 1) % n) * n + ((ix + 1) % n)];
      v += amp * ((g00 * (1 - ux) + g10 * ux) * (1 - uy) + (g01 * (1 - ux) + g11 * ux) * uy);
    }
    const k = (y * S + x) * 4;
    const b = Math.floor(v * 255);
    img.data[k] = img.data[k + 1] = img.data[k + 2] = b;
    img.data[k + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  // fibres
  let sd = 777;
  const rnd = () => { sd = (sd * 1664525 + 1013904223) >>> 0; return sd / 4294967296; };
  for (let i = 0; i < 500; i++) {
    const x = rnd() * S, y = rnd() * S, a = rnd() * 6.28, l = 8 + rnd() * 30;
    g.strokeStyle = rnd() < 0.5 ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.2)';
    g.lineWidth = 0.7;
    g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a + 0.6) * l / 2, y + Math.sin(a + 0.6) * l / 2, x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
  }
  return c;
}
