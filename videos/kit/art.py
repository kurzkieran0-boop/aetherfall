"""2D assets (PIL): face textures, counter digits, lined-paper insert cards, envelope wallpaper."""
import os, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from common import FONT, ASSETS, FACE_EXPR, DIGITS


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def face(skin, expr, size=256):
    im = Image.new("RGB", (size, size), skin)
    d = ImageDraw.Draw(im)
    k = size / 256
    dark = (30, 24, 22)
    lid = tuple(int(c * 0.78) for c in skin)
    lx, rx, ey = 78 * k, 178 * k, 108 * k
    ew, eh = 26 * k, 40 * k

    def box(cx, cy, w, h, col):
        d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=col)

    if expr in ("neutral", "talk"):
        for cx in (lx, rx):
            box(cx, ey, ew, eh, dark)
            box(cx - 5 * k, ey - 10 * k, 8 * k, 10 * k, (250, 250, 250))
        if expr == "neutral":
            box(128 * k, 186 * k, 74 * k, 12 * k, dark)
        else:
            box(128 * k, 186 * k, 56 * k, 34 * k, (60, 20, 20))
            box(128 * k, 196 * k, 40 * k, 10 * k, (170, 70, 70))
    elif expr == "scared":
        for cx, sgn in ((lx, -1), (rx, 1)):
            box(cx, ey + 2 * k, 34 * k, 42 * k, (250, 250, 248))
            box(cx + sgn * 2 * k, ey + 6 * k, 10 * k, 12 * k, dark)
            d.line([cx - 20 * k, ey - 30 * k - sgn * 9 * k, cx + 20 * k, ey - 30 * k + sgn * 9 * k], fill=dark, width=int(8 * k))
        pts = [(92 + i * 12, 192 + (6 if i % 2 else -4)) for i in range(7)]
        d.line([(x * k, y * k) for x, y in pts], fill=dark, width=int(8 * k))
    elif expr == "tired":
        for cx in (lx, rx):
            box(cx, ey + 8 * k, ew, eh * 0.45, dark)
            box(cx, ey - 6 * k, ew + 10 * k, eh * 0.55, lid)
            d.line([cx - 18 * k, ey + 2 * k, cx + 18 * k, ey + 2 * k], fill=dark, width=int(5 * k))
        box(128 * k, 190 * k, 60 * k, 9 * k, dark)
    elif expr == "shocked":
        for cx in (lx, rx):
            box(cx, ey, 44 * k, 52 * k, (250, 250, 248))
            box(cx, ey, 14 * k, 16 * k, dark)
            d.rectangle([cx - 22 * k, ey - 26 * k, cx + 22 * k, ey + 26 * k], outline=dark, width=int(4 * k))
        box(128 * k, 192 * k, 34 * k, 42 * k, (50, 16, 16))
    elif expr == "grumpy":
        for cx, sgn in ((lx, 1), (rx, -1)):
            box(cx, ey + 8 * k, ew, eh * 0.6, dark)
            d.line([cx - 22 * k, ey - 22 * k - sgn * 10 * k, cx + 22 * k, ey - 22 * k + sgn * 10 * k], fill=dark, width=int(10 * k))
        d.polygon([(92 * k, 200 * k), (128 * k, 184 * k), (164 * k, 200 * k), (164 * k, 210 * k),
                   (128 * k, 194 * k), (92 * k, 210 * k)], fill=dark)
    elif expr == "laughing":
        for cx in (lx, rx):   # happy closed eyes ^ ^
            d.line([cx - 18 * k, ey + 8 * k, cx, ey - 10 * k, cx + 18 * k, ey + 8 * k], fill=dark, width=int(9 * k))
        d.pieslice([82 * k, 150 * k, 174 * k, 230 * k], 0, 180, fill=(60, 20, 20))
        box(128 * k, 214 * k, 46 * k, 10 * k, (190, 80, 80))
        box(128 * k, 193 * k, 80 * k, 8 * k, (245, 245, 240))
    elif expr == "blank":
        for cx in (lx, rx):
            box(cx, ey + 4 * k, 12 * k, 12 * k, dark)
    return im


