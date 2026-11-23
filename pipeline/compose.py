"""Final assembly: shot frames -> (upscale) -> colour grade per look -> vignette + film
grain -> impact flashes -> word-by-word captions -> H.264 1080x1920 @ 24fps + audio.
Frames rendered "on twos" are held for 2 frames (brick-film cadence)."""
import json
import os
import subprocess

import cv2
import numpy as np

from captions import CaptionRenderer

W, H, FPS = 1080, 1920, 24

GRADES = {
    # lift (shadows tint), gain (highlights tint), contrast, saturation, gamma
    "night_blue": dict(lift=(0.0, 0.012, 0.035), gain=(1.06, 1.0, 0.94), contrast=1.12, sat=1.08, gamma=0.97),
    "storm": dict(lift=(0.0, 0.015, 0.03), gain=(0.98, 1.0, 1.05), contrast=1.15, sat=0.92, gamma=0.98),
    "ember": dict(lift=(0.01, 0.01, 0.035), gain=(1.1, 1.0, 0.88), contrast=1.14, sat=1.12, gamma=0.96),
    "sunny": dict(lift=(0.0, 0.008, 0.03), gain=(1.05, 1.0, 0.94), contrast=1.14, sat=1.25, gamma=1.0),
    "toxic": dict(lift=(0.0, 0.02, 0.03), gain=(0.98, 1.06, 0.96), contrast=1.12, sat=1.05, gamma=0.97),
    # THE KINDNESS METER colour script: cold & lonely -> burning red -> warm gold
    "cold": dict(lift=(0.0, 0.012, 0.045), gain=(0.95, 1.0, 1.06), contrast=1.16, sat=1.02, gamma=0.98),
    "warm": dict(lift=(0.0, 0.01, 0.035), gain=(1.07, 1.0, 0.92), contrast=1.14, sat=1.1, gamma=0.98),
    "red": dict(lift=(0.025, 0.005, 0.02), gain=(1.12, 0.96, 0.86), contrast=1.2, sat=1.18, gamma=0.97),
    "gold": dict(lift=(0.015, 0.01, 0.02), gain=(1.12, 1.03, 0.84), contrast=1.12, sat=1.12, gamma=1.0),
}


def build_luts(look):
    g = GRADES.get(look, GRADES["night_blue"])
    x = np.linspace(0, 1, 256)
    luts = []
    for c in range(3):
        y = x ** g["gamma"]
        y = 0.5 + (y - 0.5) * g["contrast"]                    # contrast around mid
        y = y * g["gain"][c] + g["lift"][c] * (1 - y)          # split-tone: lift shadows, tint highs
        y = np.clip(y, 0, 1)
        # soft shoulder so highlights never hard-clip
        y = np.where(y > 0.9, 0.9 + (1 - np.exp(-(y - 0.9) * 6)) / 6 * 0.98, y)
        luts.append((np.clip(y, 0, 1) * 255).astype(np.uint8))
    return np.stack(luts, 1)  # 256 x 3


def vignette(strength=0.38, W=W, H=H):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 * 1.0 + ny ** 2 * 0.65)
    v = 1 - strength * np.clip((r - 0.45) / 0.85, 0, 1) ** 1.6
    return v[..., None].astype(np.float32)


def grain_bank(n=8, amount=5.0, seed=0, W=W, H=H):
    rng = np.random.default_rng(seed)
    bank = []
    for _ in range(n):
        gsm = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        gsm = cv2.resize(gsm, (W, H), interpolation=cv2.INTER_LINEAR)
        bank.append((gsm * amount)[..., None])
    return bank


def frame_source(shot_dir, meta, local_f):
    fr = meta["frames"]
    # hold: latest rendered frame <= local_f
    best = fr[0]
    for f in fr:
        if f <= local_f:
            best = f
        else:
            break
    return os.path.join(shot_dir, f"f_{best:04d}.png")


