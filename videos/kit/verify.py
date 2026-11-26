"""Verify videos/<slug>/final.mp4 against the checklist; saves contact_sheet.png + sync_check.png next to it.

python kit/verify.py <slug>           (KIT_PREVIEW=1 checks final_preview.mp4)
Checklist: duration >= 135 s, 1080x1920, 30 fps, audio; words/sec inside the video's target; no voice gap > 0.4 s;
no frozen or repeated footage; no black frames mid-video (except scenes the config marks as intentional);
>= MIN_SHOTS distinct shots, none > 3 s; counters match every spoken countdown number (counter videos);
24-frame contact sheet + start/middle/end sync strip.
"""
import json, os, subprocess, sys, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import video, bdir, vdir, args, final_path, preview
import progress


def counter_at(keys, t):
    if not keys:
        return None
    v = keys[0][1]
    prev_t, prev_v = keys[0][0], keys[0][1]
    for kt, kv, mode in keys:
        if t >= kt:
            v, prev_t, prev_v = kv, kt, kv
            continue
        if mode == "ramp" and kt > prev_t:
            return int(round(prev_v + (kv - prev_v) * (t - prev_t) / (kt - prev_t)))
        return v
    return v


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate", "-of", "json", str(p)],
                         capture_output=True, text=True).stdout
    return json.loads(out)


def grab(src, t, w, h):
    from PIL import Image
    import io
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB")


