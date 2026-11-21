// WebGL post pass: neon bloom (two pre-blurred mips), faint chromatic aberration, CRT scanlines,
// vignette, grain, sonar-ripple refraction during wipes, and the one-frame glitch.
const VS = `attribute vec2 p; varying vec2 vUv; void main(){ vUv = p*0.5+0.5; gl_Position = vec4(p,0.,1.); }`;
const FS = `
precision highp float;
varying vec2 vUv;
uniform sampler2D uScene, uB1, uB2;
uniform vec2 uRes;
uniform float uTime, uRing, uGlitch, uPulse, uAberr, uScale;
uniform vec2 uCenter;
uniform vec3 uRingCol;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
void main(){
  vec2 uv = vUv;
  vec2 px = uv * uRes;
  float k = 0.0;
  if (uRing > 0.0) {
    vec2 d = px - uCenter; float dist = length(d);
    k = exp(-pow((dist - uRing) / (34.0 * uScale), 2.0));
    uv -= normalize(d + 1e-4) * k * 14.0 * uScale / uRes;
  }
  if (uGlitch > 0.0) {
    float row = floor(uv.y * 64.0);
    float h = hash(vec2(row, floor(uTime * 30.0)));
    float band = step(0.55, h);
    uv.x += band * (h - 0.75) * 0.22 * uGlitch;
    uv.y += step(0.93, h) * 0.02 * uGlitch;
  }
  vec2 dir = uv - 0.5;
  float ab = uAberr * (0.4 + 1.6 * dot(dir, dir)) + uGlitch * 0.012;
  vec3 col;
  col.r = texture2D(uScene, uv + dir * ab).r;
  col.g = texture2D(uScene, uv).g;
  col.b = texture2D(uScene, uv - dir * ab).b;
  vec3 bg = vec3(0.008, 0.024, 0.051);
  vec3 b1 = max(texture2D(uB1, uv).rgb - bg, 0.0), b2 = max(texture2D(uB2, uv).rgb - bg, 0.0);
  col += b1 * 0.95 + b2 * 0.85;
  col += uRingCol * k * 0.35;
  col *= 1.0 + uPulse;
  // CRT scanlines (3 px period at 1080x1920) + slow rolling band
  float sl = 0.5 + 0.5 * sin(gl_FragCoord.y * 6.2831853 / (3.0 * uScale));
  col *= 0.84 + 0.16 * sl;
  col *= 0.97 + 0.03 * sin(vUv.y * 9.0 - uTime * 1.3);
  float v = smoothstep(1.05, 0.35, length((vUv - 0.5) * vec2(1.0, 0.75)));
  col *= mix(0.55, 1.0, v);
  col += (hash(gl_FragCoord.xy * 0.73 + floor(uTime * 12.0)) - 0.5) * 0.018;
  col = max(col, vec3(0.008, 0.024, 0.05) * 0.9);
  gl_FragColor = vec4(min(col, 1.0), 1.0);
}`;

export function createPost(canvas, W, H) {
  const gl = canvas.getContext('webgl', { preserveDrawingBuffer: true, antialias: false, alpha: false });
  if (!gl) throw new Error('WebGL unavailable');
  const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o); if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
  if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
  gl.useProgram(pr);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  const tex = (unit) => { const t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, t); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE); return t; };
  const T = [tex(0), tex(1), tex(2)];
  const U = (n) => gl.getUniformLocation(pr, n);
  gl.uniform1i(U('uScene'), 0); gl.uniform1i(U('uB1'), 1); gl.uniform1i(U('uB2'), 2);
  const u = { res: U('uRes'), time: U('uTime'), ring: U('uRing'), glitch: U('uGlitch'), pulse: U('uPulse'), aberr: U('uAberr'), scale: U('uScale'), center: U('uCenter'), ringCol: U('uRingCol') };
  gl.viewport(0, 0, W, H);
  return function render(scene, b1, b2, p) {
    [scene, b1, b2].forEach((c, i) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, T[i]); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, c); });
    gl.uniform2f(u.res, W, H); gl.uniform1f(u.time, p.time); gl.uniform1f(u.ring, p.ring || 0); gl.uniform1f(u.glitch, p.glitch || 0);
    gl.uniform1f(u.pulse, p.pulse || 0); gl.uniform1f(u.aberr, p.aberr ?? 0.0035); gl.uniform1f(u.scale, W / 1080);
    gl.uniform2f(u.center, p.cx || W / 2, p.cy || H / 2); gl.uniform3f(u.ringCol, ...(p.ringCol || [0.1, 0.94, 1]));
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  };
}
