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


def vignette(strength=0.38):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xx - W / 2) / (W / 2)
    ny = (yy - H / 2) / (H / 2)
    r = np.sqrt(nx ** 2 * 1.0 + ny ** 2 * 0.65)
    v = 1 - strength * np.clip((r - 0.45) / 0.85, 0, 1) ** 1.6
    return v[..., None].astype(np.float32)


def grain_bank(n=8, amount=5.0, seed=0):
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
            preview=False, max_seconds=None):
    luts = build_luts(look)
    vig = vignette()
    grains = grain_bank()
    cr = CaptionRenderer(W, H)
    total = shotlist["total_frames"]
    if max_seconds:
        total = min(total, int(max_seconds * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", audio_wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast" if preview else "slow", "-crf", "23" if preview else "19",
           "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high", "-level", "4.1",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    shots = shotlist["shots"]
    metas = {s["id"]: json.load(open(os.path.join(shot_dirs[s["id"]], "meta.json"))) for s in shots}
    last_path, last_img = None, None
    si = 0
    cap_i = 0
    flash_frames = {}
    for fl in flashes:
        f0 = int(fl * FPS)
        for k, a in enumerate((0.85, 0.5, 0.2)):
            flash_frames[f0 + k] = a
    for n in range(total):
        while si + 1 < len(shots) and n >= shots[si + 1]["start_frame"]:
            si += 1
        s = shots[si]
        local = n - s["start_frame"] + 1
        p = frame_source(shot_dirs[s["id"]], metas[s["id"]], local)
        if p != last_path:
            img = cv2.imread(p, cv2.IMREAD_COLOR)[:, :, ::-1]
            if img.shape[1] != W:
                img = cv2.resize(img, (W, H), interpolation=cv2.INTER_LANCZOS4)
                blur = cv2.GaussianBlur(img, (0, 0), 1.6)
                img = cv2.addWeighted(img, 1.45, blur, -0.45, 0)  # unsharp after upscale
            # grade
            img = cv2.LUT(img, luts.reshape(256, 1, 3))
            hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[..., 1] = np.clip(hsv[..., 1] * GRADES.get(look, GRADES["night_blue"])["sat"], 0, 255)
            img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
            last_img, last_path = img, p
        out = last_img.astype(np.float32) * vig + grains[(n // 2) % len(grains)]
        if n in flash_frames:
            out = out * (1 - flash_frames[n]) + 255 * flash_frames[n]
        # final fade in/out
        if n < 4:
            out *= n / 4
        if n > total - 18:
            out *= max(0, (total - n) / 18)
        out = np.clip(out, 0, 255).astype(np.uint8)
        t = n / FPS
        while cap_i + 1 < len(captions) and t >= captions[cap_i + 1]["s"]:
            cap_i += 1
        if captions and captions[cap_i]["s"] <= t < captions[cap_i]["e"]:
            c = captions[cap_i]
            meta = metas[s["id"]]
            boxes = _boxes_at(meta, local)
            y = c.get("_y")
            if y is None or c.get("_shot") != s["id"]:
                y = cr.place_y(boxes, 170)
                c["_y"], c["_shot"] = y, s["id"]
            out = cr.overlay(out, c["text"], t - c["s"], y)
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
        if n % 240 == 0:
            log(f"  [compose] {n}/{total} frames")
    enc.stdin.close()
    enc.wait()
    return out_mp4


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
