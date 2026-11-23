"""Audio engine: Piper neural TTS voices, procedural trailer score, procedural SFX,
ambience, mixing and ffmpeg loudnorm.  No samples are used anywhere — every sound
is synthesised here (see credits.txt)."""
import json
import math
import os
import subprocess
import urllib.request
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(ROOT, "assets", "voices")
SR = 48000

# voice id -> (piper model, pitch semitones, length_scale)
VOICES = {
    "narrator": ("en_US-ryan-high", -3.0, 1.08),   # deep trailer narrator
    "girl": ("en_US-amy-medium", 1.5, 0.95),
    "girl_uk": ("en_GB-cori-high", 1.0, 0.95),
    "boy": ("en_US-kusal-medium", 3.0, 0.92),
    "kid": ("en_US-kristin-medium", 3.0, 0.95),
    "cop": ("en_US-joe-medium", -1.0, 0.95),
    "gruff": ("en_GB-northern_english_male-medium", -1.5, 1.0),
    "woman": ("en_US-lessac-medium", 0.0, 1.0),
    "man": ("en_US-norman-medium", -0.5, 1.0),
    "grandma": ("en_GB-southern_english_female-low", 1.0, 1.0),
    "mayor": ("en_US-john-medium", -1.0, 1.0),
    "baker": ("en_US-hfc_female-medium", 0.0, 1.0),
}
CROWD = ["girl", "boy", "cop", "woman", "man", "kid", "gruff", "grandma"]


def _hf(path):
    return f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{path}"


def ensure_voice(model):
    os.makedirs(VOICE_DIR, exist_ok=True)
    onnx = os.path.join(VOICE_DIR, model + ".onnx")
    if os.path.exists(onnx) and os.path.exists(onnx + ".json"):
        return onnx
    lang, rest = model.split("-", 1)
    name, q = rest.rsplit("-", 1)
    fam = lang.split("_")[0]
    base = f"{fam}/{lang}/{name}/{q}/{model}"
    for suffix, dst in ((".onnx", onnx), (".onnx.json", onnx + ".json")):
        req = urllib.request.Request(_hf(base + suffix), headers={"User-Agent": "film-pipeline"})
        with urllib.request.urlopen(req, timeout=600) as r, open(dst + ".part", "wb") as f:
            f.write(r.read())
        os.replace(dst + ".part", dst)
    return onnx


_LOADED = {}


_KOKORO = None


def kokoro_tts(text, voice, out_wav, speed=1.0, semis=0.0):
    """Kokoro-82M (Apache-2.0) neural TTS via kokoro-onnx. voice e.g. am_michael, af_heart.
    speed > 1 = faster. Optional pitch shift in semitones."""
    global _KOKORO
    import soundfile as sf
    from kokoro_onnx import Kokoro
    if _KOKORO is None:
        d = os.path.join(ROOT, "assets", "kokoro")
        _KOKORO = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, sr = _KOKORO.create(text, voice=voice, speed=speed, lang=lang)
    tmp = out_wav + ".raw.wav"
    sf.write(tmp, samples, sr)
    filt = []
    if abs(semis) > 0.01:
        rate = 2 ** (semis / 12)
        filt.append(f"asetrate={int(sr * rate)},aresample={SR},atempo={1 / rate:.5f}")
    else:
        filt.append(f"aresample={SR}")
    filt.append("highpass=f=70,acompressor=threshold=-22dB:ratio=3:attack=5:release=80")
    filt.append("silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-af", ",".join(filt), "-ac", "1", out_wav], check=True)
    os.remove(tmp)
    return wav_dur(out_wav)


def visemes(wav_path, fps=24, lead=1):
    """Per-frame mouth shapes from the line audio: [(open, wide, round)] at `fps`.
    open = loudness envelope; wide/round from spectral centroid (ee/ss vs oo/oh)."""
    x = read_wav(wav_path)
    hop = SR // fps
    n = len(x) // hop + 1
    rms, cen = np.zeros(n), np.zeros(n)
    win = np.hanning(hop * 2)
    freqs = np.fft.rfftfreq(hop * 2, 1 / SR)
    for i in range(n):
        seg = x[i * hop:i * hop + hop * 2]
        if len(seg) < hop * 2:
            seg = np.pad(seg, (0, hop * 2 - len(seg)))
        rms[i] = np.sqrt(np.mean(seg ** 2))
        sp = np.abs(np.fft.rfft(seg * win))
        cen[i] = (sp * freqs).sum() / (sp.sum() + 1e-9)
    ref = np.percentile(rms[rms > 0], 92) if (rms > 0).any() else 1.0
    o = np.clip((rms / (ref + 1e-9)) ** 0.8, 0, 1)
    o = np.convolve(o, [0.25, 0.5, 0.25], mode="same")         # smooth jaw, no chatter
    o[o < 0.12] = 0
    wide = np.clip((cen - 1800) / 2200, 0, 1)
    rnd = np.clip((1500 - cen) / 900, 0, 1)
    out = [(0.0, 0.0, 0.0)] * lead + [(round(float(a) * 0.9, 3), round(float(b), 3), round(float(c), 3)) for a, b, c in zip(o, wide, rnd)]
    return out


