"""Assemble final.mp4: per-shot clips -> concat -> one-word ASS captions -> synthesized audio mix."""
import json, os, subprocess, math, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build")
CLIPS = os.path.join(B, "clips")
FR = os.path.join(B, "frames")
RFPS = int(os.environ.get("QR_RENDER_FPS", "30"))
SR = 48000
W, H, FPS = 1080, 1920, 30
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "30",
       "-video_track_timescale", "15360"]


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def nframes(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_packets", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    return int(out.strip() or 0)


def make_clip(sh):
    out = os.path.join(CLIPS, sh["id"] + ".mp4")
    key = out + ".key"
    n = sh["frames"]
    sig = json.dumps([sh["kind"], n, sh.get("card"), RFPS,
                      os.path.getmtime(os.path.join(FR, sh["id"], ".done")) if sh["kind"] == "render" else 0])
    if os.path.exists(out) and os.path.exists(key) and open(key).read() == sig:
        return out
    if sh["kind"] == "render":
        src = os.path.join(FR, sh["id"], "f_%04d.png")
        run(["ffmpeg", "-y", "-v", "error", "-framerate", str(RFPS), "-i", src, "-vf",
             (f"fps={FPS},scale={W}:{H}:flags=lanczos" + ("" if RFPS == FPS else ",unsharp=5:5:0.6")), "-frames:v", str(n)] + ENC + [out])
    elif sh["kind"] == "card":
        src = os.path.join(B, "cards", sh["card"] + ".png")
        # slow push-in with a tiny settle, 2x supersampled for smooth zoom
        vf = (f"scale={W * 2}:{H * 2},zoompan=z='1.0+0.07*on/{n}':x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}")
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src, "-vf", vf, "-frames:v", str(n)] + ENC + [out])
    else:
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}",
             "-frames:v", str(n)] + ENC + [out])
    got = nframes(out)
    if got != n:
        raise RuntimeError(f"{sh['id']}: expected {n} frames, got {got}")
    open(key, "w").write(sig)
    return out


