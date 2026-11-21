// DOM overlay layer driven by a paused GSAP timeline (seeked per frame):
// title card, word-by-word captions, SVG line-draw handwriting, end card.
import gsap from 'gsap';

const SVGNS = 'http://www.w3.org/2000/svg';

export class Overlay {
  constructor(root, tl) {
    this.tl = tl;
    this.root = root;
    this.gs = gsap.timeline({ paused: true });
    this.buildTitle();
    this.buildEnd();
    this.buildCaptions();
    this.buildHandwriting();
  }

  buildTitle() {
    const c = this.tl.titleCard;
    const el = document.createElement('div');
    el.className = 'card title-card';
    el.innerHTML = `<div class="kicker">${c.kicker}</div><div class="rule"></div>
      <h1>${c.title.split(' ').map((w) => `<span>${w}</span>`).join(' ')}</h1>
      <div class="part">${c.subtitle}</div>`;
    this.root.appendChild(el);
    const words = el.querySelectorAll('h1 span');
    this.gs.set(el, { autoAlpha: 1 }, 0);
    this.gs.fromTo(el.querySelector('.kicker'), { autoAlpha: 0, y: 12 }, { autoAlpha: 0.85, y: 0, duration: 0.9, ease: 'power2.out' }, 0.25);
    this.gs.fromTo(el.querySelector('.rule'), { scaleX: 0 }, { scaleX: 1, duration: 1.2, ease: 'power3.inOut' }, 0.35);
    this.gs.fromTo(words, { autoAlpha: 0, y: 28, filter: 'blur(8px)' }, { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 1.1, stagger: 0.12, ease: 'power3.out' }, 0.45);
    this.gs.fromTo(el.querySelector('.part'), { autoAlpha: 0, letterSpacing: '0.1em' }, { autoAlpha: 1, letterSpacing: '0.55em', duration: 1.4, ease: 'power2.out' }, 1.1);
    this.gs.to(el, { autoAlpha: 0, y: -18, filter: 'blur(6px)', duration: 0.9, ease: 'power2.in' }, c.duration - 0.9);
  }

  buildEnd() {
    const c = this.tl.endCard;
    const el = document.createElement('div');
    el.className = 'card end-card';
    const [part, follow] = c.text.split('—').map((s) => s.trim());
    el.innerHTML = `<div class="series">${c.title}</div><div class="rule"></div>
      <h2>${part}</h2><div class="follow">${follow || ''}</div>`;
    this.root.appendChild(el);
    this.gs.set(el, { autoAlpha: 0 }, 0);
    const t = c.start + 0.35;
    this.gs.fromTo(el.querySelector('.series'), { autoAlpha: 0 }, { autoAlpha: 0.7, duration: 0.8 }, t);
    this.gs.set(el, { autoAlpha: 1 }, t);
    this.gs.fromTo(el.querySelector('.rule'), { scaleX: 0 }, { scaleX: 1, duration: 1.0, ease: 'power3.inOut' }, t + 0.2);
    this.gs.fromTo(el.querySelector('h2'), { autoAlpha: 0, scale: 1.12, filter: 'blur(10px)' }, { autoAlpha: 1, scale: 1, filter: 'blur(0px)', duration: 1.2, ease: 'power3.out' }, t + 0.35);
    this.gs.fromTo(el.querySelector('.follow'), { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 1.0, ease: 'power2.out' }, t + 1.3);
    this.gs.to(el.querySelector('h2'), { x: 0, duration: 0.01 }, c.start + c.duration);
  }

  buildCaptions() {
    const wrap = document.createElement('div');
    wrap.className = 'captions';
    this.root.appendChild(wrap);
    this.chunks = this.tl.captions.map((c) => {
      const el = document.createElement('div');
      const whisper = this.tl.scenes[c.scene]?.whisper;
      el.className = 'chunk' + (whisper ? ' whisper' : '');
      const spans = c.words.map((w) => {
        const s = document.createElement('span');
        s.className = 'w';
        s.textContent = w.w;
        el.appendChild(s);
        el.appendChild(document.createTextNode(' '));
        return s;
      });
      wrap.appendChild(el);
      return { ...c, el, spans };
    });
  }