def tts(text, voice, out_wav, speed=1.0):
    """Synthesize one line -> 48 kHz mono wav. Returns duration (s).
    speed < 1 = faster delivery (scales Piper's length_scale). voice 'crowd' = 8 voices at once.
    voice 'kokoro:<name>[:speed[:semitones]]' uses Kokoro."""
    if voice.startswith("kokoro:"):
        parts = voice.split(":")
        sp = float(parts[2]) if len(parts) > 2 else 1.0
        se = float(parts[3]) if len(parts) > 3 else 0.0
        return kokoro_tts(text, parts[1], out_wav, sp / max(0.5, speed), se)
    if voice == "crowd":
        return crowd_tts(text, out_wav, speed)
    from piper import PiperVoice, SynthesisConfig
    model, semis, ls = VOICES.get(voice, VOICES["narrator"])
    ls = ls * speed
    if model not in _LOADED:
        _LOADED[model] = PiperVoice.load(ensure_voice(model))
    pv = _LOADED[model]
    tmp = out_wav + ".raw.wav"
    with wave.open(tmp, "wb") as wf:
        pv.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=ls, noise_scale=0.6, noise_w_scale=0.7))
    # pitch shift (keeps tempo) + gentle EQ/compression, resample to 48k
    rate = 1.0 * 2 ** (semis / 12)
    filt = []
    if abs(semis) > 0.01:
        sr_in = _wav_rate(tmp)
        filt.append(f"asetrate={int(sr_in * rate)},aresample={SR},atempo={1 / rate:.5f}")
    else:
        filt.append(f"aresample={SR}")
    if voice == "narrator":
        filt.append("bass=g=5:f=110,equalizer=f=3000:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=4:attack=5:release=80")
    else:
        filt.append("highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=60")
    filt.append("silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-af", ",".join(filt), "-ac", "1", out_wav], check=True)
    os.remove(tmp)
    return wav_dur(out_wav)


def crowd_tts(text, out_wav, speed=1.0):
    parts = []
    for i, v in enumerate(CROWD):
        p = out_wav + f".c{i}.wav"
        tts(text, v, p, speed * (0.9 + 0.05 * (i % 3)))
        parts.append(read_wav(p))
        os.remove(p)
    n = max(len(x) for x in parts) + int(0.12 * SR)
    mix = np.zeros(n, np.float32)
    rng = np.random.default_rng(1)
    for x in parts:
        o = int(rng.uniform(0, 0.1) * SR)
        mix[o:o + len(x)] += x * rng.uniform(0.5, 0.8)
    mix = mix / (np.abs(mix).max() + 1e-6) * 0.9
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return wav_dur(out_wav)


def _wav_rate(p):
    with wave.open(p) as w:
        return w.getframerate()


def wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()


def read_wav(p):
    with wave.open(p) as w:
        n = w.getnframes(); ch = w.getnchannels(); sw = w.getsampwidth()
        data = np.frombuffer(w.readframes(n), dtype=np.int16 if sw == 2 else np.int32).astype(np.float32)
        data /= 32768.0 if sw == 2 else 2 ** 31
        if ch > 1:
            data = data.reshape(-1, ch).mean(1)
        return data


def write_wav(p, x, sr=SR):
    x = np.asarray(x)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    x = np.clip(x, -1, 1)
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------- synthesis kit

def t_axis(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.01, r=0.3, shape=2.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / max(r, 1e-4) * shape / 2)
    return e


def noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n).astype(np.float32)


def lowpass(x, fc):
    # one-pole cascaded x2 (cheap, fine for rumbles)
    a = math.exp(-2 * math.pi * fc / SR)
    y = np.empty_like(x)
    for _ in range(2):
        acc = 0.0
        out = np.empty_like(x)
        # vectorised IIR via lfilter-like recursion in chunks
        out = _iir1(x, a)
        x = out
    return x


def _iir1(x, a):
    try:
        from scipy.signal import lfilter
        return lfilter([1 - a], [1, -a], x).astype(np.float32)
    except Exception:
        y = np.empty_like(x)
        acc = 0.0
        b = 1 - a
        for i in range(len(x)):
            acc = b * x[i] + a * acc
            y[i] = acc
        return y


def highpass(x, fc):
    return x - lowpass(x, fc)


def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def boom(d=2.5, f0=55, seed=0):
    """Trailer hit: sub drop + noise crack + tail."""
    t = t_axis(d)
    f = f0 * (1 + 1.5 * np.exp(-t * 18))
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.sin(ph) * env(len(t), 0.003, 0.9)
    crack = highpass(noise(len(t), seed), 800) * env(len(t), 0.001, 0.08) * 0.5
    body = lowpass(noise(len(t), seed + 1), 300) * env(len(t), 0.005, 0.6) * 1.2
    return (sub * 0.9 + crack + body).astype(np.float32)


def braam(d=3.0, f0=43.65, seed=0):
    t = t_axis(d)
    x = np.zeros_like(t)
    for k, det in enumerate((0, 0.3, -0.25, 0.12)):
        x += saw(f0 * (1 + det / 100), t) + 0.5 * saw(f0 * 2 * (1 + det / 120), t)
    x = lowpass(x.astype(np.float32), 500) * 0.35
    x *= env(len(t), 0.05, d * 0.5, 1.2)
    b = boom(min(d, 2.0), f0 * 1.2, seed)[:len(x)] * 0.6
    x[:len(b)] += b
    return x


def riser(d=3.0, seed=0):
    t = t_axis(d)
    n = noise(len(t), seed)
    sweep = np.zeros_like(n)
    # crude band sweep: mix of lowpassed noise with rising cutoff
    seg = 12
    L = len(n) // seg
    for i in range(seg):
        fc = 300 * (2 ** (i / seg * 4.5))
        sl = slice(i * L, (i + 1) * L if i < seg - 1 else len(n))
        sweep[sl] = highpass(lowpass(n[sl], fc), fc * 0.3)
    tone = np.sin(2 * np.pi * np.cumsum(200 * (2 ** (t / d * 2.5))) / SR) * 0.25
    e = (t / d) ** 2.2
    return ((sweep * 0.6 + tone) * e).astype(np.float32)


def stomp(seed=0, power=1.0):
    d = 2.2
    t = t_axis(d)
    sub = np.sin(2 * np.pi * np.cumsum(38 * (1 + np.exp(-t * 10))) / SR) * env(len(t), 0.004, 0.7)
    rub = lowpass(noise(len(t), seed), 180) * env(len(t), 0.01, 0.9) * 2.0
    deb = highpass(noise(len(t), seed + 3), 1500) * env(len(t), 0.02, 0.35) * 0.25
    # little debris clatter
    rng = np.random.default_rng(seed)
    for k in range(8):
        i = int(rng.uniform(0.05, 1.2) * SR)
        m = min(len(t) - i, 900)
        deb[i:i + m] += highpass(noise(m, seed + k), 2500) * np.exp(-np.arange(m) / 150) * rng.uniform(0.1, 0.3)
    return ((sub + rub + deb) * power).astype(np.float32)


