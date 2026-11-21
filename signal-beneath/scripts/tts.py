#!/usr/bin/env python3
"""
Free, offline voiceover for THE SIGNAL BENEATH series template.

Reads public/episodes/<ep>/timeline.json (+ public/series.json voice settings),
synthesises every narration sentence (cached by content hash), estimates word
timings, then builds ONE WAV PER NARRATION LINE (scene) and runs it through
ffmpeg: 300-3400 Hz band-pass + a touch of radio static, so it sounds like a
recorded radio log. Writes public/episodes/<ep>/audio/voice_manifest.json.

Engine fallback chain (first that works wins):
  1. kokoro       (PyTorch build: `pip install kokoro soundfile`)
  2. kokoro-onnx  (same Kokoro-82M model, ONNX runtime; weights in .models/)
  3. piper        (`pip install piper-tts`, voice .onnx in .models/piper/)
  4. edge-tts     (`pip install edge-tts`, needs network)
  5. espeak-ng    (emergency only so the pipeline never hard-fails)

Usage: python3 scripts/tts.py [episode]      (default: part1)
"""
import hashlib, json, os, re, subprocess, sys, urllib.request
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, ".models")
SR = 24000
KOKORO_ONNX_URLS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
FX_VERSION = 4


def log(*a):
    print("[tts]", *a, flush=True)


# ----------------------------------------------------------------------------- engines
class KokoroTorch:
    name = "kokoro"

    def __init__(self):
        from kokoro import KPipeline
        self.pipe = KPipeline(lang_code="a")
        self.synth("Hello.", "af_sarah", 1.0)

    def synth(self, text, voice, speed):
        chunks = [np.asarray(a.cpu() if hasattr(a, "cpu") else a) for _, _, a in self.pipe(text, voice=voice, speed=speed)]
        return np.concatenate(chunks).astype(np.float32)


class KokoroOnnx:
    name = "kokoro-onnx"

    def __init__(self):
        from kokoro_onnx import Kokoro
        os.makedirs(MODELS, exist_ok=True)
        for fn, url in KOKORO_ONNX_URLS.items():
            p = os.path.join(MODELS, fn)
            if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
                log("downloading", fn)
                urllib.request.urlretrieve(url, p)
        self.k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))

    def synth(self, text, voice, speed):
        samples, sr = self.k.create(text, voice=voice, speed=speed, lang="en-us")
        return resample(np.asarray(samples, dtype=np.float32), sr, SR)


class Piper:
    name = "piper"

    def __init__(self):
        from piper import PiperVoice
        d = os.path.join(MODELS, "piper")
        models = sorted(f for f in os.listdir(d) if f.endswith(".onnx")) if os.path.isdir(d) else []
        if not models:
            raise RuntimeError("no piper voice in .models/piper/ (e.g. en_US-lessac-medium.onnx)")
        self.voice = PiperVoice.load(os.path.join(d, models[0]))

    def synth(self, text, voice, speed):
        import io, wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            self.voice.synthesize(text, w, length_scale=1.0 / speed)
        buf.seek(0)
        data, sr = sf.read(buf, dtype="float32")
        return resample(data, sr, SR)


class EdgeTTS:
    name = "edge-tts"

    def __init__(self):
        import edge_tts
        self.edge_tts = edge_tts
        self.synth("Hello.", "", 1.0)

    def synth(self, text, voice, speed):
        import asyncio, tempfile
        tmp = tempfile.mktemp(suffix=".mp3")
        rate = f"{int(round((speed - 1) * 100)):+d}%"
        asyncio.run(self.edge_tts.Communicate(text, "en-US-MichelleNeural", rate=rate).save(tmp))
        wav = tmp + ".wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-ac", "1", "-ar", str(SR), wav], check=True)
        return sf.read(wav, dtype="float32")[0]


class Espeak:
    name = "espeak-ng"

    def __init__(self):
        subprocess.run(["espeak-ng", "--version"], check=True, capture_output=True)

    def synth(self, text, voice, speed):
        import tempfile
        tmp = tempfile.mktemp(suffix=".wav")
        subprocess.run(["espeak-ng", "-v", "en-us+f3", "-s", str(int(150 * speed)), "-w", tmp, text], check=True)
        d, sr = sf.read(tmp, dtype="float32")
        return resample(d, sr, SR)


ENGINES = [KokoroTorch, KokoroOnnx, Piper, EdgeTTS, Espeak]


def pick_engine():
    for cls in ENGINES:
        try:
            e = cls()
            log("using engine:", cls.name)
            return e
        except Exception as ex:  # noqa
            log(f"engine {cls.name} unavailable: {type(ex).__name__}: {str(ex)[:140]}")
    raise SystemExit("[tts] no TTS engine available")


# ----------------------------------------------------------------------------- dsp
def resample(x, a, b):
    if a == b:
        return x.astype(np.float32)
    n = int(round(len(x) * b / a))
    return np.interp(np.arange(n) / b, np.arange(len(x)) / a, x).astype(np.float32)


