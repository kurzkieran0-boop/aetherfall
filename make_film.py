#!/usr/bin/env python3
"""One command, one finished film:

    python make_film.py "<idea or 'surprise me'>"

Stages (each is cached / resumable — re-running skips anything already done):
  setup    check tools, install missing Python packages, fetch CC0 assets
  story    brainstorm 10 premises -> score -> outline -> draft -> critique -> rewrite
           -> story.md, script.md, shotlist.json
  voice    neural TTS per line (Piper) -> real line lengths -> timeline
  stills   preview pass: one 540x960 still per shot -> contact_sheet.png + qa.json
  final    animated shots, parallel Blender processes, hash-cached per shot
  audio    procedural score + SFX from render events + ambience + voices -> loudnorm
  captions faster-whisper word timestamps -> word-by-word captions
  compose  grade, grain, vignette, flashes, captions, mux -> film.mp4 (1080x1920 24fps)
  deliver  ffprobe checks, thumbnail, title/description/hashtags

Options:
  --stop-after STAGE   stop after a stage (e.g. stills, to review the contact sheet)
  --only-stage STAGE   run just one stage (earlier outputs must exist)
  --jobs N             parallel Blender processes
  --redo-shots s003,s010   force re-render of specific shots
  --slug NAME          output folder name override
Nothing is ever uploaded or posted anywhere.
"""
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

STAGES = ["setup", "story", "voice", "stills", "final", "audio", "captions", "compose", "deliver"]
FPS = 24


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------------------- setup

def stage_setup():
    t = time.time()
    missing = []
    for mod, pkg in (("numpy", "numpy"), ("PIL", "pillow"), ("cv2", "opencv-python"), ("faster_whisper", "faster-whisper"),
                     ("piper", "piper-tts"), ("scipy", "scipy")):
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        log(f"[setup] installing missing packages: {missing}")
        subprocess.run([sys.executable, "-m", "pip", "install", *missing], check=True)
    if not shutil.which("ffmpeg"):
        log("[setup] ffmpeg missing -> install it (Windows: winget install Gyan.FFmpeg; Linux: apt install ffmpeg)")
        sys.exit(1)
    from render import blender_cmd, detect_gpu
    bc = blender_cmd()
    if bc[0] == sys.executable:
        try:
            importlib.import_module("bpy")
            log("[setup] Blender: using the `bpy` Python module (no blender binary on PATH)")
        except ImportError:
            log("[setup] Blender not found. Install: winget install BlenderFoundation.Blender  (or pip install bpy)")
            sys.exit(1)
    else:
        log(f"[setup] Blender: {bc[0]}")
    log(f"[setup] GPU: {detect_gpu() or 'none (CPU profile: 432x768 on twos -> upscaled 1080x1920)'}")
    import assets
    assets.fetch_all(verbose=True)
    log(f"[setup] ok ({time.time() - t:.1f}s)")


# ---------------------------------------------------------------------------- story

def stage_story(idea, slug_override=None):
    import story as S
    film = S.pick_bank(idea)
    premises = S.brainstorm(idea)
    if film is not None:
        log(f"[story] using authored film '{film['title']}' from stories/ (premise bank match)")
    else:
        best = premises[0]
        lines = S.llm_lines(best) if S.ollama_available() else None
        film = S.template_film(idea, best, lines)
        film["premises"] = premises
        film["chosen"] = 0
        film["why"] = "highest weighted score (hook ×1.5, clarity ×1.2, clever use ×1.2, idea fit ×1.5)."
        film["outline"] = S.OUTLINE
        film["draft"] = "\n".join(f"{b['say'][0].upper()}: {b['say'][1]}" for b in film["beats"] if b["say"])
        notes = S.critique(film)
        film["critique"] = notes
        film = S.rewrite(film, notes)
        log(f"[story] generated '{film['title']}' ({'ollama' if lines else 'template writer'})")
    slug = slug_override or film["slug"]
    out = os.path.join(ROOT, "output", slug)
    os.makedirs(out, exist_ok=True)
    idx_p = os.path.join(ROOT, "output", "index.json")
    idx = json.load(open(idx_p)) if os.path.exists(idx_p) else {}
    idx[idea] = slug
    json.dump(idx, open(idx_p, "w"), indent=1)
    json.dump(film, open(os.path.join(out, "film.json"), "w"), indent=1, default=list)
    return slug, out