def make_faces(cast, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for n, c in cast.items():
        sk = hexrgb(c["skin"])
        for e in FACE_EXPR:
            p = os.path.join(out_dir, f"{n}_{e}.png")
            if not os.path.exists(p):
                face(sk, e).save(p)


def make_digits():
    """Counter digit tiles: teal-white (normal), red (under 300), dim red (blink off)."""
    os.makedirs(DIGITS, exist_ok=True)
    if os.path.exists(os.path.join(DIGITS, "dim_blank.png")):
        return
    font = ImageFont.truetype(str(FONT), 150)
    for style, col, glow in (("teal", (200, 255, 248), (40, 230, 210)), ("red", (255, 220, 210), (255, 40, 40)),
                             ("dim", (110, 30, 30), (60, 10, 10))):
        for ch in list("0123456789") + ["blank"]:
            im = Image.new("RGB", (128, 196), (14, 16, 20))
            if ch != "blank":
                g = Image.new("RGB", (128, 196), (0, 0, 0))
                gd = ImageDraw.Draw(g)
                bb = gd.textbbox((0, 0), ch, font=font)
                x = (128 - (bb[2] - bb[0])) / 2 - bb[0]
                y = (196 - (bb[3] - bb[1])) / 2 - bb[1]
                gd.text((x, y), ch, font=font, fill=glow)
                g = g.filter(ImageFilter.GaussianBlur(9))
                im = Image.fromarray(__import__("numpy").clip(
                    __import__("numpy").asarray(im, "int32") + __import__("numpy").asarray(g, "int32"), 0, 255).astype("uint8"))
                ImageDraw.Draw(im).text((x, y), ch, font=font, fill=col)
            im.save(os.path.join(DIGITS, f"{style}_{ch}.png"))


def card(lines, struck, W=1080, H=1920, seed=0):
    rnd = random.Random(seed)
    bg = Image.new("RGB", (W, H), (92, 70, 52))
    d = ImageDraw.Draw(bg)
    for y in range(0, H, 46):
        c = 86 + rnd.randint(-8, 8)
        d.rectangle([0, y, W, y + 44], fill=(c, int(c * 0.76), int(c * 0.56)))
        d.line([0, y + 45, W, y + 45], fill=(60, 44, 32), width=2)
    pw, ph = 900, 1040
    paper = Image.new("RGBA", (pw, ph), (244, 238, 220, 255))
    pd = ImageDraw.Draw(paper)
    for y in range(150, ph, 62):
        pd.line([0, y, pw, y], fill=(150, 176, 200), width=3)
    pd.line([110, 0, 110, ph], fill=(206, 90, 90), width=4)
    for y in (230, 520, 810):
        pd.ellipse([30, y, 66, y + 36], fill=(92, 70, 52))
    font_size = 180
    while True:
        font = ImageFont.truetype(str(FONT), font_size)
        widest = max(pd.textbbox((0, 0), l, font=font)[2] for l in lines)
        if (widest <= pw - 110 - 70 and len(lines) * (font_size + 40) <= ph - 140) or font_size < 40:
            break
        font_size -= 6
    gap = 40 if len(lines) < 5 else 22
    y = (ph - len(lines) * (font_size + gap)) / 2 + 20
    for i, line in enumerate(lines):
        bb = pd.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        x = 110 + (pw - 110 - tw) / 2
        pd.text((x, y), line, font=font, fill=(26, 26, 30))
        if i in struck:
            yy = y + font_size * 0.62
            pd.line([x - 20, yy + 6, x + tw + 20, yy - 6], fill=(210, 40, 40), width=22)
        y += font_size + gap
    paper = paper.rotate(rnd.uniform(-4, 4), resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", paper.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 150), mask=paper.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    ox, oy = (W - paper.size[0]) // 2, 300 + (1040 - paper.size[1]) // 2
    bg.paste(shadow, (ox + 18, oy + 26), shadow)
    bg.paste(paper, (ox, oy), paper)
    return bg


def make_cards(cards, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for i, (k, (lines, struck)) in enumerate(cards.items()):
        card(lines, struck, seed=i).save(os.path.join(out_dir, f"{k}.png"))


def envwall(size=1024, seed=5):
    rnd = random.Random(seed)
    im = Image.new("RGB", (size, size), (120, 100, 78))
    for row in range(-1, 9):
        for col in range(-1, 7):
            w, h = rnd.randint(150, 190), rnd.randint(100, 125)
            cx = col * 170 + rnd.randint(-20, 20) + (85 if row % 2 else 0)
            cy = row * 118 + rnd.randint(-14, 14)
            env = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            e = ImageDraw.Draw(env)
            tone = rnd.randint(-14, 8)
            e.rectangle([0, 0, w - 1, h - 1], fill=(238 + tone, 228 + tone, 200 + tone), outline=(170, 150, 120), width=3)
            e.line([0, 0, w // 2, h // 2, w, 0], fill=(196, 182, 150), width=3)
            for li in range(2):
                yy = int(h * 0.62) + li * 14
                e.line([w * 0.3, yy, w * (0.62 + rnd.random() * 0.2), yy], fill=(120, 110, 96), width=3)
            r = rnd.randint(13, 17)
            e.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], fill=(163, 40, 36))
            env = env.rotate(rnd.uniform(-9, 9), expand=True, resample=Image.BICUBIC)
            for ox in (-size, 0, size):
                for oy in (-size, 0, size):
                    im.paste(env, (cx - env.size[0] // 2 + ox, cy - env.size[1] // 2 + oy), env)
    return im


def make_all(slug):
    """Faces, digits, cards (+ envelope wallpaper if the scene asks for it) for one video."""
    from common import video, bdir
    cfg, story, scene = video(slug)
    b = bdir(slug)
    make_faces(scene.CAST, os.path.join(b, "faces"))
    make_digits()
    make_cards(story.CARDS, os.path.join(b, "cards"))
    if cfg.STYLE == "B":
        import textures
        textures.gen_all()
    if getattr(scene, "NEEDS_ENVWALL", False):
        p = os.path.join(b, "envwall.png")
        if not os.path.exists(p):
            envwall().save(p)


if __name__ == "__main__":
    from common import args
    make_all(args()[0])
    print("art ok")