def main(slug, quiet=False):
    from PIL import ImageDraw, Image
    cfg, story, scene = video(slug)
    B = bdir(slug)
    final = final_path(slug)
    fails, notes = [], []
    if not final.exists():
        print(f"[{slug}] MISSING {final}")
        return dict(slug=slug, path=str(final), ok=False, flaws=["final.mp4 missing"])
    p = probe(final)
    dur = float(p["format"]["duration"])
    v = [s for s in p["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    if dur < 135: fails.append(f"duration {dur:.1f}s < 135s")
    if (v["width"], v["height"]) != (1080, 1920): fails.append(f"size {v['width']}x{v['height']}")
    if v["r_frame_rate"] != "30/1": fails.append(f"fps {v['r_frame_rate']}")
    if not a: fails.append("no audio stream")
    tl = json.loads((B / "timeline.json").read_text())
    sj = json.loads((vdir(slug) / "shots.json").read_text())
    shots = sj["shots"]
    content = [s for s in shots if s["kind"] != "black"]
    seen_shots = [s for s in content if s["kind"] != "blind"]
    lo, hi = cfg.WPS
    wps = tl["words"] / tl["duration"]
    if not lo <= wps <= hi: fails.append(f"speech {wps:.2f} wps outside {lo}-{hi}")
    if tl["duration"] < 135: fails.append("narration under 2:15 (add extension beats)")
    if tl["duration"] > 170: notes.append(f"narration {tl['duration']:.0f}s is over 2:50: trim weakest middle lines")
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", str(B / "voice.wav"), "-af", "silencedetect=noise=-38dB:d=0.4",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    gaps = [l for l in r.splitlines() if "silence_duration" in l]
    if gaps: fails.append(f"{len(gaps)} voice silences > 0.4s")
    ass = B / "captions.ass"
    if ass.exists():
        n_cap = sum(1 for l in ass.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:"))
        if n_cap != tl["words"]: fails.append(f"captions {n_cap} != {tl['words']} spoken words")
        starts = [l.split(",")[1] for l in ass.read_text(encoding="utf-8").splitlines() if l.startswith("Dialogue:")]
        if starts != sorted(starts): fails.append("caption events overlap / out of order")
    need = getattr(cfg, "MIN_SHOTS", 80)
    if len(seen_shots) < need: fails.append(f"{len(seen_shots)} visible shots < {need}")
    longest = max(s["dur"] for s in content)
    if longest > 3.0: fails.append(f"shot {longest:.2f}s > 3s")
    # intentional black (video 6 blind POV): time ranges from shots flagged blind
    blind = [(s["frame0"] / 30, (s["frame0"] + s["frames"]) / 30) for s in content if s["kind"] == "blind"]
    end0 = shots[-1]["frame0"] / 30

    def in_blind(t0, t1):
        return any(t0 >= b0 - 0.05 and t1 <= b1 + 0.05 for b0, b1 in blind) or \
               any(b0 - 0.05 <= t0 <= b1 + 0.05 for b0, b1 in blind)

    nocap = B / ("video_nocap_preview.mp4" if preview() else "video_nocap.mp4")
    r = subprocess.run(["ffmpeg", "-v", "info", "-t", f"{end0 - 0.05:.2f}", "-i", str(nocap), "-vf",
                        "blackdetect=d=0.1:pic_th=0.94:pix_th=0.08", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    blacks = []
    for l in r.splitlines():
        if "black_start" in l:
            kv = dict(x.split(":") for x in l.split("]")[-1].split() if ":" in x)
            t0, t1 = float(kv["black_start"]), float(kv["black_end"])
            if not in_blind(t0, t1):
                blacks.append((round(t0, 2), round(t1, 2)))
    if blacks: fails.append(f"black frames mid-video at {blacks[:3]}")
    r = subprocess.run(["ffmpeg", "-v", "info", "-t", f"{end0 - 0.05:.2f}", "-i", str(nocap), "-vf",
                        "freezedetect=n=-62dB:d=0.5", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    frozen = []
    for l in r.splitlines():
        if "freeze_start" in l:
            t0 = float(l.split("freeze_start:")[1].split()[0])
            if not in_blind(t0, t0 + 0.5):
                frozen.append(round(t0, 2))
    if frozen: fails.append(f"frozen footage at {frozen[:3]}")
    hashes = {}
    for s in content:
        if s["kind"] == "blind":
            continue
        tm = (s["frame0"] + s["frames"] / 2) / 30
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tm:.3f}", "-i", str(nocap), "-frames:v", "1", "-vf",
                              "scale=96:170", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        hashes.setdefault(hashlib.md5(raw).hexdigest(), []).append(s["id"])
    dup = [x for x in hashes.values() if len(x) > 1]
    if dup: fails.append(f"repeated shots {dup[:3]}")
    # counters match the spoken countdown numbers
    cmis = []
    if getattr(cfg, "COUNTER", None):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from tts import countdown_values
        who = cfg.COUNTER["who"]
        keys = sj["counters"].get(who, [])
        for s in tl["sentences"]:
            if s["id"] not in getattr(story, "COUNTDOWN", []):
                continue
            vals = countdown_values([dict(norm_raw=w["text"].lower()) for w in s["words"]])
            seen = set()
            for w, val in zip(s["words"], vals):
                if val is None or (s["id"], val) in seen:
                    continue
                seen.add((s["id"], val))
                shown = counter_at(keys, w["start"] + 0.05)
                if shown != val:
                    cmis.append(f"{s['id']}: says {val}, counter shows {shown}")
        if cmis: fails.append(f"counter mismatch: {cmis[:3]}")
    # contact sheet + sync strip
    sheet = Image.new("RGB", (6 * 270, 4 * 480))
    for i in range(24):
        t = (i + 0.5) * end0 / 24
        im = grab(final, t, 270, 480)
        ImageDraw.Draw(im).text((6, 6), f"{t:6.1f}s", fill=(255, 255, 0))
        sheet.paste(im, ((i % 6) * 270, (i // 6) * 480))
    tag = "_preview" if preview() else ""
    sheet.save(vdir(slug) / f"contact_sheet{tag}.png")
    words = [w for s in tl["sentences"] for w in s["words"]]
    strip = Image.new("RGB", (3 * 360, 640))
    for i, w in enumerate([words[3], words[len(words) // 2], words[-2]]):
        t = (w["start"] + w["end"]) / 2
        im = grab(final, t, 360, 640)
        ImageDraw.Draw(im).text((6, 6), f"{t:6.2f}s expect '{w['text']}'", fill=(255, 255, 0))
        strip.paste(im, (i * 360, 0))
    strip.save(vdir(slug) / f"sync_check{tag}.png")
    mb = final.stat().st_size / 2 ** 20
    if mb > 50: notes.append(f"file {mb:.0f} MB")
    row = dict(slug=slug, path=str(final), duration=round(dur, 1), shots=len(seen_shots), wps=round(wps, 2),
               ok=not fails, flaws=fails + notes)
    progress.mark(slug, "verified", ok=not fails, **{k: row[k] for k in ("duration", "shots", "wps", "flaws")})
    if not quiet:
        print(json.dumps(row, indent=1))
    return row


if __name__ == "__main__":
    row = main(args()[0])
    sys.exit(0 if row.get("ok") else 1)
