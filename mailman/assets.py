"""Procedural 2D assets: blocky face textures and lined-paper insert cards (PIL only)."""
import os, json, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FACES = os.path.join(HERE, "build", "faces")
CARDS = os.path.join(HERE, "build", "cards")
FONT = os.path.join(HERE, "assets", "QRBlack.ttf")
EXPR = ["neutral", "scared", "tired", "shocked", "blank", "talk"]
TEX = os.path.join(HERE, "build", "tex")

from scene_lib import CAST
SKIN = {n: tuple(int(c["skin"][i:i + 2], 16) for i in (1, 3, 5)) for n, c in CAST.items()}


def face(skin, expr, size=256):
    im = Image.new("RGB", (size, size), skin)
    d = ImageDraw.Draw(im)
    k = size / 256
    dark = (30, 24, 22)
    lid = tuple(int(c * 0.78) for c in skin)
    ex = [(70, 186)]  # eye centres x (left/right)
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
            box(cx, ey - 6 * k, ew + 10 * k, eh * 0.55, lid)  # heavy half lid
            d.line([cx - 18 * k, ey + 2 * k, cx + 18 * k, ey + 2 * k], fill=dark, width=int(5 * k))
        box(128 * k, 190 * k, 60 * k, 9 * k, dark)
    elif expr == "shocked":
        for cx in (lx, rx):
            box(cx, ey, 44 * k, 52 * k, (250, 250, 248))
            box(cx, ey, 14 * k, 16 * k, dark)
            d.rectangle([cx - 22 * k, ey - 26 * k, cx + 22 * k, ey + 26 * k], outline=dark, width=int(4 * k))
        box(128 * k, 192 * k, 34 * k, 42 * k, (50, 16, 16))
    elif expr == "blank":
        for cx in (lx, rx):
            box(cx, ey + 4 * k, 12 * k, 12 * k, dark)
    return im


def make_faces():
    os.makedirs(FACES, exist_ok=True)
    for ch, sk in SKIN.items():
        for e in EXPR:
            p = os.path.join(FACES, f"{ch}_{e}.png")
            if not os.path.exists(p):
                face(sk, e).save(p)


def card(lines, struck, W=1080, H=1920, seed=0):
    rnd = random.Random(seed)
    # desk background
    bg = Image.new("RGB", (W, H), (92, 70, 52))
    d = ImageDraw.Draw(bg)
    for y in range(0, H, 46):  # wood planks
        c = 86 + rnd.randint(-8, 8)
        d.rectangle([0, y, W, y + 44], fill=(c, int(c * 0.76), int(c * 0.56)))
        d.line([0, y + 45, W, y + 45], fill=(60, 44, 32), width=2)
    # paper
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
        font = ImageFont.truetype(FONT, font_size)
        widest = max(pd.textbbox((0, 0), l, font=font)[2] for l in lines)
        if (widest <= pw - 110 - 70 and len(lines) * (font_size + 40) <= ph - 140) or font_size < 40:
            break
        font_size -= 6
    gap = 40 if len(lines) < 5 else 22
    total_h = len(lines) * (font_size + gap)
    y = (ph - total_h) / 2 + 20
    for i, line in enumerate(lines):
        bb = pd.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        x = 110 + (pw - 110 - tw) / 2
        pd.text((x, y), line, font=font, fill=(26, 26, 30))
        if i in struck:
            yy = y + font_size * 0.62
            pd.line([x - 20, yy + 6, x + tw + 20, yy - 6], fill=(210, 40, 40), width=22)
        y += font_size + gap
    ang = rnd.uniform(-4, 4)
    paper = paper.rotate(ang, resample=Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", paper.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 150), mask=paper.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    ox = (W - paper.size[0]) // 2
    oy = 300 + (1040 - paper.size[1]) // 2
    bg.paste(shadow, (ox + 18, oy + 26), shadow)
    bg.paste(paper, (ox, oy), paper)
    return bg


def envwall(size=1024, seed=5):
    """Seamless-ish tile: overlapping cream envelopes with red wax seals and faint address lines."""
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
            base = (238 + tone, 228 + tone, 200 + tone)
            e.rectangle([0, 0, w - 1, h - 1], fill=base, outline=(170, 150, 120), width=3)
            e.line([0, 0, w // 2, h // 2, w, 0], fill=(196, 182, 150), width=3)
            for li in range(2):
                yy = int(h * 0.62) + li * 14
                e.line([w * 0.3, yy, w * (0.62 + rnd.random() * 0.2), yy], fill=(120, 110, 96), width=3)
            r = rnd.randint(13, 17)
            e.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], fill=(163, 40, 36))
            e.ellipse([w // 2 - r + 5, h // 2 - r + 5, w // 2 - 1, h // 2 - 1], fill=(190, 66, 58))
            env = env.rotate(rnd.uniform(-9, 9), expand=True, resample=Image.BICUBIC)
            for ox in (-size, 0, size):
                for oy in (-size, 0, size):
                    im.paste(env, (cx - env.size[0] // 2 + ox, cy - env.size[1] // 2 + oy), env)
    return im


def make_tex():
    os.makedirs(TEX, exist_ok=True)
    p = os.path.join(TEX, "envwall.png")
    if not os.path.exists(p):
        envwall().save(p)


def make_cards():
    from story import CARDS as C
    os.makedirs(CARDS, exist_ok=True)
    for i, (k, (lines, struck)) in enumerate(C.items()):
        p = os.path.join(CARDS, f"{k}.png")
        card(lines, struck, seed=i).save(p)


if __name__ == "__main__":
    make_tex()
    make_faces()
    make_cards()
    print("faces + cards ok")