# ---------------------------------------------------------------------------- voice

def stage_voice(out):
    import audio as AU
    import story as S
    film = json.load(open(os.path.join(out, "film.json")))
    vdir = os.path.join(out, "audio", "lines")
    os.makedirs(vdir, exist_ok=True)
    durs = []
    for i, b in enumerate(film["beats"]):
        if not b["say"]:
            durs.append(0.0)
            continue
        spk, text = b["say"]
        voice = "narrator" if spk == "narrator" else ("crowd" if spk == "crowd" else film["characters"].get(spk, {}).get("voice", "man"))
        p = os.path.join(vdir, f"{i:03d}_{spk}.wav")
        stamp = p + ".txt"
        if os.path.exists(p) and os.path.exists(stamp) and open(stamp).read() == f"{voice}|{text}":
            durs.append(AU.wav_dur(p))
            continue
        d = AU.tts(text, voice, p, film.get("voice_speed", 1.0))
        open(stamp, "w").write(f"{voice}|{text}")
        durs.append(d)
    tl = S.build_timeline(film, durs)
    notes = S.critique(film, durs)
    S.write_docs(film, tl, out, notes)
    json.dump(tl, open(os.path.join(out, "timeline.json"), "w"), indent=1)
    log(f"[voice] {sum(1 for d in durs if d)} lines, runtime {tl['duration']:.1f}s, {len(tl['shots'])} shots")
    for n in notes:
        log(f"   critique: {n}")
    return tl


# --------------------------------------------------------------------------- render

def _film_and_tl(out):
    return json.load(open(os.path.join(out, "film.json"))), json.load(open(os.path.join(out, "timeline.json")))


def stage_stills(out, jobs=None):
    import render as R
    from compose import contact_sheet, image_stats
    film, tl = _film_and_tl(out)
    shots = []
    for s in tl["shots"]:
        s2 = dict(s)
        shots.append(s2)
    t = time.time()
    dirs = R.render_shots(film, shots, "still", jobs=jobs, log=log)
    sd = os.path.join(out, "stills")
    os.makedirs(sd, exist_ok=True)
    stills, labels, qa = [], [], {}
    for s in tl["shots"]:
        d = dirs.get(s["id"])
        if not d:
            continue
        m = json.load(open(os.path.join(d, "meta.json")))
        src = os.path.join(d, f"f_{m['frames'][0]:04d}.png")
        dst = os.path.join(sd, f"{s['id']}.png")
        shutil.copy(src, dst)
        stills.append(dst)
        c = s["camera"]
        labels.append(f"{s['id']} {s['frames'] / FPS:.1f}s {c.get('lens')}mm\n{c.get('framing')} {c.get('angle')} {c.get('move')}")
        st = image_stats(dst)
        flags = []
        if st["mean"] < 26: flags.append("DARK")
        if st["clip"] > 4: flags.append("CLIPPING")
        if st["crush"] > 55: flags.append("CRUSHED")
        if st["std"] < 16: flags.append("FLAT")
        if st["color"] < 7: flags.append("MUDDY")
        dur = s["frames"] / FPS
        if dur < 1.2 or dur > 3.6: flags.append(f"CUT {dur:.1f}s")
        if c.get("move") in (None, "static"): flags.append("STATIC")
        qa[s["id"]] = dict(st, flags=flags, wall_s=m.get("wall_s"))
    contact_sheet(stills, labels, os.path.join(out, "contact_sheet.png"))
    json.dump(qa, open(os.path.join(out, "qa.json"), "w"), indent=1)
    bad = {k: v["flags"] for k, v in qa.items() if v["flags"]}
    log(f"[stills] contact sheet -> {os.path.join(out, 'contact_sheet.png')} ({time.time() - t:.0f}s); "
        f"flagged {len(bad)}: {bad}")