  buildHandwriting() {
    this.hands = (this.tl.overlays || []).filter((o) => o.type === 'handwriting').map((o) => {
      const svg = document.createElementNS(SVGNS, 'svg');
      svg.setAttribute('class', 'hand');
      svg.setAttribute('viewBox', '0 0 1000 300');
      const g = document.createElementNS(SVGNS, 'g');
      svg.appendChild(g);
      this.root.appendChild(svg);
      // two lines, each letter its own <text> so the stroke dash draws letter by letter
      const words = o.text.split(' ');
      const mid = Math.ceil(words.length / 2);
      const lines = [words.slice(0, mid).join(' '), words.slice(mid).join(' ')];
      const letters = [];
      const probe = document.createElementNS(SVGNS, 'text');
      probe.setAttribute('class', 'hand-text');
      g.appendChild(probe);
      lines.forEach((line, li) => {
        probe.textContent = line;
        const total = probe.getComputedTextLength();
        const x0 = 500 - total / 2;
        for (let i = 0; i < line.length; i++) {
          if (line[i] === ' ') continue;
          const x = x0 + (line.length > 1 ? probe.getStartPositionOfChar(i).x : 0);
          const t = document.createElementNS(SVGNS, 'text');
          t.setAttribute('class', 'hand-text');
          t.setAttribute('x', x.toFixed(1));
          t.setAttribute('y', (120 + li * 120).toString());
          t.textContent = line[i];
          t.style.strokeDasharray = '420 420';
          t.style.strokeDashoffset = '420';
          t.style.fillOpacity = '0';
          g.appendChild(t);
          letters.push(t);
        }
      });
      probe.remove();
      const dur = Math.max(1, o.to - o.from);
      const per = dur / letters.length;
      this.gs.set(svg, { autoAlpha: 0 }, 0);
      this.gs.set(svg, { autoAlpha: 1 }, o.from);
      letters.forEach((t, i) => {
        const s = o.from + i * per * 0.92;
        this.gs.fromTo(t, { strokeDashoffset: 420 }, { strokeDashoffset: 0, duration: per * 2.2, ease: 'power1.inOut' }, s);
        this.gs.fromTo(t, { fillOpacity: 0 }, { fillOpacity: 1, duration: 0.6, ease: 'power1.in' }, s + per * 1.4);
      });
      const sc = this.tl.scenes[o.scene];
      this.gs.to(svg, { autoAlpha: 0, duration: 1.2, ease: 'power2.in' }, sc.end + 0.2);
      return { ...o, svg };
    });
  }

  // per-frame update
  update(t, { project, glitch = 0, w, h }) {
    this.gs.seek(t, false);
    // captions
    for (const c of this.chunks) {
      const vis = Math.min(1, (t - c.start) / 0.2, (c.end - t) / 0.28);
      if (vis <= 0) { if (c.el.style.display !== 'none') c.el.style.display = 'none'; continue; }
      c.el.style.display = 'block';
      c.el.style.opacity = vis.toFixed(3);
      c.el.style.transform = `translate(-50%, ${((1 - vis) * 10).toFixed(1)}px)` + (glitch > 0.05 ? ` translateX(${((Math.sin(t * 91) * 30) * glitch).toFixed(1)}px)` : '');
      c.words.forEach((wd, i) => {
        const s = c.spans[i];
        const k = (t - wd.t0) / Math.max(0.05, wd.t1 - wd.t0);
        let cls = 'w';
        if (k >= 0 && k < 1.15) cls = 'w on';
        else if (k >= 1.15) cls = 'w done';
        if (s.className !== cls) s.className = cls;
      });
    }
    // handwriting anchored to the 3D door
    for (const hnd of this.hands) {
      if (t < hnd.from - 0.1 || t > this.tl.scenes[hnd.scene].end + 1.5) continue;
      const p = project(hnd.anchor);
      const p2 = project([hnd.anchor[0] + 1, hnd.anchor[1], hnd.anchor[2]]);
      const metre = Math.hypot(p2.x - p.x, p2.y - p.y);
      const width = Math.min(metre * 0.95, w * 0.86);
      const left = Math.min(Math.max(p.x - width / 2, w * 0.07), w * 0.93 - width);
      hnd.svg.style.width = `${width.toFixed(1)}px`;
      hnd.svg.style.left = `${left.toFixed(1)}px`;
      hnd.svg.style.top = `${(p.y - width * 0.15).toFixed(1)}px`;
    }
  }
}