def compose(shotlist, shot_dirs, audio_wav, captions, out_mp4, look="night_blue", flashes=(), log=print,  # noqa
            preview=False, max_seconds=None, film=None, size=None):
    OW, OH = size or (W, H)
    v2 = film is not None and film.get("rig") == "v2"
    luts_cache = {}

    def luts_for(lk):
        if lk not in luts_cache:
            luts_cache[lk] = build_luts(lk)
        return luts_cache[lk]
    vig = vignette(0.42 if v2 else 0.38, OW, OH)
    grains = grain_bank(amount=5.5 if v2 else 5.0, W=OW, H=OH)
    cr = CaptionRenderer(OW, OH, size=int(118 * OW / 1080), stroke=max(4, int(12 * OW / 1080)))
    total = shotlist["total_frames"]
    tail = int(0.9 * FPS) if v2 else 0
    if max_seconds:
        total = min(total, int(max_seconds * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
           "-r", str(FPS), "-i", "-", "-i", audio_wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast" if preview else "slow", "-crf", "23" if preview else "19",
           "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    shots = shotlist["shots"]
    metas = {s["id"]: json.load(open(os.path.join(shot_dirs[s["id"]], "meta.json"))) for s in shots}
    ov = Overlays(film, shotlist, OW, OH) if v2 else None
    if v2:
        flashes = list(flashes) + ov.impact_times
    last_path, last_img, last_look = None, None, None
    si = 0
    cap_i = 0
    flash_frames = {}
    for fl in flashes:
        f0 = int(fl * FPS)
        for k, a in enumerate((0.85, 0.5, 0.2)):
            flash_frames[f0 + k] = max(flash_frames.get(f0 + k, 0), a)
    for n in range(total + tail):
        if n >= total:   # hard cut to black + held silence
            enc.stdin.write(np.zeros((OH, OW, 3), np.uint8).tobytes())
            continue
        while si + 1 < len(shots) and n >= shots[si + 1]["start_frame"]:
            si += 1
        s = shots[si]
        local = n - s["start_frame"] + 1
        p = frame_source(shot_dirs[s["id"]], metas[s["id"]], local)
        lk = s.get("act", look) if v2 else look
        if lk not in GRADES:
            lk = look
        if p != last_path or lk != last_look:
            img = cv2.imread(p, cv2.IMREAD_COLOR)[:, :, ::-1]
            if img.shape[1] != OW:
                img = cv2.resize(img, (OW, OH), interpolation=cv2.INTER_LANCZOS4)
                blur = cv2.GaussianBlur(img, (0, 0), 1.6 * OW / 1080)
                img = cv2.addWeighted(img, 1.45, blur, -0.45, 0)  # unsharp after upscale
            img = cv2.LUT(img, luts_for(lk).reshape(256, 1, 3))
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[..., 1] = np.clip(hsv[..., 1] * GRADES.get(lk, GRADES["night_blue"])["sat"], 0, 255)
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
            last_img, last_path, last_look = img, p, lk
        out = last_img.astype(np.float32) * vig + grains[(n // 2) % len(grains)]
        if n in flash_frames:
            out = out * (1 - flash_frames[n]) + 255 * flash_frames[n]
        if n < 4:
            out *= n / 4
        if not v2 and n > total - 18:
            out *= max(0, (total - n) / 18)
        out = np.clip(out, 0, 255).astype(np.uint8)
        t = n / FPS
        suppress = False
        if ov is not None:
            out, suppress = ov.draw(out, t)
        while cap_i + 1 < len(captions) and t >= captions[cap_i + 1]["s"]:
            cap_i += 1
        if captions and not suppress and captions[cap_i]["s"] <= t < captions[cap_i]["e"]:
            c = captions[cap_i]
            meta = metas[s["id"]]
            boxes = _boxes_at(meta, local)
            y = c.get("_y")
            if y is None or c.get("_shot") != s["id"]:
                y = cr.place_y(boxes, int(170 * OH / 1920))
                c["_y"], c["_shot"] = y, s["id"]
            out = cr.overlay(out, c["text"], t - c["s"], y)
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
        if n % 240 == 0:
            log(f"  [compose] {n}/{total} frames")
    enc.stdin.close()
    enc.wait()
    return out_mp4


class Overlays:
    """On-screen text for rig-v2 films: hook card, server banner, impact countdown, title cards."""

    def __init__(self, film, tl, OW, OH):
        from PIL import ImageFont
        from captions import font_path
        self.W, self.H = OW, OH
        self.k = OW / 1080
        fp = font_path()
        self.f_hook = ImageFont.truetype(fp, int(62 * self.k))
        self.f_card = ImageFont.truetype(fp, int(66 * self.k))
        self.f_ban = ImageFont.truetype(fp, int(46 * self.k))
        self.f_cnt = ImageFont.truetype(fp, int(52 * self.k))
        self.items = []
        cues = {c["beat"]: c for c in tl["cues"]}
        beats = film["beats"]
        hook = [cues[i] for i, b in enumerate(beats) if b.get("hook_card") and i in cues]
        if hook:
            self.items.append(("hook", hook[0]["t"], hook[-1]["t"] + hook[-1]["len"], film.get("hook_card", "")))
        for i, b in enumerate(beats):
            c = cues.get(i)
            if not c:
                continue
            if b.get("banner"):
                self.items.append(("banner", c["t"] + 0.2, c["t"] + c["len"] + 3.0, b["banner"].replace("⚠", "").strip()))
            if b.get("card"):
                self.items.append(("card", c["t"] + 0.1, c["t"] + c["len"], b["card"]))
        self.impact_times = []
        for s in tl["shots"]:
            for v in s.get("vfx", []):
                if v.get("kind") == "impact":
                    tt = v.get("t", 0.5)
                    fr = tt * s["frames"] if isinstance(tt, float) and tt <= 1.5 else tt
                    self.impact_times.append(round(s["start"] + fr / FPS, 3))
        cd = [(i, b) for i, b in enumerate(beats) if b.get("countdown")]
        if cd and self.impact_times:
            t0 = cues[cd[0][0]]["t"]
            t_imp = next((x for x in sorted(self.impact_times) if x > t0), None)
            if t_imp:
                self.items.append(("count", t0, t_imp + 0.3, t_imp))
        self.cache = {}

    def _wrap(self, text, font, maxw):
        from PIL import ImageDraw, Image
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        out = []
        for para in text.split("\n"):
            cur = ""
            for w in para.split():
                trial = (cur + " " + w).strip()
                if d.textlength(trial, font=font) > maxw and cur:
                    out.append(cur)
                    cur = w
                else:
                    cur = trial
            out.append(cur)
        return out

    def _sprite(self, key, kind, text):
        from PIL import Image, ImageDraw
        if key in self.cache:
            return self.cache[key]
        W, k = self.W, self.k
        if kind in ("hook", "card"):
            font = self.f_hook if kind == "hook" else self.f_card
            lines = self._wrap(text.upper() if kind == "card" else text, font, W * 0.84)
            lh = int(font.size * 1.18)
            h = lh * len(lines) + int(60 * k)
            im = Image.new("RGBA", (W, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            for j, ln in enumerate(lines):
                tw = d.textlength(ln, font=font)
                d.text(((W - tw) / 2, int(30 * k) + j * lh), ln, font=font, fill=(255, 255, 255, 255),
                       stroke_width=int(7 * k), stroke_fill=(0, 0, 0, 255))
        elif kind == "banner":
            h = int(110 * k)
            im = Image.new("RGBA", (W, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rectangle([0, int(12 * k), W, h - int(12 * k)], fill=(170, 10, 10, 225))
            for x in range(-h, W + h, int(60 * k)):
                d.polygon([(x, int(12 * k)), (x + int(26 * k), int(12 * k)), (x + int(6 * k), h - int(12 * k)), (x - int(20 * k), h - int(12 * k))],
                          fill=(120, 0, 0, 120))
            tw = d.textlength(text, font=self.f_ban)
            x0 = (W - tw) / 2 + int(30 * k)
            ty = (h - self.f_ban.size) / 2 - int(4 * k)
            cx, cy, r = x0 - int(48 * k), h / 2, int(26 * k)
            d.polygon([(cx, cy - r), (cx + r * 1.1, cy + r * 0.85), (cx - r * 1.1, cy + r * 0.85)], fill=(255, 220, 40, 255))
            d.text((cx - int(6 * k), cy - r * 0.6), "!", font=ImageFont_small(int(34 * k)), fill=(0, 0, 0, 255))
            d.text((x0, ty), text, font=self.f_ban, fill=(255, 255, 255, 255), stroke_width=int(3 * k), stroke_fill=(60, 0, 0, 255))
        else:  # countdown
            h = int(90 * k)
            im = Image.new("RGBA", (W, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            tw = d.textlength(text, font=self.f_cnt)
            d.rounded_rectangle([(W - tw) / 2 - int(24 * k), int(8 * k), (W + tw) / 2 + int(24 * k), h - int(8 * k)],
                                radius=int(16 * k), fill=(0, 0, 0, 170), outline=(255, 60, 40, 255), width=int(4 * k))
            d.text(((W - tw) / 2, (h - self.f_cnt.size) / 2 - int(6 * k)), text, font=self.f_cnt, fill=(255, 80, 60, 255))
        self.cache[key] = im
        return im

    def draw(self, frame, t):
        from PIL import Image
        suppress = False
        base = None
        for kind, a, b, text in self.items:
            if not (a <= t < b):
                continue
            if base is None:
                base = Image.fromarray(frame)
            age = t - a
            if kind == "hook":
                sp = self._sprite(("hook",), "hook", text)
                al = min(1.0, age / 0.25) * min(1.0, (b - t) / 0.3)
                y = int(self.H * 0.11)
                suppress = True
            elif kind == "card":
                sp = self._sprite(("card", text), "card", text)
                al = min(1.0, age / 0.35) * min(1.0, (b - t) / 0.35)
                dark = Image.new("RGBA", base.size, (0, 0, 0, int(110 * al)))
                base = Image.alpha_composite(base.convert("RGBA"), dark).convert("RGB")
                y = int(self.H * 0.40 - sp.height / 2)
                suppress = True
            elif kind == "banner":
                sp = self._sprite(("banner", text), "banner", text)
                blink = 1.0 if age > 1.2 or int(age * 8) % 2 == 0 else 0.35
                al = min(1.0, age / 0.15) * min(1.0, (b - t) / 0.4) * blink
                y = int(self.H * 0.075) - int(max(0, 0.25 - age) * 400 * self.k)
            else:
                secs = max(0, int(text - t + 0.999))
                lab = f"NEXT IMPACT  0:{secs:02d}"
                sp = self._sprite(("count", lab), "count", lab)
                al = min(1.0, age / 0.2)
                if secs <= 3 and int(t * 6) % 2:
                    al *= 0.4
                y = int(self.H * 0.08)
            if al < 1.0:
                sp = sp.copy()
                a_ = sp.getchannel("A").point(lambda v, al=al: int(v * al))
                sp.putalpha(a_)
            base.paste(sp, (0, max(0, y)), sp)
        if base is None:
            return frame, False
        return np.asarray(base.convert("RGB")), suppress


def ImageFont_small(sz):
    from PIL import ImageFont
    from captions import font_path
    return ImageFont.truetype(font_path(), sz)


def _boxes_at(meta, local):
    sb = meta.get("safe_boxes", {})
    if not sb:
        return []
    keys = sorted(int(k) for k in sb)
    best = min(keys, key=lambda k: abs(k - local))
    return sb[str(best)]


def contact_sheet(stills, labels, out_png, cols=6, thumb_w=216):
    """Grid of per-shot stills with shot id + camera label."""
    from PIL import Image, ImageDraw, ImageFont
    from captions import font_path
    th = int(thumb_w * 16 / 9)
    rows = (len(stills) + cols - 1) // cols
    pad = 6
    lab_h = 34
    sheet = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows * (th + lab_h + pad) + pad), (12, 12, 16))
    try:
        f = ImageFont.truetype(font_path(), 13)
    except Exception:
        f = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    for i, (p, lab) in enumerate(zip(stills, labels)):
        r, c = divmod(i, cols)
        x, y = pad + c * (thumb_w + pad), pad + r * (th + lab_h + pad)
        try:
            im = Image.open(p).convert("RGB").resize((thumb_w, th))
            sheet.paste(im, (x, y))
        except Exception:
            d.rectangle([x, y, x + thumb_w, y + th], outline=(255, 0, 0))
        for k, line in enumerate(lab.split("\n")[:2]):
            d.text((x + 2, y + th + 2 + k * 15), line[:34], fill=(230, 230, 230), font=f)
    sheet.save(out_png)
    return out_png


def image_stats(p):
    """QA metrics for a still: mean luma, % clipped, % crushed, contrast (std), colourfulness."""
    im = cv2.imread(p)
    if im is None:
        return None
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    b, gch, r = [im[..., i].astype(np.float32) for i in range(3)]
    rg, yb = r - gch, 0.5 * (r + gch) - b
    colorful = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    return {"mean": round(float(g.mean()), 1), "std": round(float(g.std()), 1),
            "clip": round(float((g > 250).mean() * 100), 2), "crush": round(float((g < 6).mean() * 100), 1),
            "color": round(float(colorful), 1),
            "sharp": round(float(cv2.Laplacian(g, cv2.CV_32F).var()), 1)}