def stage_final(out, jobs=None, redo=None):
    import render as R
    film, tl = _film_and_tl(out)
    if redo:
        rset = R.profile("final")
        for s in tl["shots"]:
            if s["id"] in redo:
                d = os.path.join(R.CACHE, "final_" + R.shot_key(R.film_context(film), s, rset))
                shutil.rmtree(d, ignore_errors=True)
    t = time.time()
    dirs = R.render_shots(film, tl["shots"], "final", jobs=jobs, log=log)
    missing = [s["id"] for s in tl["shots"] if s["id"] not in dirs]
    if missing:
        log(f"[final] FAILED shots: {missing}")
        sys.exit(2)
    tm = R.timings(dirs)
    json.dump({"dirs": dirs, "timings": tm, "wall_s": round(time.time() - t, 1)},
              open(os.path.join(out, "render.json"), "w"), indent=1)


# ---------------------------------------------------------------------------- audio

def stage_audio(out):
    import numpy as np
    import audio as AU
    film, tl = _film_and_tl(out)
    rj = json.load(open(os.path.join(out, "render.json")))
    dur = tl["duration"] + 0.5
    n = int(dur * AU.SR)
    voice = np.zeros(n, np.float32)
    sfx = np.zeros(n, np.float32)
    amb = np.zeros(n, np.float32)
    vdir = os.path.join(out, "audio", "lines")
    for ln in tl["lines"]:
        w = AU.read_wav(os.path.join(vdir, f"{ln['beat']:03d}_{ln['speaker']}.wav"))
        g = 1.0
        b = film["beats"][ln["beat"]]
        if b.get("voice_fx") == "echo":
            w = AU.echo(w)
        if b.get("voice_fx") == "radio":
            w = AU.highpass(AU.lowpass(w, 3200), 400) * 1.6
        if b.get("voice_fx") == "whisper":
            g = 0.7
        AU.place(voice, w, ln["start"], g)
    # render-driven SFX: footfalls, roars, whip-pans
    shots = {s["id"]: s for s in tl["shots"]}
    seen = set()
    for sid, d in rj["dirs"].items():
        m = json.load(open(os.path.join(d, "meta.json")))
        s = shots[sid]
        for f, loc in m.get("impacts", []):
            if not (1 <= f <= s["frames"]):
                continue
            t = s["start"] + (f - 1) / FPS
            if any(abs(t - x) < 0.25 for x in seen):
                continue
            seen.add(t)
            AU.place(sfx, AU.stomp(int(t * 100), 0.9), t - 0.02)
        if m.get("roar") and 1 <= m["roar"] <= s["frames"]:
            t = s["start"] + (m["roar"] - 1) / FPS
            AU.place(sfx, AU.roar(3.2, int(t * 10), film["monster"].get("roar_pitch", 1.0)), t - 0.45, 0.9)
        if s["camera"].get("move") == "whip_pan":
            t = s["start"] + s["frames"] / FPS * s["camera"].get("whip_at", 0.45)
            AU.place(sfx, AU.whoosh(0.5, int(t * 10)), t - 0.15, 0.8)
    # scripted SFX per beat
    lib = {"thunder": lambda k: AU.thunder(k), "roar": lambda k: AU.roar(3.2, k, film["monster"].get("roar_pitch", 1.0)),
           "stomp": lambda k: AU.stomp(k), "boom": lambda k: AU.boom(2.5, 45, k), "whoosh": lambda k: AU.whoosh(0.6, k),
           "riser": lambda k: AU.riser(2.0, k) * 0.6, "siren": lambda k: AU.siren(4.0, k, "yelp") * 0.6,
           "phone": lambda k: _phone(AU, k), "splash": lambda k: _splash(AU, k), "steam": lambda k: _steam(AU, k),
           "crash": lambda k: AU.stomp(k, 1.2)[:int(2.0 * AU.SR)] + AU.boom(2.0, 60, k) * 0.5, "spark": lambda k: _spark(AU, k),
           "rumble": lambda k: AU.city_rumble(3.0, k, 0.6), "click": lambda k: _click(AU, k),
           "power_down": lambda k: _powerdown(AU, k), "bell": lambda k: AU.bell(k), "splat": lambda k: AU.splat(k),
           "cheer": lambda k: AU.cheer(3.0, k), "horn": lambda k: AU.horn(0.5, k), "bonk": lambda k: AU.bonk(k),
           "sprinkler": lambda k: AU.sprinkler(3.0, k), "bells": lambda k: _bells(AU, k), "band": lambda k: _band(AU, k)}
    for c in tl["cues"]:
        for e in c.get("sfx", []):
            kind = e["kind"] if isinstance(e, dict) else e
            off = (e.get("at", 0.0) if isinstance(e, dict) else 0.0) * c["len"]
            g = e.get("gain", 1.0) if isinstance(e, dict) else 1.0
            if kind in lib:
                AU.place(sfx, lib[kind](int(c["t"] * 10) + 7), c["t"] + off, g)
    # ambience beds
    fx_all = set()
    for s in tl["shots"]:
        for x in s.get("fx", []):
            fx_all.add(x if isinstance(x, str) else x.get("kind"))
    for s in tl["shots"]:
        seg_n = int(s["frames"] / FPS * AU.SR)
        i0 = int(s["start"] * AU.SR)
        fxs = {x if isinstance(x, str) else x.get("kind") for x in s.get("fx", [])}
        if "rain" in fxs:
            amb[i0:i0 + seg_n] += AU.rain_amb(s["frames"] / FPS + 0.01, int(s["start"] * 10), 0.3)[:len(amb[i0:i0 + seg_n])]
    amb += AU.city_rumble(dur, 5, 0.12 if film.get("look") != "sunny" else 0.03)[:n]
    if film.get("look") == "sunny":
        amb += AU.birds(dur, 3, 0.1)[:n]
    if any(p.get("kind") == "police_car" for ps in film.get("dressing", {}).values() for p in ps):
        sir = AU.siren(dur, 1, "wail") * 0.18
        amb += AU.lowpass(sir, 1800)[:n]
    # score from the cue sheet (tension curve + hits/braams/drops/resolve)
    cues = []
    last = 0.3
    for c in tl["cues"]:
        ten = c["tension"] if c["tension"] is not None else last
        last = ten
        cues.append({"t": c["t"], "tension": ten, "kind": c["kind"], "len": c["len"]})
    if film.get("score_style") == "playful":
        music = AU.score_playful(dur, cues, key=film.get("key", "F"), seed=len(film["title"]), bpm=film.get("bpm", 128))[:n]
    else:
        music = AU.score(dur, cues, key=film.get("key", "D"), seed=len(film["title"]), bpm=film.get("bpm", 100))[:n]
    music = AU.duck(music, voice, 0.5)
    amb = AU.duck(amb, voice, 0.3)
    mix = voice * 1.0 + music * 0.42 + sfx * 0.75 + amb * 0.5
    mix = np.tanh(mix * 0.9)
    ad = os.path.join(out, "audio")
    AU.write_wav(os.path.join(ad, "voice.wav"), voice)
    AU.write_wav(os.path.join(ad, "mix_raw.wav"), mix)
    js = AU.loudnorm(os.path.join(ad, "mix_raw.wav"), os.path.join(ad, "mix.wav"), I=-14)
    log(f"[audio] mixed {dur:.1f}s; loudnorm in {js['input_i']} LUFS -> -14 LUFS (TP -1 dB)")


