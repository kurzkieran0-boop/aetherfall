#!/usr/bin/env python3
"""Voiceover for a series part: one WAV per narration line.

Engine order: Kokoro (kokoro-onnx, weights cached in .cache/kokoro) -> Piper ->
edge-tts. Every WAV is trimmed, measured, and given word timings so captions
and shots can be fitted to the real audio.

usage: tts.py <timeline.json> <out_dir>
"""
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache")
SR = 24000


def clean(text):
    return re.sub(r"\*", "", text).strip()


def tokens(text):
    return clean(text).split()


# ------------------------------------------------------------------ engines
_kokoro = None


def kokoro(text, voice, speed, lang):
    global _kokoro
    from kokoro_onnx import Kokoro

    if _kokoro is None:
        _kokoro = Kokoro(os.path.join(CACHE, "kokoro", "kokoro-v1.0.onnx"), os.path.join(CACHE, "kokoro", "voices-v1.0.bin"))
    samples, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
    return np.asarray(samples, dtype=np.float32), sr


def piper(text, voice_cfg, speed, out_tmp):
    model = voice_cfg.get("piperModel", os.path.join(CACHE, "piper", "en_US-amy-medium.onnx"))
    if not os.path.exists(model):
        raise RuntimeError("piper model missing: " + model)
    subprocess.run(["piper", "--model", model, "--length_scale", str(1 / speed), "--output_file", out_tmp], input=text.encode(), check=True, capture_output=True)
    s, sr = sf.read(out_tmp, dtype="float32")
    return s, sr


def edge(text, voice_cfg, speed, out_tmp):
    rate = f"{int(round((speed - 1) * 100)):+d}%"
    mp3 = out_tmp + ".mp3"
    subprocess.run(["edge-tts", "--voice", voice_cfg.get("edgeVoice", "en-US-AnaNeural"), "--rate", rate, "--text", text, "--write-media", mp3], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), out_tmp], check=True)
    s, sr = sf.read(out_tmp, dtype="float32")
    return s, sr


def synth(text, cfg, speed, tmp):
    order = [cfg.get("engine", "kokoro")] + cfg.get("fallbacks", ["piper", "edge-tts"])
    errs = []
    for eng in order:
        try:
            if eng == "kokoro":
                return kokoro(text, cfg.get("voice", "af_bella"), speed, cfg.get("lang", "en-us")) + (eng,)
            if eng == "piper":
                return piper(text, cfg, speed, tmp) + (eng,)
            if eng == "edge-tts":
                return edge(text, cfg, speed, tmp) + (eng,)
        except Exception as e:  # noqa: BLE001 - fall through to next engine
            errs.append(f"{eng}: {e}")
    raise RuntimeError("all TTS engines failed:\n  " + "\n  ".join(errs))


