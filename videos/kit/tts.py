"""Narration: Piper TTS per sentence (generated at the source pace via length_scale - never sped up or
pitch-shifted afterwards), silence squeeze (no gap > MAX_SIL), auto-tuned to the video's words/sec target,
extension beats added until MIN_AUDIO, faster-whisper word timestamps, red-word marking.

python3 kit/tts.py <slug>   ->  build/voice.wav, build/timeline.json, videos/<slug>/script.txt
"""
import json, os, re, subprocess, difflib, wave, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import video, bdir, vdir, VOICES, args, tts_hash
import progress

PY = sys.executable

SR = 48000
NUM = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
       "ten": 10, "eleven": 11, "twelve": 12, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
       "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100}


def numval(tok):
    t = tok.lower().strip(".,!?\"")
    if t in NUM:
        return NUM[t]
    if "-" in t:
        a, _, b = t.partition("-")
        if a in NUM and b in NUM:
            return NUM[a] + NUM[b]
    if t.isdigit():
        return int(t)
    return None


def countdown_values(words):
    """Group consecutive number words into values: 'two fifty' -> 250, 'two hundred' -> 200, 'ten' -> 10."""
    vals = [None] * len(words)
    i = 0
    while i < len(words):
        v = numval(words[i]["norm_raw"])
        if v is None:
            i += 1
            continue
        j = i + 1
        total = v
        if j < len(words) and numval(words[j]["norm_raw"]) is not None:
            v2 = numval(words[j]["norm_raw"])
            if v2 == 100:
                total = v * 100; j += 1
            elif v < 10 and v2 >= 10:
                total = v * 100 + v2; j += 1
        for k in range(i, j):
            vals[k] = total
        i = j
    return vals


def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a, sr


