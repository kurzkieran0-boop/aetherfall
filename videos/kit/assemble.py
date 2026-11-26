"""Assemble videos/<slug>/final.mp4: per-shot clips (+bloom for style B) -> concat -> one-word ASS captions
-> synthesized audio (tense bed, whooshes, paper rustle, heartbeat during countdowns, stone thuds).

python3 kit/assemble.py <slug>
"""
import json, os, subprocess, math, wave, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import video, bdir, vdir, ASSETS, FONT_NAME, args, frames_dir, final_path, preview
import progress

RFPS = int(os.environ.get("KIT_RENDER_FPS") or (15 if os.environ.get("KIT_PREVIEW") == "1" else 30))
SR = 48000
W, H, FPS = 1080, 1920, 30
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30",
       "-video_track_timescale", "15360"]


def run(cmd, cwd=None):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, cwd=cwd)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])


def nframes(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return int(out.strip() or 0)


BLOOM = ("split[a][b];[b]lutyuv=y='if(gt(val,205),val,0)':u=128:v=128,gblur=sigma=14[g];"
         "[a][g]blend=all_mode=screen:all_opacity=0.45")


def make_clip(B, FR, sh, style):
    clips = B / ("clips_preview" if preview() else "clips")
    clips.mkdir(parents=True, exist_ok=True)
    out = str(clips / (sh["id"] + ".mp4"))
    key = out + ".key"
    n = sh["frames"]
    done = str(FR / sh["id"] / ".done")
    sig = json.dumps([sh["kind"], n, sh.get("card"), RFPS, style, os.path.getmtime(done) if sh["kind"] == "render" else 0])
    if os.path.exists(out) and os.path.exists(key) and open(key).read() == sig:
        return out
    if sh["kind"] == "render":
        vf = f"fps={FPS},scale={W}:{H}:flags=lanczos" + ("" if RFPS == FPS else ",unsharp=5:5:0.6")
        if style == "B":
            vf += "," + BLOOM
        run(["ffmpeg", "-y", "-v", "error", "-framerate", str(RFPS), "-i", str(FR / sh["id"] / "f_%04d.png"),
             "-vf", vf, "-frames:v", str(n)] + ENC + [out])
    elif sh["kind"] == "card":
        vf = (f"scale={W * 2}:{H * 2},zoompan=z='1.0+0.08*on/{n}':x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)+20*on/{n}':d={n}:s={W}x{H}:fps={FPS}")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(B / "cards" / (sh["card"] + ".png")), "-vf", vf,
             "-frames:v", str(n)] + ENC + [out])
    else:   # "black" (final hard cut) and "blind" (intentional black POV shots)
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}", "-frames:v", str(n)] + ENC + [out])
    got = nframes(out)
    if got != n:
        raise RuntimeError(f"{sh['id']}: expected {n} frames, got {got}")
    open(key, "w").write(sig)
    return out


def ass_time(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def captions(tl, path, style):
    words = [w for s in tl["sentences"] for w in s["words"]]
    if style == "A":   # white, thick black outline
        st = (f"Style: Word,{FONT_NAME},128,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,"
              "100,100,2,0,1,12,5,5,40,40,0,1")
    else:              # white, soft dark shadow, thin outline
        st = (f"Style: Word,{FONT_NAME},128,&H00FFFFFF,&H00FFFFFF,&H40101010,&H70000000,0,0,0,0,"
              "100,100,2,0,1,4,7,5,40,40,0,1")
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
             "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
             "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
             "Alignment, MarginL, MarginR, MarginV, Encoding", st, "",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    blur = "" if style == "A" else "\\blur2"
    # every word gets its own slot (>= 0.1 s), strictly one at a time: a very short word nudges the next one later
    starts = []
    for w in words:
        starts.append(max(w["start"], starts[-1] + 0.1) if starts else w["start"])
    for i, w in enumerate(words):
        s0 = starts[i]
        nxt = starts[i + 1] if i + 1 < len(words) else w["end"] + 0.4
        en = min(nxt, max(w["end"] + 0.22, s0 + 0.18))
        txt = w["text"]
        size = min(172, int(1010 / (0.78 * max(1, len(txt)))))
        col = "{\\1c&H2A2AE6&}" if w["red"] else ""
        anim = f"{{\\an5\\pos(540,1210)\\fs{size}{blur}\\fscx72\\fscy72\\t(0,90,\\fscx100\\fscy100)}}"
        lines.append(f"Dialogue: 0,{ass_time(s0)},{ass_time(en)},Word,,0,0,0,,{anim}{col}{txt}")
    open(path, "w").write("\n".join(lines) + "\n")


def onepole(x, fc):
    """Cheap one-pole low-pass via FFT (no scipy)."""
    n = len(x)
    sp = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1 / SR)
    sp *= 1 / np.sqrt(1 + (fr / fc) ** 2)
    return np.fft.irfft(sp, n).astype(np.float32)


