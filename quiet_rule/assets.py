"""Procedural 2D assets: blocky face textures and lined-paper insert cards (PIL only)."""
import os, json, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FACES = os.path.join(HERE, "build", "faces")
CARDS = os.path.join(HERE, "build", "cards")
FONT = os.path.join(HERE, "assets", "QRBlack.ttf")
EXPR = ["neutral", "sad", "tired", "shocked", "blank", "talk"]

# character -> skin colour (muted)
SKIN = {"eli": (226, 190, 150), "baker": (214, 172, 132), "mayor": (232, 200, 168),
        "dad": (196, 150, 112), "pell": (236, 206, 178), "t1": (170, 122, 88),
        "t2": (222, 184, 144), "t3": (150, 104, 74), "t4": (230, 196, 160),
        "t5": (204, 160, 120), "t6": (184, 136, 100)}


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
    elif expr == "sad":
        for cx, s in ((lx, -1), (rx, 1)):
            box(cx, ey + 4 * k, ew, eh * 0.8, dark)
            d.line([cx - 22 * k, ey - 28 * k - s * 8 * k, cx + 22 * k, ey - 28 * k + s * 8 * k],
                   fill=dark, width=int(9 * k))
        # frown
        d.polygon([(92 * k, 200 * k), (128 * k, 178 * k), (164 * k, 200 * k), (164 * k, 210 * k),
                   (128 * k, 190 * k), (92 * k, 210 * k)], fill=dark)
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
        if widest <= pw - 110 - 70 or font_size < 40:
            break
        font_size -= 6
    total_h = len(lines) * (font_size + 40)
    y = (ph - total_h) / 2 + 20
    for i, line in enumerate(lines):
        bb = pd.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        x = 110 + (pw - 110 - tw) / 2
        pd.text((x, y), line, font=font, fill=(26, 26, 30))
        if i in struck:
            yy = y + font_size * 0.62
            pd.line([x - 20, yy + 6, x + tw + 20, yy - 6], fill=(210, 40, 40), width=22)
        y += font_size + 40
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


def make_cards():
    from story import CARDS as C
    os.makedirs(CARDS, exist_ok=True)
    for i, (k, (lines, struck)) in enumerate(C.items()):
        p = os.path.join(CARDS, f"{k}.png")
        card(lines, struck, seed=i).save(p)


if __name__ == "__main__":
    make_faces()
    make_cards()
    print("faces + cards ok")