def roar(d=3.2, seed=0, pitch=1.0):
    """Original creature roar: detuned growling saws + formant-ish filtered noise,
    pitch contour rises then falls; amplitude wobble for throat flutter."""
    t = t_axis(d)
    contour = (70 + 40 * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.7) * pitch
    flutter = 1 + 0.15 * np.sin(2 * np.pi * 27 * t) * np.random.default_rng(seed).uniform(0.6, 1, len(t))
    ph = np.cumsum(contour) / SR
    x = (saw(1, ph) + 0.7 * saw(1, ph * 1.502) + 0.5 * saw(1, ph * 0.497)) * flutter
    x = lowpass(x.astype(np.float32), 1400)
    n = noise(len(t), seed)
    breath = highpass(lowpass(n, 2600), 500) * 0.8
    e = env(len(t), 0.25, d * 0.6, 1.0)
    out = (x * 0.6 + breath * 0.5) * e
    return np.tanh(out * 2.2).astype(np.float32) * 0.8


def siren(d, seed=0, kind="wail", pan_speed=0.0):
    t = t_axis(d)
    if kind == "wail":
        f = 750 + 450 * np.sin(2 * np.pi * t / 4.0 + seed)
    else:  # yelp
        f = 900 + 400 * np.sign(np.sin(2 * np.pi * t * 3 + seed))
    ph = np.cumsum(f) / SR
    x = (np.sin(2 * np.pi * ph) + 0.3 * np.sin(4 * np.pi * ph)) * 0.25
    return lowpass(x.astype(np.float32), 2500)


def rain_amb(d, seed=0, level=0.25):
    n = noise(int(d * SR), seed)
    hiss = highpass(lowpass(n, 6000), 800) * 0.5
    drops = np.zeros_like(n)
    rng = np.random.default_rng(seed)
    for i in rng.integers(0, len(n) - 500, int(d * 40)):
        drops[i:i + 400] += highpass(noise(400, int(i)), 3000) * np.exp(-np.arange(400) / 60) * rng.uniform(0.05, 0.3)
    return ((hiss + drops) * level).astype(np.float32)


def city_rumble(d, seed=0, level=0.15):
    n = noise(int(d * SR), seed)
    return (lowpass(n, 90) * 3 * level).astype(np.float32)


def thunder(seed=0):
    d = 4.0
    t = t_axis(d)
    n = noise(len(t), seed)
    crack = highpass(n, 1200) * env(len(t), 0.002, 0.15) * 0.6
    roll = lowpass(n, 250) * env(len(t), 0.05, 2.5, 1.0) * 2.0
    return (crack + roll).astype(np.float32)


def footsteps(d, rate=7.0, seed=0, level=0.2, wet=True):
    n = int(d * SR)
    x = np.zeros(n, np.float32)
    rng = np.random.default_rng(seed)
    step = int(SR / rate)
    for i in range(0, n - 4000, step):
        j = i + int(rng.uniform(-0.02, 0.02) * SR)
        j = max(0, j)
        m = min(4000, n - j)
        thump = lowpass(noise(m, j), 400) * np.exp(-np.arange(m) / 500) * 1.5
        splash = highpass(noise(m, j + 1), 2000) * np.exp(-np.arange(m) / 900) * (0.6 if wet else 0.1)
        x[j:j + m] += (thump + splash) * level
    return x


def whoosh(d=0.6, seed=0):
    t = t_axis(d)
    n = noise(len(t), seed)
    e = np.sin(np.pi * t / d) ** 2
    return (highpass(lowpass(n, 3000), 400) * e * 0.6).astype(np.float32)


def glitch_hum(d, seed=0):
    t = t_axis(d)
    return (np.sin(2 * np.pi * 60 * t) * 0.1 + np.sin(2 * np.pi * 120 * t) * 0.05).astype(np.float32)


def echo(x, delays=(0.18, 0.37, 0.61, 0.9), gains=(0.6, 0.45, 0.32, 0.22)):
    y = x.copy()
    for d, g in zip(delays, gains):
        k = int(d * SR)
        y = np.concatenate([y, np.zeros(k, np.float32)]) if len(y) < len(x) + k else y
        y[k:k + len(x)] += x * g
    return y


# --------------------------------------------------------------------------- score

NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def score(duration, beats, key="D", seed=0, bpm=100):
    """Tension-following score.
    beats: list of {"t": sec, "tension": 0..1, "kind": "hit"|"riser"|"braam"|"drop"|"resolve"|None}
    Layers: sub drone, pulsing ostinato (speed+volume follow tension), string-pad chords
    (minor; resolves to major on 'resolve'), risers before hits, hits/braams on reveals,
    full drop-out ('drop') for silence moments."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    root = 38 + NOTE.get(key, 2)  # D2
    rng = np.random.default_rng(seed)
    # tension curve
    bt = sorted(beats, key=lambda b: b["t"])
    xs = [0] + [b["t"] for b in bt] + [duration]
    ys = [bt[0]["tension"] if bt else 0.3] + [b["tension"] for b in bt] + [bt[-1]["tension"] if bt else 0.3]
    ten = np.interp(t, xs, ys).astype(np.float32)
    # silence gates
    gate = np.ones(n, np.float32)
    for b in bt:
        if b.get("kind") == "drop":
            i0 = int(b["t"] * SR); i1 = int(min(duration, b["t"] + b.get("len", 1.2)) * SR)
            fade = np.linspace(1, 0, min(2400, i1 - i0))
            gate[i0:i0 + len(fade)] = np.minimum(gate[i0:i0 + len(fade)], fade)
            gate[i0 + len(fade):i1] = 0
            back = np.linspace(0, 1, min(4800, n - i1))
            gate[i1:i1 + len(back)] = np.minimum(gate[i1:i1 + len(back)], back)
    resolve_t = next((b["t"] for b in bt if b.get("kind") == "resolve"), None)
    major = (t >= resolve_t) if resolve_t is not None else np.zeros(n, bool)
    # sub drone
    drone = (np.sin(2 * np.pi * midi(root - 12) * t) * 0.5 + np.sin(2 * np.pi * midi(root - 5) * t) * 0.15)
    drone *= 0.35 + 0.4 * ten
    # pads: i - VI - iv - v minor progression (major I-IV-V-I after resolve)
    prog_m = [(0, 3, 7), (-4, 0, 3), (5, 8, 12), (7, 10, 14)]
    prog_M = [(0, 4, 7), (5, 9, 12), (7, 11, 14), (0, 4, 7)]
    bar = 60 / bpm * 4
    pad = np.zeros(n, np.float32)
    for i in range(int(duration / bar) + 1):
        a, b_ = int(i * bar * SR), int(min(duration, (i + 1) * bar) * SR)
        if a >= n:
            break
        seg_t = t[a:b_]
        maj = major[a]
        chord = (prog_M if maj else prog_m)[i % 4]
        s = np.zeros(len(seg_t), np.float32)
        for k, iv in enumerate(chord):
            f = midi(root + 12 + iv)
            for det in (-0.12, 0.0, 0.11):
                s += saw(f * (1 + det / 100), seg_t) * 0.08
        e = np.minimum(1, (seg_t - seg_t[0]) / 0.8) * np.minimum(1, (seg_t[-1] - seg_t + 1e-3) / 0.5)
        pad[a:b_] = s * e
    pad = lowpass(pad, 1200) * (0.25 + 0.35 * ten)
    # ostinato pulse (16ths that accelerate feel with tension)
    puls = np.zeros(n, np.float32)
    six = 60 / bpm / 4
    k = 0
    tt = 0.0
    seq = [0, 12, 7, 12, 3, 12, 7, 15]
    while tt < duration:
        i = int(tt * SR)
        lvl = ten[min(i, n - 1)]
        if lvl > 0.25:
            m = min(int(six * SR), n - i)
            nt = root + 12 + seq[k % len(seq)] + (4 if major[min(i, n - 1)] and seq[k % len(seq)] == 3 else 0)
            tone = saw(midi(nt), np.arange(m) / SR) * np.exp(-np.arange(m) / (SR * 0.06))
            puls[i:i + m] += tone * 0.22 * lvl
        k += 1
        tt += six
    puls = lowpass(puls, 2200)
    # percussion: low toms on beats when tension high
    perc = np.zeros(n, np.float32)
    beat = 60 / bpm
    tt = 0.0
    while tt < duration:
        i = int(tt * SR)
        lvl = ten[min(i, n - 1)]
        if lvl > 0.6:
            hit = boom(0.5, 70, int(tt * 10))[: n - i] * 0.25 * lvl
            perc[i:i + len(hit)] += hit
        tt += beat if lvl < 0.85 else beat / 2
    mix = (drone + pad + puls + perc) * gate
    # risers + hits
    for b in bt:
        kind = b.get("kind")
        i = int(b["t"] * SR)
        if kind in ("hit", "braam"):
            r = riser(2.0, int(b["t"] * 7)) * 0.5
            j = max(0, i - len(r))
            if i - j > 0:  # riser ends exactly on the hit (trimmed at its start near t=0)
                seg = r[len(r) - (i - j):]
                mix[j:j + len(seg)] += seg[: len(mix) - j]
            h = (braam(3.0, midi(root - 12), int(b["t"])) if kind == "braam" else boom(2.5, 50, int(b["t"]))) * 0.9
            mix[i:i + len(h)] += h[: n - i]
        elif kind == "riser":
            r = riser(b.get("len", 3.0), int(b["t"] * 3)) * 0.5
            mix[i:i + len(r)] += r[: n - i]
        elif kind == "resolve":
            # warm sustained major chord swell
            d = min(duration - b["t"], 8.0)
            tt_ = t_axis(d)
            s = sum(np.sin(2 * np.pi * midi(root + 12 + iv) * tt_) for iv in (0, 4, 7, 12, 16)) * 0.08
            s *= np.minimum(1, tt_ / 1.5) * np.minimum(1, (d - tt_) / 2.0)
            mix[i:i + len(s)] += s[: n - i]
    return np.tanh(mix * 1.2).astype(np.float32) * 0.8


# ----------------------------------------------------------------------------- mix

def place(bus, x, t, gain=1.0):
    i = int(t * SR)
    if i >= len(bus) or i < -len(x):
        return
    if i < 0:
        x = x[-i:]; i = 0
    m = min(len(x), len(bus) - i)
    bus[i:i + m] += x[:m] * gain


def duck(music, voice, amount=0.45, release=0.25):
    envv = np.abs(voice)
    k = int(release * SR)
    from numpy.lib.stride_tricks import sliding_window_view  # noqa
    # smooth envelope
    kern = np.ones(k, np.float32) / k
    sm = np.convolve(envv, kern, mode="same")
    g = 1 - amount * np.clip(sm * 8, 0, 1)
    return music * g


def loudnorm(inp, out, I=-14, TP=-1.0, LRA=9):
    """Two-pass EBU R128 loudness normalisation."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", inp, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = p.stderr
    js = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", inp, "-af", af, "-ar", str(SR), out], check=True)
    return js


# ------------------------------------------------------------- comedy SFX + score

def bell(seed=0, f0=392.0, d=3.5):
    t = t_axis(d)
    x = np.zeros_like(t)
    for ratio, amp, dec in ((0.5, 0.5, 2.0), (1.0, 1.0, 1.6), (1.19, 0.5, 1.0), (1.5, 0.35, 0.8), (2.0, 0.4, 0.6), (2.74, 0.2, 0.4)):
        x += np.sin(2 * np.pi * f0 * ratio * t) * amp * np.exp(-t / dec)
    return (x * 0.25 * np.minimum(1, t / 0.003)).astype(np.float32)


def splat(seed=0):
    n = noise(int(0.7 * SR), seed)
    body = lowpass(n, 700) * env(len(n), 0.002, 0.18) * 2.5
    wet = highpass(lowpass(n, 4000), 900) * env(len(n), 0.01, 0.3) * 0.6
    return (body + wet).astype(np.float32)


