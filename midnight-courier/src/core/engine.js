// Frame engine: renderFrame(t) is a pure function of the resolved timeline
// and t, which is what makes parallel deterministic export possible.
import { W, H, makeCanvas, clamp, hex } from './util.js';
import { getPalette, lerpPalette } from './palettes.js';
import { buildCamera, motionBlur } from './camera.js';
import { Post } from './post.js';
import { Captions } from './captions.js';
import { win } from '../scenes/common.js';
import * as skyline from '../scenes/skyline.js';
import * as market from '../scenes/market.js';
import * as rooftops from '../scenes/rooftops.js';
import * as letter from '../scenes/letter.js';
import * as library from '../scenes/library.js';
import * as door from '../scenes/door.js';

export const SCENES = { skyline, market, rooftops, letter, library, door };

export class Engine {
  constructor(tl) {
    this.tl = tl;
    this.scene = makeCanvas(W, H);
    this.sctx = this.scene.getContext('2d');
    this.post = new Post();
    this.out = makeCanvas(W, H);
    this.octx = this.out.getContext('2d');
    this.captions = new Captions(tl, this.octx);
    this.cache = new Map();
    this.cams = new Map();
    this.fps = tl.fps || 30;
  }

  shotAt(t) {
    const S = this.tl.shots;
    let lo = 0, hi = S.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (S[mid].start <= t + 1e-6) lo = mid; else hi = mid - 1;
    }
    return S[lo];
  }

  sceneKey(shot) { return `${shot.scene}|${shot.palette}|${JSON.stringify(shot.sceneOpts || {})}`; }

  getScene(shot) {
    const key = this.sceneKey(shot);
    let st = this.cache.get(key);
    if (st) { this.cache.delete(key); this.cache.set(key, st); return st; }
    const mod = SCENES[shot.scene];
    if (!mod) throw new Error('Unknown scene ' + shot.scene);
    st = mod.build(getPalette(shot.palette), shot.sceneOpts || {}, shot.seed ?? 7);
    this.cache.set(key, st);
    while (this.cache.size > 3) this.cache.delete(this.cache.keys().next().value);
    return st;
  }

  // Pre-build every scene a range of frames needs (avoids hitches mid-capture).
  warm(t0, t1) {
    for (const s of this.tl.shots) if (s.end > t0 && s.start < t1) this.getScene(s);
  }

  cam(shot) {
    let c = this.cams.get(shot.id);
    if (!c) { c = buildCamera(shot); this.cams.set(shot.id, c); }
    return c;
  }

  render(t) {
    const shot = this.shotAt(t);
    const lt = t - shot.start;
    const dur = shot.dur;
    const p = clamp(lt / dur);
    const rig = this.cam(shot);
    const dt = 1 / this.fps;
    const cam = rig.at(lt);
    const a = lt - dt >= 0 ? rig.at(lt - dt) : cam;
    const b = lt - dt >= 0 ? cam : rig.at(lt + dt);
    const blur = motionBlur({ ...a }, { ...b }, this.fps);
    rig.at(lt);
    const fx = shot.fx || {};
    const pal = getPalette(shot.palette);
    let skyPal = pal;
    if (fx.dawn) skyPal = lerpPalette(pal, getPalette(fx.dawnTo || 'predawn'), win(p, fx.dawn[0], fx.dawn[1]));
    const beatDur = 60 / this.tl.bpm;
    const beatPhase = ((t / beatDur) % 1 + 1) % 1;
    const f = {
      t, lt, p, dur, shot, cam, fx, pal, skyPal, beatPhase, beatDur,
      pt: fx.freeze ? shot.start : t,
      line: this.lineAt(t),
    };
    const ctx = this.sctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    const st = this.getScene(shot);
    SCENES[shot.scene].render(ctx, f, st);
    // flashes: on cut (shot.flashIn) and timed events (fx.flash: [[p, strength]])
    let flash = 0;
    if (shot.flashIn) flash = Math.max(flash, shot.flashIn * Math.exp(-lt * 9));
    for (const fl of fx.flash || []) {
      const ft = fl[0] * dur;
      if (lt >= ft) flash = Math.max(flash, fl[1] * Math.exp(-(lt - ft) * 6));
    }
    const g = shot.grade || {};
    const o = this.octx;
    o.setTransform(1, 0, 0, 1, 0, 0);
    o.clearRect(0, 0, W, H);
    this.captions.draw(o, t, beatPhase);
    const out = this.post.apply(this.scene, {
      bx: blur.bx, by: blur.by, zoom: blur.zoom, time: t, flash: clamp(flash),
      flashCol: g.flashCol ? hex(g.flashCol).map((v) => v / 255) : [1, 0.93, 0.74],
      sat: g.sat !== undefined ? g.sat + (g.satTo !== undefined ? (g.satTo - g.sat) * p : 0) : 1.06,
      tint: g.tint ? hex(g.tint).map((v) => v / 255) : [1, 1, 1], tintAmt: g.tintAmt || 0,
      vig: g.vig ?? 0.85, grain: 1,
    }, this.out);
    return out;
  }

  lineAt(t) {
    for (const l of this.tl.lines) if (t >= l.start - 0.05 && t < l.end + 0.3) return l;
    return null;
  }
}
