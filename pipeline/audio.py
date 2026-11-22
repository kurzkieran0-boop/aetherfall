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
}


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


def tts(text, voice, out_wav):
    """Synthesize one line -> 48 kHz mono wav. Returns duration (s)."""
    from piper import PiperVoice, SynthesisConfig
    model, semis, ls = VOICES.get(voice, VOICES["narrator"])
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
            mix[j:j + len(r)] += r[: len(mix) - j][: i - j] if i - j > 0 else 0
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
