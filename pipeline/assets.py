"""CC0 asset fetcher + cache (Poly Haven HDRIs, ambientCG PBR textures).

Everything lands in ./assets and is listed in ./assets/credits.txt.
Downloads are skipped when the cached file already exists, so this is cheap to
call at the start of every run. If the network is unavailable the pipeline
falls back to procedural materials (the kit checks for files before using them).
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

# Night / interior HDRIs (Poly Haven, CC0)
HDRIS = {
    "city_night": "modern_buildings_night",
    "street_night": "cobblestone_street_night",
    "station_night": "dresden_station_night",
    "sky_night": "kloppenheim_02_puresky",
    "moonless": "moonless_golf",
    "metro": "metro_vijzelgracht",
}

# PBR textures (ambientCG, CC0). key -> asset id
TEXTURES = {
    "asphalt": "Asphalt031",
    "road": "Road012A",
    "concrete": "Concrete049",
    "paving": "PavingStones130",
    "metal": "Metal032",
    "metal_plate": "MetalPlates006",
    "bricks": "Bricks059",
    "tiles": "Tiles074",
    "ground": "Ground037",
    "wood": "WoodFloor051",
    "rock": "Rock030",
}

UA = {"User-Agent": "lantern-film-pipeline/1.0"}


def _get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_hdri(key, res="1k"):
    pid = HDRIS[key]
    out = os.path.join(ASSETS, "hdri", f"{pid}_{res}.hdr")
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    meta = json.loads(_get(f"https://api.polyhaven.com/files/{pid}"))
    url = meta["hdri"][res]["hdr"]["url"]
    data = _get(url)
    with open(out + ".part", "wb") as f:
        f.write(data)
    os.replace(out + ".part", out)
    return out


def fetch_texture(key, res="1K"):
    aid = TEXTURES[key]
    d = os.path.join(ASSETS, "textures", aid)
    if os.path.isdir(d) and os.listdir(d):
        return d
    os.makedirs(d, exist_ok=True)
    data = _get(f"https://ambientcg.com/get?file={aid}_{res}-JPG.zip", timeout=300)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if n.lower().endswith((".jpg", ".png")):
                with open(os.path.join(d, os.path.basename(n)), "wb") as f:
                    f.write(z.read(n))
    return d


def texture_maps(key):
    """Return dict of map-type -> file path for a cached texture (or {})."""
    aid = TEXTURES.get(key)
    if not aid:
        return {}
    d = os.path.join(ASSETS, "textures", aid)
    if not os.path.isdir(d):
        return {}
    maps = {}
    for f in os.listdir(d):
        lf = f.lower()
        for tag, name in (("_color", "color"), ("_roughness", "rough"),
                          ("_normalgl", "normal"), ("_displacement", "disp"),
                          ("_metalness", "metal"), ("_ambientocclusion", "ao")):
            if tag in lf:
                maps[name] = os.path.join(d, f)
    return maps


def hdri_path(key):
    p = os.path.join(ASSETS, "hdri", f"{HDRIS.get(key, key)}_1k.hdr")
    return p if os.path.exists(p) else None


def write_credits():
    lines = [
        "CREDITS — all third-party assets are CC0 (public domain).",
        "",
        "HDRIs — Poly Haven (https://polyhaven.com), CC0:",
    ]
    for k, v in HDRIS.items():
        lines.append(f"  - {v}  (https://polyhaven.com/a/{v})")
    lines += ["", "PBR textures — ambientCG (https://ambientcg.com), CC0:"]
    for k, v in TEXTURES.items():
        lines.append(f"  - {v}  (https://ambientcg.com/view?id={v})")
    lines += [
        "",
        "Voices — Piper TTS (https://github.com/rhasspy/piper), voice models from",
        "  rhasspy/piper-voices on Hugging Face; see each voice's MODEL_CARD for its dataset licence.",
        "Captions — faster-whisper (MIT) word timestamps.",
        "Music, ambience and sound effects — generated procedurally in Python (pipeline/audio.py); no samples.",
        "Characters, monsters, vehicles and sets — generated procedurally in Blender (pipeline/blender/kit.py).",
        "Fonts — Inter (SIL Open Font License).",
    ]
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "credits.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return os.path.join(ASSETS, "credits.txt")


def fetch_all(verbose=True):
    ok, bad = [], []
    for k in HDRIS:
        try:
            fetch_hdri(k); ok.append(k)
        except Exception as e:  # network/missing asset -> procedural fallback
            bad.append((k, str(e)[:80]))
    for k in TEXTURES:
        try:
            fetch_texture(k); ok.append(k)
        except Exception as e:
            bad.append((k, str(e)[:80]))
    write_credits()
    if verbose:
        print(f"[assets] cached {len(ok)} assets; {len(bad)} unavailable -> procedural fallback")
        for k, e in bad:
            print(f"   - {k}: {e}")
    return ok, bad


if __name__ == "__main__":
    fetch_all()
    sys.exit(0)