def audio(B, tl, sj, total, path, cfg):
    rng = np.random.default_rng(3)
    shots = sj["shots"]
    n = int(round(total * SR))
    t = np.arange(n) / SR
    with wave.open(str(B / "voice.wav")) as wv:
        v = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(np.float32) / 32768
    voice = np.zeros(n, np.float32)
    voice[:min(n, len(v))] = v[:n]
    # tense ambient bed: low wind + detuned drone, slow swell
    brown = np.cumsum(rng.standard_normal(n).astype(np.float32))
    brown -= np.convolve(brown, np.ones(4801) / 4801, mode="same")
    lp = onepole(brown, 300.0)
    lp /= np.abs(lp).max() + 1e-9
    base = 55 if cfg.STYLE == "A" else 65.4
    drone = (np.sin(2 * np.pi * base * t) + 0.6 * np.sin(2 * np.pi * base * 1.502 * t + 1) +
             0.35 * np.sin(2 * np.pi * base * 2.006 * t + 2)) / 1.95
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 23.0)
    bed = (0.55 * lp + 0.45 * drone * swell) * (0.042 if cfg.STYLE == "A" else 0.034)
    late = tl["duration"] * 0.6
    bed *= 1 + 0.4 * np.clip((t - late) / 10, 0, 1)
    bed *= np.clip(t / 1.0, 0, 1)
    sfx = np.zeros(n, np.float32)
    # whooshes on cuts
    last = -9
    for sh in shots[1:]:
        tc = sh["frame0"] / FPS
        if sh["kind"] == "black" or tc - last < 0.4:
            continue
        last = tc
        L = int(0.3 * SR)
        s0 = int((tc - 0.13) * SR)
        if s0 < 0 or s0 + L >= n:
            continue
        nz = rng.standard_normal(L).astype(np.float32)
        tt = np.arange(L) / L
        env = np.sin(np.pi * tt) ** 2 * np.exp(-1.5 * tt)
        lo = onepole(nz, 1500.0)
        w = lo * (1 - tt) + (nz - lo) * 0.5 * tt
        sfx[s0:s0 + L] += w / (np.abs(w).max() + 1e-9) * env * 0.08
    # paper rustle
    for sh in shots:
        if not sh.get("paper"):
            continue
        t0, d = sh["frame0"] / FPS, sh["dur"]
        for _ in range(int(6 + 10 * min(d, 1.5))):
            i0 = int((t0 + rng.uniform(0, min(d, 1.2))) * SR)
            L = int(rng.uniform(0.012, 0.05) * SR)
            if i0 + L >= n:
                continue
            nz = np.diff(np.concatenate([[0], rng.standard_normal(L)])).astype(np.float32)
            sfx[i0:i0 + L] += nz * np.exp(-np.arange(L) / (L * 0.3)) * rng.uniform(0.02, 0.05)
    # heartbeat during countdowns
    for a, b in sj.get("sfx", {}).get("heartbeat", []):
        tt = a
        while tt < b:
            for off, amp in ((0.0, 1.0), (0.2, 0.65)):
                i0 = int((tt + off) * SR)
                L = int(0.16 * SR)
                if i0 + L >= n:
                    continue
                x = np.arange(L) / SR
                sfx[i0:i0 + L] += amp * 0.32 * np.exp(-x * 30) * np.sin(2 * np.pi * (52 - 60 * x) * x)
            tt += 0.68
    # stone thuds: low sine drop + gritty crunch
    for ts in sj.get("sfx", {}).get("stone", []):
        i0 = int(ts * SR)
        L = int(0.9 * SR)
        if i0 + L >= n:
            continue
        x = np.arange(L) / SR
        thud = np.sin(2 * np.pi * (70 - 40 * x) * x) * np.exp(-x * 6)
        crunch = onepole(rng.standard_normal(L).astype(np.float32), 900.0) * np.exp(-x * 12)
        sfx[i0:i0 + L] += 0.5 * thud + 0.25 * crunch / (np.abs(crunch).max() + 1e-9)
    mix = voice + bed + sfx
    blk = shots[-1]["frame0"] / FPS
    mix[int(blk * SR):] = 0   # hard cut to black
    mix = np.clip(mix / max(1.0, np.abs(mix).max() / 0.97), -1, 1)
    with wave.open(path, "w") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())


def main(slug):
    cfg, story, scene = video(slug)
    B = bdir(slug)
    FR = frames_dir(slug)
    tl = json.loads((B / "timeline.json").read_text())
    sj = json.loads((vdir(slug) / "shots.json").read_text())
    shots = sj["shots"]
    missing = [s["id"] for s in shots if s["kind"] == "render" and not (FR / s["id"] / ".done").exists()]
    if missing:
        raise SystemExit(f"{slug}: not rendered yet: {len(missing)} shots, e.g. {missing[:5]}")
    lst = str(B / "concat.txt")
    with open(lst, "w") as f:
        for sh in shots:
            f.write(f"file '{Path(make_clip(B, FR, sh, cfg.STYLE)).as_posix()}'\n")
    total_frames = sum(s["frames"] for s in shots)
    total = total_frames / FPS
    nocap = str(B / ("video_nocap_preview.mp4" if preview() else "video_nocap.mp4"))
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", nocap])
    fonts = B / "fonts"
    fonts.mkdir(exist_ok=True)
    import shutil
    shutil.copy(ASSETS / "QRBlack.ttf", fonts / "QRBlack.ttf")
    ass = B / "captions.ass"
    captions(tl, str(ass), cfg.STYLE)
    mixp = str(B / "mix.wav")
    audio(B, tl, sj, total, mixp, cfg)
    final = str(final_path(slug))
    # ffmpeg filter args need forward slashes and an escaped drive colon on Windows; run from the build dir instead
    run(["ffmpeg", "-y", "-v", "error", "-i", nocap, "-i", mixp, "-vf", "ass=captions.ass:fontsdir=fonts",
         "-frames:v", str(total_frames), "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "1900k",
         "-bufsize", "3800k", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-movflags", "+faststart", final], cwd=str(B))
    progress.mark(slug, "assembled", ok=True, seconds=round(total, 2), mb=round(Path(final).stat().st_size / 2 ** 20, 1))
    print(f"[{slug}] wrote {final}: {total:.2f}s, {len(shots)} shots")


if __name__ == "__main__":
    main(args()[0])