def cheer(d=3.0, seed=0):
    n = noise(int(d * SR), seed)
    x = highpass(lowpass(n, 3500), 300)
    t = t_axis(d)
    amp = np.minimum(1, t / 0.3) * np.exp(-np.maximum(0, t - 1.2) / 1.2)
    wob = 1 + 0.3 * np.sin(2 * np.pi * 5.5 * t)
    return (x * amp * wob * 0.5).astype(np.float32)


def horn(d=0.5, seed=0):
    t = t_axis(d)
    x = (saw(415, t) + saw(523, t)) * 0.2
    return (lowpass(x.astype(np.float32), 2500) * np.minimum(1, t / 0.01) * np.minimum(1, (d - t) / 0.03)).astype(np.float32)


def bonk(seed=0):
    t = t_axis(0.5)
    f = 300 * np.exp(-t * 6) + 80
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.8).astype(np.float32)


def sprinkler(d=3.0, seed=0):
    n = noise(int(d * SR), seed)
    t = t_axis(d)
    chk = (np.sin(2 * np.pi * 7 * t) > 0.6).astype(np.float32) * 0.6 + 0.4
    return (highpass(n, 2500) * chk * 0.35).astype(np.float32)


def pluck(f, d=0.35):
    t = t_axis(d)
    x = (2 * np.abs(2 * ((f * t) % 1) - 1) - 1)  # triangle
    return (x * np.exp(-t * 9) * np.minimum(1, t / 0.002)).astype(np.float32)