def frame_rms(x, hop=240, win=480):
    n = max(1, (len(x) - win) // hop + 1)
    return np.array([np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2) + 1e-12) for i in range(n)], dtype=np.float32), hop


def trim(x, pad=0.05):
    rms, hop = frame_rms(x)
    idx = np.where(rms > rms.max() * 10 ** (-38 / 20))[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] * hop - int(pad * SR)); b = min(len(x), (idx[-1] + 2) * hop + int(pad * SR))
    y = x[a:b].copy(); f = int(0.01 * SR)
    y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    return y


def whisperize(x, amount=0.6, seed=9):
    """Phase-vocoder whisper: keep magnitudes, randomise phase, blend with dry."""
    rng = np.random.default_rng(seed)
    n, hop = 512, 128
    win = np.hanning(n).astype(np.float32)
    pad = np.concatenate([np.zeros(n), x, np.zeros(n)]).astype(np.float32)
    out = np.zeros_like(pad); norm = np.zeros_like(pad)
    for i in range(0, len(pad) - n, hop):
        mag = np.abs(np.fft.rfft(pad[i:i + n] * win))
        out[i:i + n] += np.fft.irfft(mag * np.exp(1j * rng.uniform(-np.pi, np.pi, mag.shape)), n) * win
        norm[i:i + n] += win * win
    wh = (out / np.maximum(norm, 1e-6))[n:n + len(x)]
    wh *= np.sqrt(np.mean(x * x)) / (np.sqrt(np.mean(wh * wh)) + 1e-9)
    return (amount * wh + (1 - amount) * x).astype(np.float32)


def normalize(x, target_db=-20.0, peak_db=-1.5):
    y = x * (10 ** (target_db / 20) / np.sqrt(np.mean(x * x) + 1e-12))
    lim = 10 ** (peak_db / 20)
    if np.abs(y).max() > lim:
        y = np.tanh(y / lim) * lim
    return y.astype(np.float32)


def radio_fx(src, dst, lo, hi, static, seed):
    """ffmpeg: steep 300-3400 Hz band-pass, light compression, + band-limited static bed."""
    fc = (f"[0:a]highpass=f={lo},highpass=f={lo},lowpass=f={hi},lowpass=f={hi},"
          f"acompressor=threshold=0.08:ratio=3:attack=5:release=120,volume=1.6[v];"
          f"[1:a]highpass=f=900,lowpass=f=4200,volume=1[n];"
          f"[v][n]amix=inputs=2:duration=first:normalize=0[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                    "-f", "lavfi", "-i", f"anoisesrc=color=white:amplitude={static}:seed={seed}:sample_rate={SR}",
                    "-filter_complex", fc, "-map", "[o]", "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", dst], check=True)


# ----------------------------------------------------------------------------- word timing
def syllables(w):
    w = re.sub(r"[^a-z]", "", w.lower())
    if not w:
        return 1
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


def word_timings(x, text):
    """Estimate per-word times: split at detected pauses mapped to punctuation, then syllable-weight."""
    words = text.split(); dur = len(x) / SR
    rms, hop = frame_rms(x)
    thr = np.median(rms[rms > 0]) * 0.18
    quiet = rms < thr; pauses = []; i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            a, b = i * hop / SR, j * hop / SR
            if b - a >= 0.11 and a > 0.15 and b < dur - 0.15:
                pauses.append((a, b))
            i = j
        else:
            i += 1
    breaks = [k for k, w in enumerate(words[:-1]) if re.search(r"[,;:.]$", w)]
    weights = np.array([syllables(w) + 0.6 for w in words], dtype=float)
    cum = np.cumsum(weights) / weights.sum()
    chosen = []
    if breaks and pauses:
        best = sorted(sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[:len(breaks)])
        used = set()
        for p in best:
            mid = (p[0] + p[1]) / 2
            k = min((k for k in range(len(breaks)) if k not in used), key=lambda k: abs(cum[breaks[k]] * dur - mid), default=None)
            if k is not None:
                used.add(k); chosen.append((breaks[k], p))
        chosen.sort()
    segs, w0, t0 = [], 0, 0.04
    for k, (a, b) in chosen:
        segs.append((w0, k + 1, t0, a)); w0, t0 = k + 1, b
    segs.append((w0, len(words), t0, dur - 0.04))
    out = []
    for a, b, s, e in segs:
        ws = words[a:b]
        if not ws:
            continue
        wt = np.array([syllables(w) + 0.6 for w in ws], dtype=float)
        edges = s + np.concatenate([[0], np.cumsum(wt)]) / wt.sum() * max(0.05, e - s)
        out += [{"w": w, "t0": round(float(edges[j]), 3), "t1": round(float(edges[j + 1]), 3)} for j, w in enumerate(ws)]
    return out