def write_wav(p, a, sr=SR):
    with wave.open(p, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def squeeze(a, sr, max_sil, keep):
    """Trim ends; cut every internal silence longer than max_sil down to `keep` seconds (a cut, not a speed change)."""
    hop = int(0.01 * sr)
    n = len(a) // hop
    rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))
    sil = rms < 0.01
    nz = np.where(~sil)[0]
    first, last = max(0, nz[0] - 2), min(n, nz[-1] + 4)
    idx = []
    i = first
    lim = int(keep / 0.01)
    while i < last:
        if sil[i]:
            j = i
            while j < last and sil[j]:
                j += 1
            if (j - i) * 0.01 > max_sil:
                idx.extend(range(i, i + lim // 2)); idx.extend(range(j - (lim - lim // 2), j))
            else:
                idx.extend(range(i, j))
            i = j
        else:
            idx.append(i); i += 1
    out = np.concatenate([a[k * hop:(k + 1) * hop] for k in idx])
    f = int(0.004 * sr)
    out[:f] *= np.linspace(0, 1, f); out[-f:] *= np.linspace(1, 0, f)
    return out


def spoken(text):
    t = re.sub(r"\b([A-Z]{2,})\b", lambda m: m.group(1).lower(), text)
    return t.replace("...", ",").replace("“", '"').replace("”", '"').replace("a.m.", "A M").replace("—", ", ")


class Voice:
    def __init__(self, cfg, slug):
        self.cfg = cfg
        self.dir = str(bdir(slug) / "tts")
        Path(self.dir).mkdir(parents=True, exist_ok=True)
        self.engine = os.environ.get("KIT_TTS", getattr(cfg, "ENGINE", "piper"))
        self.onnx = str(VOICES / (cfg.VOICE + ".onnx"))
        if self.engine == "piper" and not Path(self.onnx).exists():
            VOICES.mkdir(parents=True, exist_ok=True)
            subprocess.run([PY, "-m", "piper.download_voices", "--download-dir", str(VOICES), cfg.VOICE], check=True)
        self.max_sil = getattr(cfg, "MAX_SIL", 0.35)
        self.keep = getattr(cfg, "SQUEEZE_TO", 0.22)
        self.speaker = getattr(cfg, "SPEAKER", None)

    def synth(self, sid, text, ls):
        key = f"{text}|{self.engine}|{self.cfg.VOICE}|{self.speaker}|{ls:.3f}|{self.max_sil}|{self.keep}"
        out = os.path.join(self.dir, f"{sid}.wav")
        kp = out + ".key"
        if os.path.exists(out) and os.path.exists(kp) and open(kp).read() == key:
            return out, key
        raw = os.path.join(self.dir, f"{sid}_raw.wav")
        if self.engine == "edge":
            return self.synth_edge(sid, text, ls, out, kp, key)
        cmd = [PY, "-m", "piper", "-m", self.onnx, "--length-scale", f"{ls:.3f}", "--noise-scale", "0.55",
               "--noise-w-scale", "0.7", "--sentence-silence", "0.0", "-f", raw]
        if self.speaker is not None:
            cmd += ["-s", str(self.speaker)]
        subprocess.run(cmd, input=spoken(text).encode(), check=True, capture_output=True)
        r48 = raw.replace("_raw", "_48k")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-ar", str(SR), "-ac", "1", r48], check=True)
        a, sr = read_wav(r48)
        write_wav(out, squeeze(a, sr, self.max_sil, self.keep), sr)
        open(kp, "w").write(key)
        return out, key

    def synth_edge(self, sid, text, ls, out, kp, key):
        """Optional edge-tts engine (needs internet). Pace via rate (+%), never by stretching audio afterwards."""
        import asyncio, edge_tts
        rate = f"{int(round((1 / ls - 1) * 100)):+d}%"
        mp3 = os.path.join(self.dir, f"{sid}_edge.mp3")

        async def go():
            com = edge_tts.Communicate(spoken(text), getattr(self.cfg, "EDGE_VOICE", "en-US-AnaNeural"), rate=rate)
            with open(mp3, "wb") as fh:
                async for ch in com.stream():
                    if ch["type"] == "audio":
                        fh.write(ch["data"])
        asyncio.run(go())
        r48 = os.path.join(self.dir, f"{sid}_48k.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp3, "-ar", str(SR), "-ac", "1", r48], check=True)
        a, sr = read_wav(r48)
        write_wav(out, squeeze(a, sr, self.max_sil, self.keep), sr)
        open(kp, "w").write(key)
        return out, key


def tokens(text):
    out = []
    for raw in text.split():
        disp = raw.replace("“", "").replace("”", "").replace('"', "").strip(".,!;:")
        if not disp or disp in ("—", "-"):
            continue
        letters = re.sub(r"[^A-Za-z]", "", disp)
        red = len(letters) > 1 and letters.isupper() and letters not in ("AM",)
        out.append(dict(text=disp.upper(), red=red, norm=re.sub(r"[^a-z0-9]", "", disp.lower()),
                        norm_raw=disp.lower()))
    return out


_model = None


def whisper_words(path):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=2)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = _model.transcribe(np.frombuffer(pcm, np.float32).copy(), word_timestamps=True, language="en", beam_size=5)
    return [(re.sub(r"[^a-z0-9]", "", w.word.lower()), w.start, w.end) for s in segs for w in s.words
            if re.sub(r"[^a-z0-9]", "", w.word.lower())]


def align(toks, words, dur):
    a, b = [t["norm"] for t in toks], [w[0] for w in words]
    st, en = [None] * len(toks), [None] * len(toks)
    for blk in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            st[blk.a + k], en[blk.a + k] = words[blk.b + k][1], words[blk.b + k][2]
    known = [i for i in range(len(toks)) if st[i] is not None]
    pts = [(-1, 0.0)] + [(i, st[i]) for i in known] + [(len(toks), dur)]
    for (i0, t0), (i1, t1) in zip(pts, pts[1:]):
        gap = list(range(i0 + 1, i1))
        if not gap:
            continue
        cur = en[i0] if i0 >= 0 and en[i0] is not None else t0
        span = max(0.05, t1 - cur)
        wts = [max(1, len(toks[g]["norm"])) for g in gap]
        for g, w in zip(gap, wts):
            st[g] = cur; cur += span * w / sum(wts); en[g] = cur
    for i in range(len(toks)):
        st[i] = max(0.0, min(st[i], dur)); en[i] = max(st[i] + 0.05, min(en[i], dur))
        if i and st[i] < st[i - 1] + 0.04:
            st[i] = st[i - 1] + 0.04
    return st, en, len(known) / max(1, len(toks))


def build_order(story, n_extra):
    order = list(story.S)
    for after, sent in story.EXTRA[:n_extra]:
        idx = [s[0] for s in order].index(after)
        order.insert(idx + 1, sent)
    return order


def main(slug):
    cfg, story, scene = video(slug)
    B = bdir(slug)
    V = Voice(cfg, slug)
    lo, hi = cfg.WPS
    target = getattr(cfg, "WPS_TARGET", (lo + hi) / 2)
    gap = getattr(cfg, "SENT_GAP", 0.2)
    lead = 0.08
    min_audio = getattr(cfg, "MIN_AUDIO", 140.0)
    st_path = str(B / "tts_state.json")
    ls = json.load(open(st_path))["length_scale"] if os.path.exists(st_path) else cfg.LENGTH_SCALE
    all_sent = list(story.S) + [e[1] for e in story.EXTRA]
    for it in range(5):
        durs, keys = {}, {}
        for sid, text, beats, light in all_sent:
            p, key = V.synth(sid, text, ls)
            durs[sid], keys[sid] = len(read_wav(p)[0]) / SR, key

        def total(n):
            return lead + sum(durs[s[0]] + gap for s in build_order(story, n))

        n_extra = 0
        while total(n_extra) < min_audio and n_extra < len(story.EXTRA):
            n_extra += 1
        order = build_order(story, n_extra)
        nwords = sum(len(tokens(s[1])) for s in order)
        wps = nwords / total(n_extra)
        print(f"[{slug}] iter {it}: length_scale {ls:.3f} -> {total(n_extra):.1f}s, {n_extra} extra beats, {wps:.2f} wps")
        if lo + 0.05 <= wps <= hi - 0.05:
            break
        ls = max(0.45, min(1.6, ls * wps / target))
    json.dump({"length_scale": ls}, open(st_path, "w"))
    countdown = set(getattr(story, "COUNTDOWN", []))
    pieces = [np.zeros(int(lead * SR), np.float32)]
    t = lead
    timeline, match = [], []
    for sid, text, beats, light in order:
        p = os.path.join(V.dir, f"{sid}.wav")
        a, _ = read_wav(p)
        d = len(a) / SR
        toks = tokens(text)
        cache = p + ".words.json"
        if os.path.exists(cache) and json.load(open(cache)).get("key") == keys[sid]:
            ww = json.load(open(cache))["words"]
        else:
            ww = whisper_words(p)
            json.dump({"key": keys[sid], "words": ww}, open(cache, "w"))
        s0, e0, m = align(toks, ww, d)
        match.append(m)
        if getattr(cfg, "RED_NUMBERS", False) and sid in countdown:
            for tk, v in zip(toks, countdown_values(toks)):
                if v is not None and v < 300:
                    tk["red"] = True
        for tk in toks:
            if tk["norm"] in getattr(cfg, "RED_ALWAYS", ()):
                tk["red"] = True
        for tk, a0, b0 in zip(toks, s0, e0):
            tk["start"], tk["end"] = round(t + a0, 3), round(t + b0, 3)
        timeline.append(dict(id=sid, text=text, start=round(t, 3), speech_end=round(t + d, 3), end=round(t + d + gap, 3),
                             light=light, beats=beats, words=toks))
        pieces += [a, np.zeros(int(gap * SR), np.float32)]
        t += d + gap
    voice = np.concatenate(pieces)
    voice = voice / max(1e-6, np.abs(voice).max()) * 0.89
    write_wav(str(B / "voice.wav"), voice)
    nwords = sum(len(s["words"]) for s in timeline)
    wps = nwords / t
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(B / "voice.wav"), "-c:a", "flac", str(B / "voice.flac")], check=True)
    json.dump(dict(duration=round(t, 3), n_extra=n_extra, words=nwords, wps=round(wps, 3), length_scale=ls,
                   source_hash=tts_hash(slug),
                   whisper_match=round(float(np.mean(match)), 3), sentences=timeline),
              open(B / "timeline.json", "w"), indent=1)
    with open(vdir(slug) / "script.txt", "w", encoding="utf-8") as f:
        f.write(f"{cfg.TITLE.upper()}\n(narrator: {cfg.NARRATOR}; voice {cfg.VOICE}; CAPS = red caption words)\n\n")
        for i, s in enumerate(timeline, 1):
            f.write(f"{i}. {s['text']}\n")
        f.write("(hard cut to black)\n")
    ok = lo <= wps <= hi and t >= 135
    progress.mark(slug, "tts", ok=ok, seconds=round(t, 1), words=nwords, wps=round(wps, 2), extra_beats=n_extra,
                  length_scale=round(ls, 3))
    print(f"[{slug}] narration {t:.1f}s, {nwords} words, {wps:.2f} wps (target {lo}-{hi}), extras {n_extra}, "
          f"whisper match {np.mean(match):.3f}")


if __name__ == "__main__":
    main(args()[0])