def ass_time(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def captions(tl, path):
    words = [w for s in tl["sentences"] for w in s["words"]]
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
             "ScaledBorderAndShadow: yes", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
             "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
             "Alignment, MarginL, MarginR, MarginV, Encoding",
             "Style: Word,QR Montserrat Black,128,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,"
             "100,100,2,0,1,12,5,5,40,40,0,1", "",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for i, w in enumerate(words):
        st = w["start"]
        nxt = words[i + 1]["start"] if i + 1 < len(words) else w["end"] + 0.4
        en = min(nxt, max(w["end"] + 0.22, st + 0.18))
        if en - st < 0.08:
            continue
        txt = w["text"]
        size = min(172, int(1010 / (0.78 * max(1, len(txt)))))
        col = "{\\1c&H2A2AE6&}" if w["red"] else ""
        anim = f"{{\\an5\\pos(540,1210)\\fs{size}\\fscx72\\fscy72\\t(0,90,\\fscx100\\fscy100)}}"
        lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Word,,0,0,0,,{anim}{col}{txt}")
    open(path, "w").write("\n".join(lines) + "\n")


def audio(tl, shots, total, path):
    rng = np.random.default_rng(3)
    n = int(round(total * SR))
    t = np.arange(n) / SR
    # voice
    with wave.open(os.path.join(B, "voice.wav")) as wv:
        v = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(np.float32) / 32768
    voice = np.zeros(n, np.float32)
    voice[:min(n, len(v))] = v[:n]
    # ambient bed: low brown noise wind + soft detuned drone with slow swell
    white = rng.standard_normal(n).astype(np.float32)
    brown = np.cumsum(white)
    brown -= np.convolve(brown, np.ones(4801) / 4801, mode="same")  # remove drift (high-pass)
    brown /= np.abs(brown).max() + 1e-9
    spec = np.fft.rfft(brown)
    fr = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / np.sqrt(1 + (fr / 300.0) ** 4)
    lp = np.fft.irfft(spec, n).astype(np.float32)
    lp /= np.abs(lp).max() + 1e-9
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 23.0)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.6 * np.sin(2 * np.pi * 82.6 * t + 1) +
             0.35 * np.sin(2 * np.pi * 110.3 * t + 2)) / 1.95
    bed = (0.55 * lp + 0.45 * drone * swell) * 0.045
    # darker, slightly louder bed in the last act (kitchen)
    act3 = next((s["start"] for s in tl["sentences"] if s["id"] == "s22"), total)
    ramp = np.clip((t - act3) / 6.0, 0, 1)
    bed *= 1 + 0.5 * ramp
    fade = np.clip(t / 1.5, 0, 1)
    bed *= fade
    # whooshes on cuts
    from itertools import accumulate
    sfx = np.zeros(n, np.float32)
    last = -9
    for sh in shots[1:]:
        tc = sh["frame0"] / FPS
        if sh["kind"] == "black" or tc - last < 0.45:
            continue
        last = tc
        L = int(0.32 * SR)
        s0 = int((tc - 0.14) * SR)
        if s0 < 0 or s0 + L >= n:
            continue
        nz = rng.standard_normal(L).astype(np.float32)
        tt = np.arange(L) / L
        env = np.sin(np.pi * tt) ** 2 * np.exp(-1.5 * tt)
        # swept band: mix of two crude filters whose balance moves over time
        c = math.exp(-2 * math.pi * 1800 / SR)
        y = np.frombuffer(np.array(list(accumulate(nz, lambda p, x: c * p + (1 - c) * x)), np.float32), np.float32)
        hp = nz - y
        w = (y * (1 - tt) + hp * 0.5 * tt)
        sfx[s0:s0 + L] += w / (np.abs(w).max() + 1e-9) * env * 0.11
    mix = voice * 1.0 + bed + sfx
    # hard cut to black: total silence on the final black
    blk = shots[-1]["frame0"] / FPS
    mix[int(blk * SR):] = 0
    mix = np.clip(mix / max(1.0, np.abs(mix).max() / 0.97), -1, 1)
    st = np.stack([mix, mix], 1)
    with wave.open(path, "w") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((st * 32767).astype(np.int16).tobytes())


def main():
    os.makedirs(CLIPS, exist_ok=True)
    tl = json.load(open(os.path.join(B, "timeline.json")))
    shots = json.load(open(os.path.join(HERE, "shots.json")))["shots"]
    missing = [s["id"] for s in shots if s["kind"] == "render" and not os.path.exists(os.path.join(FR, s["id"], ".done"))]
    if missing:
        raise SystemExit(f"not rendered yet: {len(missing)} shots, e.g. {missing[:5]}")
    lst = os.path.join(B, "concat.txt")
    with open(lst, "w") as f:
        for sh in shots:
            f.write(f"file '{make_clip(sh)}'\n")
    total_frames = sum(s["frames"] for s in shots)
    total = total_frames / FPS
    nocap = os.path.join(B, "video_nocap.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", nocap])
    ass = os.path.join(B, "captions.ass")
    captions(tl, ass)
    mixp = os.path.join(B, "mix.wav")
    audio(tl, shots, total, mixp)
    final = os.path.join(HERE, "final.mp4")
    fonts = os.path.join(HERE, "assets")
    run(["ffmpeg", "-y", "-v", "error", "-i", nocap, "-i", mixp, "-vf",
         f"ass={ass}:fontsdir={fonts}", "-frames:v", str(total_frames), "-c:v", "libx264", "-preset", "slow",
         "-crf", "21", "-maxrate", "1900k", "-bufsize", "3800k", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
         "-movflags", "+faststart", final])
    print(f"wrote {final}: {total:.2f}s, {len(shots)} shots")


if __name__ == "__main__":
    main()