def _band(AU, k):
    """Marching snare + bass drum + a tuba-ish oom-pah for ~3 s."""
    import numpy as np
    d = 3.2
    out = np.zeros(int(d * AU.SR), np.float32)
    beat = 60 / 120
    for j in range(int(d / beat * 2)):
        i = int(j * beat / 2 * AU.SR)
        if j % 2 == 0:
            b = AU.boom(0.35, 70, k + j)[: len(out) - i] * 0.5
            out[i:i + len(b)] += b
        sn = AU.highpass(AU.noise(int(0.09 * AU.SR), k + j), 1800) * np.exp(-np.arange(int(0.09 * AU.SR)) / 700) * 0.35
        out[i:i + len(sn)] += sn[: len(out) - i]
        if j % 4 in (0, 2):
            tt = AU.t_axis(0.22)
            tu = AU.saw(87.3 if j % 8 < 4 else 130.8, tt) * np.exp(-tt * 6) * 0.25
            tu = AU.lowpass(tu.astype(np.float32), 600)
            out[i:i + len(tu)] += tu[: len(out) - i]
    return out


def _bells(AU, k):
    import numpy as np
    out = np.zeros(int(4.5 * AU.SR), np.float32)
    for j in range(4):
        b = AU.bell(k + j, 392.0 if j % 2 == 0 else 330.0, 2.5)
        i = int(j * 0.8 * AU.SR)
        out[i:i + len(b)] += b[: len(out) - i]
    return out


