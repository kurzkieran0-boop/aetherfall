"""Procedural tileable textures for Style B (semi-realistic textured world). Pure numpy/PIL.

Textures are neutral-ish detail maps (brightness ~0.6-1.0) that get multiplied by each material's tint.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from texmap import TEX
N = 512


def noise(seed, octaves=5, base=8):
    rng = np.random.default_rng(seed)
    out = np.zeros((N, N), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        g = base * 2 ** o
        grid = rng.random((g, g)).astype(np.float32)
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)
        # wrap: blend with rolled copy for tileability
        a = np.asarray(img, np.float32) / 255
        out += amp * a
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def tile_fix(a):
    """Make an array tileable by cross-fading with its half-rolled copy."""
    b = np.roll(np.roll(a, N // 2, 0), N // 2, 1)
    y, x = np.mgrid[0:N, 0:N] / N
    w = (np.minimum(x, 1 - x) * np.minimum(y, 1 - y) * 4) ** 0.5
    if a.ndim == 3:
        w = w[..., None]
    return a * w + b * (1 - w)


def save(name, arr):
    TEX.mkdir(parents=True, exist_ok=True)
    arr = np.clip(arr, 0, 1)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, -1)
    Image.fromarray((arr * 255).astype(np.uint8)).save(TEX / f"{name}.png")


def gen_all():
    TEX.mkdir(parents=True, exist_ok=True)
    if (TEX / "water.png").exists():
        return
    rng = np.random.default_rng(1)
    # grass: speckled blades
    n = tile_fix(noise(2, 6, 6))
    spk = rng.random((N, N)) ** 6
    save("grass", 0.62 + 0.28 * n + 0.25 * spk)
    # dirt road
    n = tile_fix(noise(3, 6, 4))
    peb = (rng.random((N, N)) > 0.995).astype(np.float32)
    pebimg = np.asarray(Image.fromarray((peb * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)), np.float32) / 255
    save("dirt", 0.7 + 0.25 * n - 0.15 * pebimg)
    # cobblestone
    im = Image.new("L", (N, N), 120)
    d = ImageDraw.Draw(im)
    for row in range(10):
        for col in range(9):
            x = col * 58 + (29 if row % 2 else 0) + rng.integers(-4, 4)
            y = row * 52 + rng.integers(-4, 4)
            v = int(rng.integers(185, 235))
            for ox in (-N, 0, N):
                d.rounded_rectangle([x + ox, y, x + ox + 52, y + 46], radius=12, fill=v)
    a = np.asarray(im, np.float32) / 255 * (0.85 + 0.15 * noise(4, 5, 16))
    save("cobble", a)
    # wood planks (horizontal boards with grain)
    y = np.mgrid[0:N, 0:N][0] / N
    grain = 0.5 + 0.5 * np.sin((y * 90 + 6 * noise(5, 4, 4)) * np.pi)
    boards = (np.mod(np.mgrid[0:N, 0:N][0], 64) < 3).astype(np.float32)
    save("wood", 0.72 + 0.14 * grain + 0.1 * noise(6, 5, 8) - 0.35 * boards)
    # plaster wall
    save("plaster", 0.82 + 0.13 * tile_fix(noise(7, 6, 8)))
    # roof shingles
    sh = np.ones((N, N), np.float32) * 0.85
    for r in range(16):
        y0 = r * 32
        sh[y0:y0 + 3, :] = 0.5
        off = 16 if r % 2 else 0
        for c in range(17):
            x0 = (c * 32 + off) % N
            sh[y0:y0 + 32, x0:x0 + 2] = 0.55
    save("shingle", sh * (0.85 + 0.15 * noise(8, 5, 16)))
    # stone blocks
    st = np.ones((N, N), np.float32) * 0.9
    for r in range(8):
        y0 = r * 64
        st[y0:y0 + 4, :] = 0.5
        off = 48 if r % 2 else 0
        for c in range(6):
            x0 = (c * 96 + off) % N
            st[y0:y0 + 64, x0:x0 + 4] = 0.5
    save("stone", st * (0.8 + 0.2 * noise(9, 6, 8)))
    # bark
    x = np.mgrid[0:N, 0:N][1] / N
    save("bark", 0.6 + 0.3 * (0.5 + 0.5 * np.sin((x * 40 + 4 * noise(10, 4, 4)) * np.pi)) * noise(11, 5, 8))
    # leaves
    lv = 0.55 + 0.35 * tile_fix(noise(12, 6, 10)) + 0.2 * (rng.random((N, N)) ** 8)
    save("leaves", lv)
    # water: soft ripples, slightly bluish detail
    n = tile_fix(noise(13, 5, 6))
    rip = 0.5 + 0.5 * np.sin((np.mgrid[0:N, 0:N][0] / N * 30 + n * 6) * np.pi)
    save("water", 0.75 + 0.15 * rip + 0.1 * n)


from texmap import TEXMAP, B_TINT  # noqa: F401 (re-exported)


if __name__ == "__main__":
    gen_all()
    print("textures in", TEX)
