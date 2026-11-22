// GSAP-driven camera rig. Each shot gets a paused gsap.timeline that is
// *seeked* to the frame time, so playback is fully deterministic.
import gsap from 'gsap';
import { noise1, clamp } from './util.js';

const WHIP_PX = 420; // screen px a whip travels at the reference depth
const REF_D = 2.5;
const DIRS = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] };

export function buildCamera(shot) {
  const c = shot.camera || {};
  const D = shot.dur;
  const from = { x: 0, y: 0, z: 0, zoom: 1, roll: 0, ...(c.from || {}) };
  const to = { ...from, ...(c.to || {}) };
  const st = { ...from, wx: 0, wy: 0, wr: 0 };
  const tl = gsap.timeline({ paused: true });
  tl.to(st, { x: to.x, y: to.y, z: to.z, zoom: to.zoom, roll: to.roll, duration: D, ease: c.ease || 'power1.inOut' }, 0);
  const whipAmt = (dir) => {
    const v = DIRS[dir] || [1, 0];
    return { wx: (v[0] * WHIP_PX * REF_D) / from.zoom, wy: (v[1] * WHIP_PX * REF_D) / from.zoom, wr: v[0] * 4 };
  };
  const inDur = Math.min(0.42, D * 0.18);
  const outDur = Math.min(0.32, D * 0.12);
  if (c.whipIn) {
    const a = whipAmt(c.whipIn);
    tl.fromTo(st, { wx: -a.wx, wy: -a.wy, wr: -a.wr }, { wx: 0, wy: 0, wr: 0, duration: inDur, ease: 'expo.out', immediateRender: true }, 0);
  }
  if (c.whipOut) {
    const a = whipAmt(c.whipOut);
    tl.fromTo(st, { wx: 0, wy: 0, wr: 0 }, { wx: a.wx, wy: a.wy, wr: a.wr, duration: outDur, ease: 'expo.in', immediateRender: false }, D - outDur);
  }
  const shake = c.shake || 0;
  return {
    at(lt) {
      tl.seek(clamp(lt, 0, D), true);
      const sx = shake ? (noise1(lt * 9, 1) - 0.5) * 40 * shake : 0;
      const sy = shake ? (noise1(lt * 9, 2) - 0.5) * 40 * shake : 0;
      return { x: st.x + st.wx + sx, y: st.y + st.wy + sy, z: st.z, zoom: st.zoom, roll: st.roll + st.wr };
    },
  };
}

// Screen-space blur vector (px) from the camera's motion between two frames,
// measured at the reference depth. Also returns a zoom-blur amount.
export function motionBlur(a, b, fps = 30) {
  const proj = (cam) => {
    const dz = Math.max(0.1, REF_D - cam.z);
    return [(-cam.zoom * cam.x) / dz, (-cam.zoom * cam.y) / dz, (cam.zoom * REF_D) / dz];
  };
  const pa = proj(a), pb = proj(b);
  const shutter = 0.55;
  let bx = (pb[0] - pa[0]) * shutter, by = (pb[1] - pa[1]) * shutter;
  const rollPx = ((b.roll - a.roll) * Math.PI / 180) * 600 * shutter;
  bx += rollPx * 0.3;
  const len = Math.hypot(bx, by);
  const maxL = 90;
  if (len > maxL) { bx *= maxL / len; by *= maxL / len; }
  const zoom = clamp(Math.abs(pb[2] / pa[2] - 1) * 2.2 * shutter, 0, 0.06);
  return { bx, by, zoom };
}