# ----------------------------------------------------------------------------- main
def main():
    ep = sys.argv[1] if len(sys.argv) > 1 else "part1"
    ep_dir = os.path.join(ROOT, "public", "episodes", ep)
    series = json.load(open(os.path.join(ROOT, "public", "series.json")))
    tl = json.load(open(os.path.join(ep_dir, "timeline.json")))
    v = {**series["voice"], **tl.get("voice", {})}
    gap = series["timing"]["sentenceGap"]
    radio = v.get("radio", {})
    cache = os.path.join(ep_dir, "audio", ".cache"); os.makedirs(cache, exist_ok=True)
    engine = None
    manifest = {"episode": ep, "sampleRate": SR, "engine": None, "voice": v["voice"], "lines": []}

    for si, scene in enumerate(tl["scenes"]):
        whisper = scene.get("delivery") == "whisper"
        voice = v["whisperVoice"] if whisper else v["voice"]
        speed = v["whisperSpeed"] if whisper else v["speed"]
        sents = []
        for s in scene.get("narration", []):
            s = {"text": s} if isinstance(s, str) else dict(s)
            key = json.dumps([s["text"], voice, speed, whisper, 2], sort_keys=True)
            h = hashlib.sha1(key.encode()).hexdigest()[:14]
            wp, mp = os.path.join(cache, h + ".wav"), os.path.join(cache, h + ".json")
            if os.path.exists(wp) and os.path.exists(mp):
                meta = json.load(open(mp))
            else:
                if engine is None:
                    engine = pick_engine()
                log(f"synth [{scene['id']}] {s['text']}")
                x = trim(engine.synth(s["text"], voice, speed))
                words = word_timings(x, s["text"])
                if whisper:
                    x = whisperize(x, 0.5)
                x = normalize(x, -21.0 if whisper else -19.0)
                sf.write(wp, x, SR, subtype="PCM_16")
                meta = {"text": s["text"], "engine": engine.name, "duration": round(len(x) / SR, 3), "words": words}
                json.dump(meta, open(mp, "w"), indent=1)
            manifest["engine"] = manifest["engine"] or meta["engine"]
            sents.append({**s, "hash": h, "duration": meta["duration"], "words": meta["words"]})

        # assemble one WAV per narration line, then radio FX on the whole line (static runs through the gaps)
        parts, t, out_s = [], 0.0, []
        for k, s in enumerate(sents):
            g = 0.0 if k == 0 else (gap + float(s.get("silenceBefore", 0)))
            if g:
                parts.append(np.zeros(int(round(g * SR)), np.float32)); t += g
            x, _ = sf.read(os.path.join(cache, s["hash"] + ".wav"), dtype="float32")
            out_s.append({"text": s["text"], "start": round(t, 3), "duration": s["duration"], "voice": bool(s.get("voice")),
                          "final": bool(s.get("final")), "silenceBefore": float(s.get("silenceBefore", 0)),
                          "words": [{"w": w["w"], "t0": round(t + w["t0"], 3), "t1": round(t + w["t1"], 3)} for w in s["words"]]})
            parts.append(x); t += len(x) / SR
        line = np.concatenate(parts) if parts else np.zeros(1, np.float32)
        lh = hashlib.sha1(json.dumps([[s["hash"] for s in sents], [s.get("silenceBefore", 0) for s in sents], gap, radio, FX_VERSION]).encode()).hexdigest()[:10]
        dry = os.path.join(cache, f"line_{lh}_dry.wav")
        out_name = f"line_{si:02d}_{scene['id']}.wav"
        out_path = os.path.join(ep_dir, "audio", out_name)
        sf.write(dry, line, SR, subtype="PCM_16")
        radio_fx(dry, out_path, radio.get("lowHz", 300), radio.get("highHz", 3400), radio.get("static", 0.01), 100 + si)
        # the 1.5 s "total silence" windows must be truly silent: gate the static bed there
        y, _ = sf.read(out_path, dtype="float32")
        for q in out_s:
            if q["silenceBefore"] > 0:
                a = int((q["start"] - q["silenceBefore"]) * SR); b = int(q["start"] * SR) - int(0.02 * SR)
                f = int(0.03 * SR)
                y[a + f:b - f] = 0
                y[a:a + f] *= np.linspace(1, 0, f); y[b - f:b] *= np.linspace(0, 1, f)
        sf.write(out_path, y, SR, subtype="PCM_16")
        dur = len(y) / SR
        manifest["lines"].append({"id": scene["id"], "file": f"audio/{out_name}", "duration": round(dur, 3), "sentences": out_s})
        log(f"{scene['id']}: line {dur:.2f}s ({len(out_s)} sentences) -> {out_name}")

    json.dump(manifest, open(os.path.join(ep_dir, "audio", "voice_manifest.json"), "w"), indent=1)
    log(f"engine={manifest['engine']} voice={v['voice']} total voice {sum(l['duration'] for l in manifest['lines']):.1f}s")


if __name__ == "__main__":
    main()
