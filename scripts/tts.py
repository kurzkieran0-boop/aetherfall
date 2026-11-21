#!/usr/bin/env python3
"""
Free, offline voiceover generator for the series template.

Reads public/episodes/<ep>/script.json and synthesises one clip per narration
sentence (cached by content hash), measures it, estimates word timings, and
writes public/episodes/<ep>/audio/voice_manifest.json. build-timeline.mjs then
assembles one WAV per narration line and derives scene durations from it.

Engine fallback chain (first that works wins, per run):
  1. kokoro       (PyTorch, `pip install kokoro soundfile`; weights from Hugging Face)
  2. kokoro-onnx  (same Kokoro-82M model, ONNX build; weights from GitHub releases)
  3. piper        (`pip install piper-tts`; voice in .models/piper/*.onnx)
  4. edge-tts     (`pip install edge-tts`; needs network)
  5. espeak-ng    (last resort so the pipeline never hard-fails)

Usage: python3 scripts/tts.py [episode]   (default: part1)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, ".models")
SR = 24000
KOKORO_ONNX_URLS = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}


def log(*a):
    print("[tts]", *a, flush=True)


# --------------------------------------------------------------------------- engines
class Engine:
    name = "base"

    def synth(self, text, voice, speed):  # -> float32 mono @ SR
        raise NotImplementedError


def parse_blend(voice):
    parts = []
    for p in voice.split(","):
        if ":" in p:
            n, w = p.split(":")
            parts.append((n.strip(), float(w)))
        else:
            parts.append((p.strip(), 1.0))
    total = sum(w for _, w in parts)
    return [(n, w / total) for n, w in parts]


class KokoroTorch(Engine):
    name = "kokoro"

    def __init__(self):
        from kokoro import KPipeline  # noqa
        import torch  # noqa
        self.torch = torch
        self.pipe = KPipeline(lang_code="a")
        # force a model/voice download now so failures surface during probing
        self.synth("Hello.", "af_heart", 1.0)

    def synth(self, text, voice, speed):
        blend = parse_blend(voice)
        packs = [self.pipe.load_voice(n) * w for n, w in blend]
        pack = sum(packs[1:], packs[0])
        chunks = [a.cpu().numpy() if hasattr(a, "cpu") else np.asarray(a)
                  for _, _, a in self.pipe(text, voice=pack, speed=speed)]
        return np.concatenate(chunks).astype(np.float32)


class KokoroOnnx(Engine):
    name = "kokoro-onnx"

    def __init__(self):
        from kokoro_onnx import Kokoro
        os.makedirs(MODELS, exist_ok=True)
        for fn, url in KOKORO_ONNX_URLS.items():
            path = os.path.join(MODELS, fn)
            if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
                log("downloading", fn, "...")
                urllib.request.urlretrieve(url, path)
        self.k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))

    def synth(self, text, voice, speed):
        blend = parse_blend(voice)
        style = sum(self.k.get_voice_style(n) * w for n, w in blend)
        samples, sr = self.k.create(text, voice=style, speed=speed, lang="en-us")
        return resample(np.asarray(samples, dtype=np.float32), sr, SR)


class Piper(Engine):
    name = "piper"

    def __init__(self):
        from piper import PiperVoice  # noqa
        d = os.path.join(MODELS, "piper")
        models = [f for f in os.listdir(d) if f.endswith(".onnx")] if os.path.isdir(d) else []
        if not models:
            raise RuntimeError("no piper voice in .models/piper (e.g. en_US-amy-medium.onnx)")
        self.voice = PiperVoice.load(os.path.join(d, models[0]))

    def synth(self, text, voice, speed):
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            self.voice.synthesize(text, w, length_scale=1.0 / speed)
        buf.seek(0)
        data, sr = sf.read(buf, dtype="float32")
        return resample(data, sr, SR)


class EdgeTTS(Engine):
    name = "edge-tts"

    def __init__(self):
        import edge_tts  # noqa
        self.edge_tts = edge_tts
        self.synth("Hello.", "", 1.0)

    def synth(self, text, voice, speed):
        import asyncio
        import tempfile
        rate = f"{int(round((speed - 1) * 100)):+d}%"
        tmp = tempfile.mktemp(suffix=".mp3")
        asyncio.run(self.edge_tts.Communicate(text, "en-US-AnaNeural", rate=rate).save(tmp))
        wav = tmp + ".wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-ac", "1", "-ar", str(SR), wav], check=True)
        data, _ = sf.read(wav, dtype="float32")
        return data


class Espeak(Engine):
    name = "espeak-ng"

    def __init__(self):
        subprocess.run(["espeak-ng", "--version"], check=True, capture_output=True)

    def synth(self, text, voice, speed):
        import tempfile
        tmp = tempfile.mktemp(suffix=".wav")
        subprocess.run(["espeak-ng", "-v", "en-us+f3", "-s", str(int(150 * speed)), "-w", tmp, text], check=True)
        data, sr = sf.read(tmp, dtype="float32")
        return resample(data, sr, SR)


ENGINES = [KokoroTorch, KokoroOnnx, Piper, EdgeTTS, Espeak]


def pick_engine(preferred=None):
    order = ENGINES
    if preferred:
        order = sorted(ENGINES, key=lambda e: 0 if e.name == preferred else 1)
    for cls in order:
        try:
            eng = cls()
            log("using engine:", cls.name)
            return eng
        except Exception as e:  # noqa
            log(f"engine {cls.name} unavailable: {type(e).__name__}: {str(e)[:160]}")
    raise SystemExit("[tts] no TTS engine available")


# --------------------------------------------------------------------------- dsp
def resample(x, sr_in, sr_out):
    if sr_in == sr_out:
        return x.astype(np.float32)
    n = int(round(len(x) * sr_out / sr_in))
    t_in = np.arange(len(x)) / sr_in
    t_out = np.arange(n) / sr_out
    return np.interp(t_out, t_in, x).astype(np.float32)


def frame_rms(x, hop=240, win=480):
    n = max(1, (len(x) - win) // hop + 1)
    out = np.empty(n, dtype=np.float32)
    for i in range(n):
        seg = x[i * hop:i * hop + win]
        out[i] = np.sqrt(np.mean(seg * seg) + 1e-12)
    return out, hop


def trim(x, pad=0.06):
    rms, hop = frame_rms(x)
    thr = rms.max() * 10 ** (-38 / 20)
    idx = np.where(rms > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] * hop - int(pad * SR))
    b = min(len(x), (idx[-1] + 2) * hop + int(pad * SR))
    y = x[a:b].copy()
    f = int(0.01 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def whisperize(x, amount=0.6, seed=7):
    """Classic phase-vocoder whisperisation: keep magnitudes, randomise phase."""
    rng = np.random.default_rng(seed)
    n, hop = 512, 128
    win = np.hanning(n).astype(np.float32)
    pad = np.concatenate([np.zeros(n), x, np.zeros(n)]).astype(np.float32)
    out = np.zeros_like(pad)
    norm = np.zeros_like(pad)
    for i in range(0, len(pad) - n, hop):
        spec = np.fft.rfft(pad[i:i + n] * win)
        mag = np.abs(spec)
        ph = rng.uniform(-np.pi, np.pi, size=mag.shape)
        frame = np.fft.irfft(mag * np.exp(1j * ph), n) * win
        out[i:i + n] += frame
        norm[i:i + n] += win * win
    wh = (out / np.maximum(norm, 1e-6))[n:n + len(x)]
    # gentle high-pass to make it airy
    wh = wh - np.convolve(wh, np.ones(24) / 24, mode="same")
    wh *= (np.sqrt(np.mean(x * x)) / (np.sqrt(np.mean(wh * wh)) + 1e-9))
    return (amount * wh + (1 - amount) * x).astype(np.float32)


def normalize(x, target_db=-20.0, peak_db=-1.5):
    rms = np.sqrt(np.mean(x * x) + 1e-12)
    y = x * (10 ** (target_db / 20) / rms)
    peak = np.abs(y).max()
    lim = 10 ** (peak_db / 20)
    if peak > lim:  # soft-knee limiter
        y = np.tanh(y / lim) * lim
    return y.astype(np.float32)


# --------------------------------------------------------------------------- word timing
def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


def word_timings(x, text):
    words = text.split()
    dur = len(x) / SR
    rms, hop = frame_rms(x)
    thr = np.median(rms[rms > 0]) * 0.18
    # find pauses (>=110ms below threshold)
    quiet = rms < thr
    pauses, i = [], 0
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
    # phrase breaks after punctuation
    breaks = [k for k, w in enumerate(words[:-1]) if re.search(r"[,;:—]|\.\.\.$", w)]
    chosen = []
    if breaks and pauses:
        best = sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[:len(breaks)]
        best.sort()
        # map in order; if fewer pauses than breaks, map to the most likely ones by position
        weights = np.array([syllables(w) + 0.6 for w in words], dtype=float)
        cum = np.cumsum(weights) / weights.sum()
        exp_t = [cum[k] * dur for k in breaks]
        used = set()
        for p in best:
            mid = (p[0] + p[1]) / 2
            k = min((k for k in range(len(breaks)) if k not in used), key=lambda k: abs(exp_t[k] - mid), default=None)
            if k is not None:
                used.add(k)
                chosen.append((breaks[k], p))
        chosen.sort()
    # build segments
    segs, start_w, start_t = [], 0, 0.05
    for k, (a, b) in chosen:
        segs.append((start_w, k + 1, start_t, a))
        start_w, start_t = k + 1, b
    segs.append((start_w, len(words), start_t, dur - 0.05))
    out = []
    for w0, w1, t0, t1 in segs:
        ws = words[w0:w1]
        if not ws:
            continue
        wt = np.array([syllables(w) + 0.6 for w in ws], dtype=float)
        edges = t0 + np.concatenate([[0], np.cumsum(wt)]) / wt.sum() * max(0.05, t1 - t0)
        for j, w in enumerate(ws):
            out.append({"w": w, "t0": round(float(edges[j]), 3), "t1": round(float(edges[j + 1]), 3)})
    return out


# --------------------------------------------------------------------------- main
def main():
    ep = sys.argv[1] if len(sys.argv) > 1 else "part1"
    ep_dir = os.path.join(ROOT, "public", "episodes", ep)
    script = json.load(open(os.path.join(ep_dir, "script.json")))
    vcfg = script.get("voice", {})
    cache = os.path.join(ep_dir, "audio", ".cache")
    os.makedirs(cache, exist_ok=True)

    engine = None
    manifest = {"episode": ep, "sampleRate": SR, "engine": None, "scenes": []}
    for scene in script["scenes"]:
        whisper = bool(scene.get("whisper"))
        sents = []
        for s in scene.get("narration", []):
            if isinstance(s, str):
                s = {"text": s}
            voice = s.get("voice") or (vcfg.get("whisperVoice") if whisper else vcfg.get("voice", "af_heart"))
            speed = s.get("speed") or (vcfg.get("whisperSpeed", 0.86) if whisper else vcfg.get("speed", 0.9))
            key = json.dumps([s["text"], voice, speed, whisper, 3], sort_keys=True)
            h = hashlib.sha1(key.encode()).hexdigest()[:14]
            wav_path = os.path.join(cache, h + ".wav")
            meta_path = os.path.join(cache, h + ".json")
            if os.path.exists(wav_path) and os.path.exists(meta_path):
                meta = json.load(open(meta_path))
            else:
                if engine is None:
                    engine = pick_engine(vcfg.get("engine"))
                log(f"synth [{scene['id']}] {s['text']}")
                x = engine.synth(s["text"], voice, speed)
                x = trim(x)
                words = word_timings(x, s["text"])
                if whisper:
                    x = whisperize(x, 0.55)
                x = normalize(x, -23.0 if whisper else -20.0)
                sf.write(wav_path, x, SR, subtype="PCM_16")
                meta = {"text": s["text"], "engine": engine.name, "duration": round(len(x) / SR, 3), "words": words}
                json.dump(meta, open(meta_path, "w"), indent=1)
            manifest["engine"] = manifest["engine"] or meta.get("engine")
            sents.append({"text": s["text"], "file": f"audio/.cache/{h}.wav", **{k: meta[k] for k in ("duration", "words")}})
        manifest["scenes"].append({"id": scene["id"], "sentences": sents})
        log(f"{scene['id']}: {sum(x['duration'] for x in sents):.2f}s voice in {len(sents)} sentences")

    out = os.path.join(ep_dir, "audio", "voice_manifest.json")
    json.dump(manifest, open(out, "w"), indent=1)
    total = sum(s["duration"] for sc in manifest["scenes"] for s in sc["sentences"])
    log(f"wrote {out}  (engine={manifest['engine']}, raw voice total {total:.1f}s)")


if __name__ == "__main__":
    main()