def _phone(AU, k):
    import numpy as np
    t = AU.t_axis(1.6)
    on = ((t % 0.4) < 0.2).astype(np.float32)
    return (np.sin(2 * np.pi * 1400 * t) * 0.3 + np.sin(2 * np.pi * 1800 * t) * 0.2) * on * 0.5


def _splash(AU, k):
    import numpy as np
    n = AU.noise(int(1.8 * AU.SR), k)
    return (AU.highpass(AU.lowpass(n, 5000), 300) * AU.env(len(n), 0.01, 0.7) * 0.9 +
            AU.lowpass(n, 200) * AU.env(len(n), 0.005, 0.3) * 1.5).astype(np.float32)


def _steam(AU, k):
    n = AU.noise(int(2.5 * AU.SR), k)
    return AU.highpass(n, 3000) * AU.env(len(n), 0.05, 1.5, 1.0) * 0.5


def _spark(AU, k):
    import numpy as np
    n = AU.noise(int(0.8 * AU.SR), k)
    x = AU.highpass(n, 4000) * AU.env(len(n), 0.001, 0.15)
    return np.concatenate([x, x * 0.6, x * 0.3])


def _click(AU, k):
    import numpy as np
    n = AU.noise(int(0.08 * AU.SR), k)
    return AU.highpass(n, 2000) * np.exp(-np.arange(len(n)) / 200) * 0.8


def _powerdown(AU, k):
    import numpy as np
    t = AU.t_axis(1.5)
    f = 120 * np.exp(-t * 2)
    return (np.sin(2 * np.pi * np.cumsum(f) / AU.SR) * np.exp(-t * 1.5) * 0.6).astype(np.float32)


# ------------------------------------------------------------------------- captions

def stage_captions(out):
    import captions as CP
    film, tl = _film_and_tl(out)
    vdir = os.path.join(out, "audio", "lines")
    caps, allw = [], []
    for ln in tl["lines"]:
        p = os.path.join(vdir, f"{ln['beat']:03d}_{ln['speaker']}.wav")
        ww = CP.whisper_words(p)
        words = CP.align(ln["text"], ww, ln["dur"])
        for w, s, e in CP.group_words(words):
            caps.append({"text": w, "s": round(ln["start"] + s, 3), "e": round(ln["start"] + e, 3),
                         "speaker": ln["speaker"]})
        allw += [(w, ln["start"] + s) for w, s, e in words]
    json.dump(caps, open(os.path.join(out, "captions.json"), "w"), indent=1)
    log(f"[captions] {len(caps)} caption pops from {len(allw)} words")