def score_playful(duration, beats, key="F", seed=0, bpm=128):
    """Bouncy comedy score: plucked major-key ostinato + walking bass + claps; busier with
    'tension'; 'hit' = brass stab chord; 'drop' = full stop; 'resolve' = big major finish."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    root = 41 + NOTE.get(key, 5)  # F2
    bt = sorted(beats, key=lambda b: b["t"])
    xs = [0] + [b["t"] for b in bt] + [duration]
    ys = [bt[0]["tension"] if bt else 0.4] + [b["tension"] for b in bt] + [bt[-1]["tension"] if bt else 0.4]
    ten = np.interp(t, xs, ys).astype(np.float32)
    gate = np.ones(n, np.float32)
    for b in bt:
        if b.get("kind") == "drop":
            i0 = int(b["t"] * SR); i1 = int(min(duration, b["t"] + b.get("len", 1.2)) * SR)
            gate[i0:i1] = 0
            back = np.linspace(0, 1, min(2400, n - i1)); gate[i1:i1 + len(back)] *= back
    mix = np.zeros(n, np.float32)
    beat = 60 / bpm
    prog = [(0, 4, 7), (9, 12, 16), (5, 9, 12), (7, 11, 14)]  # I vi IV V
    bass_walk = [0, 4, 7, 9]
    k = 0
    tt = 0.0
    while tt < duration:
        i = int(tt * SR)
        lv = float(ten[min(i, n - 1)])
        bar = int(tt / (beat * 4))
        ch = prog[bar % 4]
        step = k % 8
        # bass on every beat (walking)
        if step % 2 == 0:
            bn = root + ch[0] + bass_walk[(step // 2) % 4] * (1 if lv > 0.5 else 0)
            x = pluck(midi(bn), 0.4) * 0.55
            mix[i:i + len(x)] += x[: n - i]
        # plucked arpeggio on 8ths; 16ths when tense
        notes = [ch[0], ch[1], ch[2], ch[1] + 12 if lv > 0.6 else ch[1]]
        for sub in ((0,) if lv < 0.65 else (0, 0.5)):
            j = int((tt + sub * beat / 2) * SR)
            x = pluck(midi(root + 24 + notes[(k + int(sub * 2)) % 4]), 0.25) * (0.22 + 0.18 * lv)
            mix[j:j + len(x)] += x[: max(0, n - j)]
        # claps on 2 and 4 when lively
        if lv > 0.45 and step in (2, 6):
            c = highpass(noise(int(0.12 * SR), k), 1500) * np.exp(-np.arange(int(0.12 * SR)) / 900) * 0.25
            mix[i:i + len(c)] += c[: n - i]
        if lv > 0.7 and step in (0, 4):
            kk = boom(0.3, 60, k)[: n - i] * 0.3
            mix[i:i + len(kk)] += kk
        tt += beat / 2
        k += 1
    mix *= gate
    for b in bt:
        i = int(b["t"] * SR)
        if b.get("kind") in ("hit", "braam"):
            d = 0.6
            tt_ = t_axis(d)
            stab = sum(saw(midi(root + 12 + iv), tt_) for iv in (0, 4, 7, 12)) * 0.12
            stab = lowpass(stab.astype(np.float32), 2200) * np.exp(-tt_ * 5)
            mix[i:i + len(stab)] += stab[: n - i]
        elif b.get("kind") == "riser":
            r = riser(b.get("len", 2.0), int(b["t"])) * 0.35
            mix[i:i + len(r)] += r[: n - i]
        elif b.get("kind") == "resolve":
            d = min(duration - b["t"], 6.0)
            tt_ = t_axis(d)
            s_ = sum(np.sin(2 * np.pi * midi(root + 12 + iv) * tt_) for iv in (0, 4, 7, 12, 16, 19)) * 0.07
            s_ *= np.minimum(1, tt_ / 0.4) * np.minimum(1, (d - tt_) / 1.5)
            mix[i:i + len(s_)] += s_[: n - i]
    return np.tanh(mix * 1.3).astype(np.float32) * 0.8


def birds(d, seed=0, level=0.12):
    n = int(d * SR)
    x = np.zeros(n, np.float32)
    rng = np.random.default_rng(seed)
    for _ in range(int(d * 1.6)):
        i = int(rng.uniform(0, d - 0.5) * SR)
        f0 = rng.uniform(2500, 4500)
        for c in range(rng.integers(2, 5)):
            m = int(0.07 * SR)
            tt = np.arange(m) / SR
            f = f0 * (1 + rng.uniform(-0.3, 0.3) * tt / 0.07)
            ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / 0.07)
            j = i + c * int(0.1 * SR)
            x[j:j + m] += ch[: max(0, n - j)] * rng.uniform(0.3, 1)
    return x * level


# ============================================================ THE KINDNESS METER: score + SFX
def soft_keys(f, d=1.6, bright=0.4):
    """Felt-piano-ish note: decaying sine partials with a soft hammer."""
    t = t_axis(d)
    x = np.zeros_like(t)
    for k, (r, a, dec) in enumerate(((1, 1.0, 1.1), (2, 0.35 * bright + 0.1, 0.6), (3, 0.12 * bright, 0.35), (4.01, 0.06, 0.25))):
        x += np.sin(2 * np.pi * f * r * t) * a * np.exp(-t / dec)
    ham = lowpass(noise(len(t), int(f)), 1800) * np.exp(-t / 0.01) * 0.05
    return ((x * 0.22 + ham) * np.minimum(1, t / 0.004)).astype(np.float32)


def choir(freqs, d, seed=0):
    """Warm 'ooh' pad: detuned sines with slow vibrato, formant-ish lowpass."""
    t = t_axis(d)
    x = np.zeros_like(t)
    rng = np.random.default_rng(seed)
    for f in freqs:
        for det in (-0.004, 0.0, 0.005):
            vib = 1 + 0.004 * np.sin(2 * np.pi * rng.uniform(4.5, 5.5) * t + rng.uniform(0, 6))
            ph = 2 * np.pi * np.cumsum(f * (1 + det) * vib) / SR
            x += np.sin(ph) * 0.5 + 0.18 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    return lowpass((x / max(1, len(freqs) * 3)).astype(np.float32), 2400)


def score_kindness(duration, beats, seed=0, bpm=92, silences=(), swell_t=None, cut_t=None):
    """Colour-script score: lonely felt-keys pulse in D minor -> tension risers -> disaster
    percussion (taiko + braams + string ostinato) -> SILENCE before the twist -> warm D-major
    choir/strings swell on the infinity flip -> gentle resolve. beats: cue list (t, tension, kind, len)."""
    n = int(duration * SR)
    t = np.arange(n) / SR
    bt = sorted(beats, key=lambda b: b["t"])
    xs = [0] + [b["t"] for b in bt] + [duration]
    ys = [bt[0]["tension"]] + [b["tension"] for b in bt] + [bt[-1]["tension"]]
    ten = np.interp(t, xs, ys).astype(np.float32)
    ten = np.convolve(ten, np.ones(SR // 2) / (SR // 2), mode="same").astype(np.float32)
    root = 50  # D3
    swell_t = swell_t if swell_t is not None else duration
    major = t >= swell_t
    beat = 60 / bpm
    bar = beat * 4
    mix = np.zeros(n, np.float32)
    # 1) lonely pulse: felt keys arpeggio, i-VI-III-VII, gets sparser as tension rises
    prog = [(0, 3, 7), (-4, 0, 3), (3, 7, 10), (-2, 2, 5)]
    progM = [(0, 4, 7), (5, 9, 12), (-3, 0, 4), (7, 11, 14)]
    k = 0
    tt = 0.0
    while tt < duration:
        i = int(tt * SR)
        lv = ten[min(i, n - 1)]
        mj = major[min(i, n - 1)]
        ch = (progM if mj else prog)[int(tt / bar) % 4]
        if lv < 0.62 or mj:
            note = root + 12 + ch[[0, 1, 2, 1][k % 4]] + (12 if k % 8 == 6 else 0)
            x = soft_keys(midi(note), 1.8, 0.5) * (0.55 if mj else 0.45) * (1.0 - 0.5 * max(0, lv - 0.4))
            mix[i:i + len(x)] += x[: n - i]
        k += 1
        tt += beat / 2
    # 2) pads (strings) follow chords, fuller with tension; choir after the flip
    pad = np.zeros(n, np.float32)
    for bi in range(int(duration / bar) + 1):
        a, b_ = int(bi * bar * SR), int(min(duration, (bi + 1) * bar) * SR)
        if a >= n:
            break
        seg = t[a:b_]
        ch = (progM if major[a] else prog)[bi % 4]
        s = np.zeros(len(seg), np.float32)
        for iv in ch:
            for det in (-0.1, 0.0, 0.12):
                s += saw(midi(root + iv) * (1 + det / 100), seg) * 0.05
        e = np.minimum(1, (seg - seg[0]) / 1.0) * np.minimum(1, (seg[-1] - seg + 1e-3) / 0.6)
        pad[a:b_] = s * e
    mix += lowpass(pad, 900) * (0.2 + 0.55 * ten)
    # 3) disaster: string ostinato (16ths), taiko on beats, sub drone
    ost = np.zeros(n, np.float32)
    seq = [0, 0, 12, 0, 7, 0, 12, 3]
    tt, k = 0.0, 0
    while tt < duration:
        i = int(tt * SR)
        lv = ten[min(i, n - 1)]
        if lv > 0.6 and not major[min(i, n - 1)]:
            m = min(int(beat / 4 * SR), n - i)
            tone = saw(midi(root - 12 + seq[k % 8]), np.arange(m) / SR) * np.exp(-np.arange(m) / (SR * 0.07))
            ost[i:i + m] += tone * 0.3 * (lv - 0.5)
        k += 1
        tt += beat / 4
    mix += lowpass(ost, 1600)
    tt = 0.0
    while tt < duration:
        i = int(tt * SR)
        lv = ten[min(i, n - 1)]
        if lv > 0.7 and not major[min(i, n - 1)]:
            hit = boom(0.7, 62, int(tt * 13))[: n - i] * 0.5 * lv
            mix[i:i + len(hit)] += hit
            if lv > 0.88:
                h2 = boom(0.4, 90, int(tt * 17))[: n - i - int(beat / 2 * SR)] * 0.25
                j = i + int(beat / 2 * SR)
                mix[j:j + len(h2)] += h2
        tt += beat
    drone = np.sin(2 * np.pi * midi(root - 12) * t) * (0.12 + 0.3 * np.clip(ten - 0.5, 0, 1)) * (~major)
    mix += drone.astype(np.float32)
    # 4) risers into hits, braams
    for b in bt:
        i = int(b["t"] * SR)
        if b.get("kind") in ("hit", "braam"):
            r = riser(1.8, int(b["t"] * 7)) * 0.45
            j = max(0, i - len(r))
            seg = r[len(r) - (i - j):]
            mix[j:j + len(seg)] += seg[: n - j]
            h = braam(3.2, midi(root - 24), int(b["t"])) if b["kind"] == "braam" else boom(2.2, 48, int(b["t"]))
            mix[i:i + len(h)] += h[: n - i] * 0.8
    # 5) the swell: choir + strings + bell on the flip, D major
    if swell_t < duration:
        i = int(swell_t * SR)
        d = duration - swell_t
        tt_ = t_axis(d)
        sw = choir([midi(root + x) for x in (0, 4, 7, 12, 16)], d, seed) * 0.9
        sw *= np.minimum(1, tt_ / 2.2) * np.minimum(1, (d - tt_ + 1e-3) / 0.05)
        mix[i:i + len(sw)] += sw[: n - i]
        for j, (fq, dt) in enumerate(((midi(root + 24), 0.0), (midi(root + 28), 0.6), (midi(root + 31), 1.2), (midi(root + 36), 1.8))):
            bl = bell(seed + j, fq, 4.0) * 0.6
            p = i + int(dt * SR)
            mix[p:p + len(bl)] += bl[: max(0, n - p)]
    # 6) silences (hard drop before the twist), hard cut at the end
    gate = np.ones(n, np.float32)
    for a, b in silences:
        i0, i1 = int(a * SR), int(b * SR)
        f = min(int(0.35 * SR), max(1, i1 - i0))
        gate[i0:i0 + f] = np.minimum(gate[i0:i0 + f], np.linspace(1, 0, f))
        gate[i0 + f:i1] = 0
    if cut_t is not None:
        gate[int(cut_t * SR):] = 0
    return (np.tanh(mix * gate * 1.1) * 0.8).astype(np.float32)


def sfx_kindness(kind, seed=0):
    """Synthesised one-shots for THE KINDNESS METER."""
    if kind == "door_slam":
        x = boom(0.9, 70, seed) * 0.7
        k = highpass(noise(int(0.12 * SR), seed), 900) * np.exp(-np.arange(int(0.12 * SR)) / 500)
        x[:len(k)] += k * 0.9
        rat = highpass(noise(int(0.4 * SR), seed + 1), 3000) * env(int(0.4 * SR), 0.005, 0.15) * 0.15
        x[int(0.05 * SR):int(0.05 * SR) + len(rat)] += rat
        return x
    if kind == "ding":
        t = t_axis(1.0)
        x = (np.sin(2 * np.pi * 1760 * t) * np.exp(-t / 0.35) + 0.6 * np.sin(2 * np.pi * 2637 * t) * np.exp(-t / 0.25)
             + 0.3 * np.sin(2 * np.pi * 3520 * t) * np.exp(-t / 0.15))
        sh = highpass(noise(len(t), seed), 6000) * np.exp(-t / 0.08) * 0.2
        return ((x * 0.3 + sh) * np.minimum(1, t / 0.002)).astype(np.float32)
    if kind == "laugh":
        d = 2.2
        x = np.zeros(int(d * SR), np.float32)
        rng = np.random.default_rng(seed)
        for v in range(6):
            f0 = rng.uniform(180, 420)
            st = rng.uniform(0, 0.5)
            for h in range(rng.integers(3, 6)):
                tt = t_axis(0.12)
                ha = (np.sin(2 * np.pi * f0 * tt) + 0.5 * np.sin(4 * np.pi * f0 * tt)) * np.sin(np.pi * tt / 0.12) ** 2
                ha += lowpass(noise(len(tt), int(f0) + h), 2500) * 0.3 * np.sin(np.pi * tt / 0.12)
                i = int((st + h * rng.uniform(0.16, 0.22)) * SR)
                x[i:i + len(ha)] += ha[: len(x) - i] * 0.12
        return x
    if kind == "thunk":
        t = t_axis(0.35)
        x = np.sin(2 * np.pi * 180 * t * (1 + np.exp(-t * 40))) * np.exp(-t / 0.06)
        x += lowpass(noise(len(t), seed), 1200) * np.exp(-t / 0.03) * 0.6
        return (x * 0.7).astype(np.float32)
    if kind in ("glitch_tiny", "glitch"):
        d = 0.12 if kind == "glitch_tiny" else 0.9
        t = t_axis(d)
        rng = np.random.default_rng(seed)
        f = np.repeat(rng.uniform(300, 2400, int(d * 60) + 1), SR // 60)[: len(t)]
        x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.25
        x = np.round(x * 4) / 4
        x *= (rng.random(len(t) // 400 + 1).repeat(400)[: len(t)] > 0.3)
        return (x * env(len(t), 0.002, d * 0.6) * (0.6 if kind == "glitch" else 0.9)).astype(np.float32)
    if kind == "server_alarm":
        t = t_axis(2.4)
        on = ((t % 0.6) < 0.45).astype(np.float32)
        f = np.where((t % 1.2) < 0.6, 880, 660)
        return (np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.12 * on * np.minimum(1, (2.4 - t) / 0.3)).astype(np.float32)
    if kind == "meteor_fall":
        d = 2.6
        t = t_axis(d)
        f = 2400 * np.exp(-t * 0.9) + 200
        wh = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 * (t / d) ** 1.5
        roar = lowpass(noise(len(t), seed), 600) * (t / d) ** 2 * 1.2
        hiss = highpass(noise(len(t), seed + 3), 3000) * (t / d) ** 2 * 0.3
        return (wh + roar + hiss).astype(np.float32)
    if kind == "impact":
        x = boom(4.0, 38, seed) * 1.4
        cr = highpass(noise(int(0.3 * SR), seed + 1), 1500) * np.exp(-np.arange(int(0.3 * SR)) / 2500)
        x[:len(cr)] += cr
        deb = np.zeros_like(x)
        rng = np.random.default_rng(seed)
        for k in range(40):
            i = int(rng.uniform(0.15, 2.5) * SR)
            m = int(0.06 * SR)
            c = bandpass_noise(m, rng.uniform(400, 2400), seed + k) * np.exp(-np.arange(m) / 600) * rng.uniform(0.1, 0.35)
            deb[i:i + m] += c[: len(deb) - i]
        return x + deb
    if kind == "crash":
        return (boom(2.0, 60, seed) * 0.6 + bandpass_noise(int(2.0 * SR), 1200, seed) * env(int(2.0 * SR), 0.002, 0.5) * 0.5)
    if kind == "creak":
        d = 2.4
        t = t_axis(d)
        f = 55 + 25 * np.sin(2 * np.pi * 0.7 * t) + 8 * np.sin(2 * np.pi * 13 * t)
        x = saw(f, t) * 0.25
        x = lowpass(x.astype(np.float32), 700) * env(len(t), 0.4, 1.0, 1.0)
        return x + lowpass(noise(len(t), seed), 120) * 0.4 * env(len(t), 0.4, 1.0)
    if kind == "rumble":
        return city_rumble(3.0, seed, 0.9)
    if kind == "thud":
        t = t_axis(0.6)
        x = np.sin(2 * np.pi * 70 * t * (1 + 2 * np.exp(-t * 30))) * np.exp(-t / 0.12)
        x += lowpass(noise(len(t), seed), 500) * np.exp(-t / 0.05) * 0.8
        return (x * 0.9).astype(np.float32)
    if kind == "collapse":
        d = 4.5
        x = city_rumble(d, seed, 1.6)[: int(d * SR)]
        rng = np.random.default_rng(seed)
        for k in range(14):
            i = int(rng.uniform(0, d - 1.5) * SR)
            c = boom(1.2, rng.uniform(45, 90), seed + k) * rng.uniform(0.3, 0.7)
            x[i:i + len(c)] += c[: len(x) - i]
        return x
    if kind == "crack":
        x = np.zeros(int(1.2 * SR), np.float32)
        rng = np.random.default_rng(seed)
        for k in range(12):
            i = int(rng.uniform(0, 1.0) * SR)
            m = int(0.015 * SR)
            x[i:i + m] += highpass(noise(m, seed + k), 4000) * rng.uniform(0.3, 0.8)
        t = t_axis(1.2)
        x += np.sin(2 * np.pi * 1200 * t * (1 + 0.3 * t)) * np.exp(-t / 0.5) * 0.06
        return x
    if kind == "flip_burst":
        d = 3.5
        t = t_axis(d)
        wh = bandpass_noise(len(t), 3000, seed) * env(len(t), 0.02, 0.8) * 0.5
        sh = np.zeros(len(t), np.float32)
        for k, f in enumerate((1174.7, 1480, 1760, 2349.3, 2960)):
            p = int(k * 0.06 * SR)
            b = bell(seed + k, f, 2.8)
            sh[p:p + len(b)] += b[: len(sh) - p] * 0.5
        return wh + sh
    if kind == "whoosh":
        return whoosh(0.6, seed)
    if kind == "cheer":
        return cheer(2.5, seed)
    if kind == "siren":
        return siren(4.0, seed, "wail") * 0.6
    return np.zeros(int(0.1 * SR), np.float32)


def bandpass_noise(n, fc, seed=0):
    return highpass(lowpass(noise(n, seed), fc * 1.4), fc * 0.7)


def step_sound(seed=0, run=False, wet=True):
    m = int(0.18 * SR)
    t = np.arange(m) / SR
    thump = lowpass(noise(m, seed), 380) * np.exp(-t / 0.025) * (1.6 if run else 1.0)
    scuff = bandpass_noise(m, 1800, seed + 1) * np.exp(-t / 0.04) * 0.25
    splash = highpass(noise(m, seed + 2), 2500) * np.exp(-t / 0.05) * (0.35 if wet else 0.05)
    return (thump + scuff + splash).astype(np.float32)


def murmur(d, seed=0, level=0.12, voices=14):
    """Crowd babble bed: many syllabic band-passed noise voices."""
    n = int(d * SR)
    x = np.zeros(n, np.float32)
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    for v in range(voices):
        fc = rng.uniform(350, 1100)
        sy = rng.uniform(3.5, 6.0)
        am = np.clip(np.sin(2 * np.pi * sy * t + rng.uniform(0, 6)) * 0.5 + 0.5, 0, 1) ** 2
        gate = (np.sin(2 * np.pi * rng.uniform(0.15, 0.4) * t + rng.uniform(0, 6)) > -0.2).astype(np.float32)
        x += bandpass_noise(n, fc, seed + v) * am * gate
    return lowpass(x, 2200) * level / np.sqrt(voices) * 3


def screams(d, seed=0, level=0.15):
    n = int(d * SR)
    x = np.zeros(n, np.float32)
    rng = np.random.default_rng(seed)
    for k in range(int(d * 1.6)):
        i = int(rng.uniform(0, max(0.01, d - 1.0)) * SR)
        L = int(rng.uniform(0.4, 1.0) * SR)
        tt = np.arange(L) / SR
        f = rng.uniform(600, 1100) * (1 + 0.15 * np.sin(2 * np.pi * 5 * tt)) * (1 - 0.2 * tt)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.4 + bandpass_noise(L, 1500, seed + k) * 0.6
        s *= np.sin(np.pi * tt / tt[-1]) ** 0.5
        x[i:i + L] += s[: n - i] * rng.uniform(0.3, 1.0)
    return lowpass(x, 3500) * level


def fire_crackle(d, seed=0, level=0.12):
    n = int(d * SR)
    rng = np.random.default_rng(seed)
    x = lowpass(noise(n, seed), 500) * 0.4
    for k in range(int(d * 25)):
        i = int(rng.uniform(0, d) * SR)
        m = int(0.01 * SR)
        x[i:i + m] += highpass(noise(m, seed + k), 2000)[: n - i] * rng.uniform(0.2, 1.0)
    return x * level