# ------------------------------------------------------------------ analysis
def envelope(s, sr, hop=0.01):
    n = int(sr * hop)
    frames = len(s) // n
    e = np.sqrt(np.mean(s[: frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)
    return e, hop


def trim(s, sr):
    e, hop = envelope(s, sr)
    thr = max(1e-4, e.max() * 0.02)
    idx = np.where(e > thr)[0]
    if len(idx) == 0:
        return s
    a = max(0, int((idx[0] * hop - 0.03) * sr))
    b = min(len(s), int(((idx[-1] + 1) * hop + 0.06) * sr))
    return s[a:b]


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 1
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


def word_times(words, s, sr):
    """Distribute words over the speech, snapping phrase boundaries (words
    ending in punctuation) to the longest internal pauses."""
    dur = len(s) / sr
    e, hop = envelope(s, sr)
    thr = max(1e-4, e.max() * 0.06)
    silent = e < thr
    # internal pauses >= 90ms
    pauses = []
    i = 0
    while i < len(silent):
        if silent[i]:
            j = i
            while j < len(silent) and silent[j]:
                j += 1
            if i > 3 and j < len(silent) - 3 and (j - i) * hop >= 0.09:
                pauses.append(((i * hop), (j * hop)))
            i = j
        else:
            i += 1
    breaks = [k for k, w in enumerate(words[:-1]) if re.search(r"[,.;:!?…—-]$", w)]
    chosen = []
    if breaks and pauses:
        best = sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[: len(breaks)]
        best.sort()
        # map breaks to pauses in time order using expected position
        weights = [syllables(w) + 0.6 for w in words]
        cum = np.cumsum(weights) / sum(weights)
        used = set()
        for k in breaks:
            exp = cum[k] * dur
            cand = [p for idx, p in enumerate(best) if idx not in used]
            if not cand:
                break
            p = min(cand, key=lambda p: abs((p[0] + p[1]) / 2 - exp))
            if abs((p[0] + p[1]) / 2 - exp) < dur * 0.25:
                used.add(best.index(p))
                chosen.append((k, p))
        chosen.sort(key=lambda x: x[1][0])
        # enforce monotonic
        mono, last = [], -1
        for k, p in sorted(chosen):
            if k > last and (not mono or p[0] > mono[-1][1][1]):
                mono.append((k, p))
                last = k
        chosen = mono
    # build segments
    segs = []
    start_w, start_t = 0, 0.02
    for k, (p0, p1) in chosen:
        segs.append((start_w, k, start_t, p0))
        start_w, start_t = k + 1, p1
    segs.append((start_w, len(words) - 1, start_t, dur - 0.04))
    out = [None] * len(words)
    for a, b, t0, t1 in segs:
        ws = [syllables(words[i]) + 0.6 for i in range(a, b + 1)]
        tot = sum(ws)
        t = t0
        for i, wgt in zip(range(a, b + 1), ws):
            d = (t1 - t0) * wgt / tot
            out[i] = {"w": words[i], "s": round(t, 3), "e": round(t + d, 3)}
            t += d
    return out


def main():
    tl_path, out_dir = sys.argv[1], sys.argv[2]
    tl = json.load(open(tl_path))
    cfg = tl.get("voice", {})
    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    idx = 0
    for b in tl["beats"]:
        for li, line in enumerate(b.get("narration", [])):
            if isinstance(line, str):
                line = {"text": line}
            text = clean(line["text"])
            speed = float(line.get("speed", cfg.get("speed", 1.1)))
            key = hashlib.sha1(json.dumps([cfg.get("engine"), cfg.get("voice"), cfg.get("lang"), speed, text]).encode()).hexdigest()[:12]
            fname = f"{b['id']}_{li}_{key}.wav"
            path = os.path.join(out_dir, fname)
            meta_path = path + ".json"
            if os.path.exists(path) and os.path.exists(meta_path):
                meta = json.load(open(meta_path))
            else:
                s, sr, eng = synth(text, cfg, speed, path + ".tmp.wav")
                if sr != SR:
                    import scipy.signal as ss  # only needed for fallbacks

                    s = ss.resample_poly(s, SR, sr).astype(np.float32)
                s = trim(s, SR)
                peak = float(np.abs(s).max() or 1)
                s = s * (0.89 / peak)
                sf.write(path, s, SR, subtype="PCM_16")
                words = word_times(tokens(line["text"]), s, SR)
                meta = {"engine": eng, "duration": round(len(s) / SR, 3), "words": words}
                json.dump(meta, open(meta_path, "w"))
                for ext in (".tmp.wav", ".tmp.wav.mp3"):
                    if os.path.exists(path + ext):
                        os.remove(path + ext)
            manifest.append({"idx": idx, "beat": b["id"], "line": li, "file": fname, "text": text, **meta})
            print(f"  {b['id']}.{li}  {meta['duration']:5.2f}s  [{meta['engine']}]  {text}")
            idx += 1
    json.dump({"sampleRate": SR, "lines": manifest}, open(os.path.join(out_dir, "manifest.json"), "w"), indent=1)
    total = sum(m["duration"] for m in manifest)
    print(f"voice: {len(manifest)} lines, {total:.1f}s of speech")


if __name__ == "__main__":
    main()