# -------------------------------------------------------------------------- compose

def stage_compose(out):
    import compose as C
    film, tl = _film_and_tl(out)
    rj = json.load(open(os.path.join(out, "render.json")))
    caps = json.load(open(os.path.join(out, "captions.json")))
    flashes = [c["t"] for c in tl["cues"] if c["kind"] in ("hit", "braam") and c["t"] > 1.0]
    t = time.time()
    C.compose(tl, rj["dirs"], os.path.join(out, "audio", "mix.wav"), caps, os.path.join(out, "film.mp4"),
              look=film["look"], flashes=flashes, log=log)
    log(f"[compose] film.mp4 written ({time.time() - t:.0f}s)")


# -------------------------------------------------------------------------- deliver

def ffprobe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_name",
                        "-of", "json", p], capture_output=True, text=True)
    return json.loads(r.stdout)


def stage_deliver(out):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import captions as CP
    from compose import image_stats
    film, tl = _film_and_tl(out)
    pr = ffprobe(os.path.join(out, "film.mp4"))
    dur = float(pr["format"]["duration"])
    v = [s for s in pr["streams"] if s.get("width")][0]
    lo, hi = film.get("runtime_target", (60, 120))
    ok = lo <= dur <= hi and v["width"] == 1080 and v["height"] == 1920 and v["r_frame_rate"] == "24/1"
    log(f"[deliver] ffprobe: {dur:.2f}s {v['width']}x{v['height']} @ {v['r_frame_rate']} {v['codec_name']} -> {'OK' if ok else 'CHECK'}")
    # thumbnail: chosen shot (film['thumb']) or the punchiest monster still
    sd = os.path.join(out, "stills")
    cand = film.get("thumb")
    if not cand:
        best, bs = None, -1
        for s in tl["shots"]:
            if not any(a["who"] == "monster" for a in s["actions"]):
                continue
            st = image_stats(os.path.join(sd, s["id"] + ".png"))
            sc = st["std"] + st["color"] - abs(st["mean"] - 70) * 0.5
            if sc > bs:
                best, bs = s["id"], sc
        cand = best or tl["shots"][0]["id"]
    im = Image.open(os.path.join(sd, cand + ".png")).convert("RGB").resize((1080, 1920), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(2, 80, 2))
    d = ImageDraw.Draw(im)
    fnt = ImageFont.truetype(CP.font_path(), 150)
    words = film.get("thumb_text", film["title"]).upper().split()
    lines, cur = [], ""
    for w in words:
        if len(cur + " " + w) > 10 and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    y = 150
    for ln in lines:
        bb = fnt.getbbox(ln, stroke_width=14)
        x = (1080 - (bb[2] - bb[0])) // 2
        d.text((x, y), ln, font=fnt, fill=(255, 222, 26), stroke_width=14, stroke_fill=(0, 0, 0))
        y += bb[3] - bb[1] + 30
    im.save(os.path.join(out, "thumbnail.jpg"), quality=92)
    meta = {
        "title": film["title"],
        "tiktok": {"caption": f"{film['hook_caption']} {' '.join(film['hashtags'][:6])}",
                   "hashtags": film["hashtags"][:8]},
        "youtube_shorts": {"title": f"{film['title']} | {film['rule']} #shorts"[:100],
                           "description": film["description"] + "\n\n" + " ".join(film["hashtags"]),
                           "tags": [h.lstrip("#") for h in film["hashtags"]]},
        "runtime_s": round(dur, 2), "resolution": "1080x1920", "fps": 24,
        "credits": "All assets CC0 / procedural — see assets/credits.txt",
        "posted": False,
    }
    json.dump(meta, open(os.path.join(out, "metadata.json"), "w"), indent=1)
    with open(os.path.join(out, "metadata.txt"), "w") as f:
        f.write(f"TITLE: {film['title']}\n\nTIKTOK CAPTION:\n{meta['tiktok']['caption']}\n\n"
                f"YOUTUBE SHORTS TITLE:\n{meta['youtube_shorts']['title']}\n\nDESCRIPTION:\n{meta['youtube_shorts']['description']}\n")
    shutil.copy(os.path.join(ROOT, "assets", "credits.txt"), os.path.join(out, "credits.txt"))
    # QA contact sheet built from the FINAL rendered frames (what is actually in the film)
    from compose import contact_sheet
    rj = json.load(open(os.path.join(out, "render.json")))
    stills, labels = [], []
    for s in tl["shots"]:
        d = rj["dirs"][s["id"]]
        m = json.load(open(os.path.join(d, "meta.json")))
        f = m["frames"][int(len(m["frames"]) * 0.6)]
        stills.append(os.path.join(d, f"f_{f:04d}.png"))
        c = s["camera"]
        tm = rj["timings"].get(s["id"], {})
        labels.append(f"{s['id']} {s['frames'] / FPS:.1f}s {c.get('move')}\nrender {tm.get('wall_s', '?')}s {c.get('lens')}mm {c.get('framing')}")
    contact_sheet(stills, labels, os.path.join(out, "contact_sheet_final.png"))
    log(f"[deliver] {out}/film.mp4 + thumbnail.jpg + metadata.json  (NOT posted anywhere)")


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea", nargs="?", default="surprise me")
    ap.add_argument("--stop-after", choices=STAGES)
    ap.add_argument("--only-stage", choices=STAGES)
    ap.add_argument("--jobs", type=int)
    ap.add_argument("--redo-shots")
    ap.add_argument("--slug")
    a = ap.parse_args()
    t0 = time.time()
    times = {}
    state_slug = None
    stages = [a.only_stage] if a.only_stage else STAGES
    out = None
    if a.slug and os.path.exists(os.path.join(ROOT, "output", a.slug, "film.json")):
        state_slug, out = a.slug, os.path.join(ROOT, "output", a.slug)
    for st in stages:
        ts = time.time()
        if st == "setup":
            stage_setup()
        elif st == "story":
            fj = os.path.join(out, "film.json") if out else None
            if fj and os.path.exists(fj) and json.load(open(fj)).get("source") == "template" and not a.only_stage:
                log(f"[story] resume: {fj} exists")
            else:
                state_slug, out = stage_story(a.idea, a.slug)
        else:
            if out is None:
                import story as S
                idx_p = os.path.join(ROOT, "output", "index.json")
                idx = json.load(open(idx_p)) if os.path.exists(idx_p) else {}
                f = S.pick_bank(a.idea)
                state_slug = a.slug or idx.get(a.idea) or (f["slug"] if f else None)
                out = os.path.join(ROOT, "output", state_slug)
            if st == "voice":
                stage_voice(out)
            elif st == "stills":
                stage_stills(out, a.jobs)
            elif st == "final":
                stage_final(out, a.jobs, set(a.redo_shots.split(",")) if a.redo_shots else None)
            elif st == "audio":
                stage_audio(out)
            elif st == "captions":
                stage_captions(out)
            elif st == "compose":
                stage_compose(out)
            elif st == "deliver":
                stage_deliver(out)
        times[st] = round(time.time() - ts, 1)
        if out:
            tp = os.path.join(out, "stage_times.json")
            old = json.load(open(tp)) if os.path.exists(tp) else {}
            old.update(times)
            json.dump(old, open(tp, "w"), indent=1)
        if a.stop_after == st:
            break
    log(f"[make_film] done in {time.time() - t0:.0f}s  stage times: {times}")


if __name__ == "__main__":
    main()
