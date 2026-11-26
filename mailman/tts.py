"""Fast deadpan narration with Piper (generated fast at the source: length_scale, no atempo/pitch),
silence squeezing (no gap > 0.25 s), faster-whisper word timestamps.

Outputs build/voice.wav, build/timeline.json, script.txt
"""
import json, os, re, subprocess, difflib, wave
import numpy as np
from story import build_script, S, EXTRA, MIN_AUDIO, MAX_AUDIO

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build")
TTS = os.path.join(B, "tts")
os.makedirs(TTS, exist_ok=True)
VOICE_NAME = "en_US-lessac-high"
VOICE = os.path.join(HERE, "voices", VOICE_NAME + ".onnx")
LENGTH_SCALE = os.environ.get("MM_LENGTH_SCALE", "0.69")
SR = 48000
LEAD_IN = 0.08
SENT_GAP = 0.15      # silence between sentences
MAX_SIL = 0.25       # any silence longer than this is squeezed
SQUEEZE_TO = 0.18
KEY = f"{VOICE_NAME}|{LENGTH_SCALE}|{MAX_SIL}|{SQUEEZE_TO}"


def spoken(text):
    t = re.sub(r"\b([A-Z]{2,})\b", lambda m: m.group(1).lower(), text)
    t = t.replace("...", ",").replace("“", '"').replace("”", '"').replace("a.m.", "A M")
    return t


def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a, sr


def write_wav(p, a, sr=SR):
    with wave.open(p, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def squeeze(a, sr):
    """Trim ends; shrink every internal silence longer than MAX_SIL to SQUEEZE_TO (a cut, not a speed change)."""
    hop = int(0.01 * sr)
    n = len(a) // hop
    rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))
    sil = rms < 0.01
    nz = np.where(~sil)[0]
    first, last = max(0, nz[0] - 2), min(n, nz[-1] + 4)
    keep = []
    i = first
    while i < last:
        if sil[i]:
            j = i
            while j < last and sil[j]:
                j += 1
            run = j - i
            lim = int(SQUEEZE_TO / 0.01)
            if run * 0.01 > MAX_SIL:
                keep.extend(range(i, i + lim // 2))
                keep.extend(range(j - (lim - lim // 2), j))
            else:
                keep.extend(range(i, j))
            i = j
        else:
            keep.append(i)
            i += 1
    out = np.concatenate([a[k * hop:(k + 1) * hop] for k in keep])
    # 4 ms fades at the joins are unnecessary (cuts are in silence); tiny fade at the ends only
    f = int(0.004 * sr)
    out[:f] *= np.linspace(0, 1, f); out[-f:] *= np.linspace(1, 0, f)
    return out


def synth(sid, text):
    out = os.path.join(TTS, f"{sid}.wav")
    key = os.path.join(TTS, f"{sid}.txt")
    if os.path.exists(out) and os.path.exists(key) and open(key).read() == text + KEY:
        return out
    raw = os.path.join(TTS, f"{sid}_raw.wav")
    subprocess.run(["python3", "-m", "piper", "-m", VOICE, "--length-scale", LENGTH_SCALE, "--noise-scale", "0.55",
                    "--noise-w-scale", "0.7", "--sentence-silence", "0.0", "-f", raw],
                   input=spoken(text).encode(), check=True, capture_output=True)
    r48 = raw.replace("_raw", "_48k")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-ar", str(SR), "-ac", "1", r48], check=True)
    a, sr = read_wav(r48)
    write_wav(out, squeeze(a, sr), sr)
    open(key, "w").write(text + KEY)
    return out


def tokens(text):
    out = []
    for raw in text.split():
        disp = raw.replace("“", "").replace("”", "").replace('"', "").strip(".,!;:")
        if not disp:
            continue
        letters = re.sub(r"[^A-Za-z]", "", disp)
        red = len(letters) > 1 and letters.isupper() and letters not in ("AM",)
        out.append(dict(text=disp.upper(), red=red, norm=re.sub(r"[^a-z0-9]", "", disp.lower())))
    return out


_model = None


def whisper_words(path):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = _model.transcribe(np.frombuffer(pcm, np.float32).copy(), word_timestamps=True, language="en", beam_size=5)
    return [(re.sub(r"[^a-z0-9]", "", w.word.lower()), w.start, w.end) for s in segs for w in s.words
            if re.sub(r"[^a-z0-9]", "", w.word.lower())]


def align(toks, words, dur):
    a = [t["norm"] for t in toks]
    b = [w[0] for w in words]
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
    return st, en


def main():
    durs = {}
    for sid, text, beats, light in list(S) + [e[1] for e in EXTRA]:
        a, _ = read_wav(synth(sid, text))
        durs[sid] = len(a) / SR

    def total(n):
        return LEAD_IN + sum(durs[s[0]] + SENT_GAP for s in build_script(n))

    n_extra = 0
    while total(n_extra) < MIN_AUDIO and n_extra < len(EXTRA):
        n_extra += 1
    order = build_script(n_extra)
    print(f"base narration {total(0):.1f}s -> {n_extra} extra story beats -> {total(n_extra):.1f}s")
    if total(n_extra) > MAX_AUDIO:
        print("WARNING: narration longer than target; consider trimming middle beats")

    pieces = [np.zeros(int(LEAD_IN * SR), np.float32)]
    t = LEAD_IN
    timeline = []
    nwords = 0
    for sid, text, beats, light in order:
        p = os.path.join(TTS, f"{sid}.wav")
        a, _ = read_wav(p)
        d = len(a) / SR
        toks = tokens(text)
        cache = p + ".words.json"
        if os.path.exists(cache) and json.load(open(cache)).get("key") == text + KEY:
            ww = json.load(open(cache))["words"]
        else:
            ww = whisper_words(p)
            json.dump({"key": text + KEY, "words": ww}, open(cache, "w"))
        st, en = align(toks, ww, d)
        for tk, s0, e0 in zip(toks, st, en):
            tk["start"], tk["end"] = round(t + s0, 3), round(t + e0, 3)
        nwords += len(toks)
        timeline.append(dict(id=sid, text=text, start=round(t, 3), speech_end=round(t + d, 3),
                             end=round(t + d + SENT_GAP, 3), light=light, beats=beats, words=toks))
        pieces += [a, np.zeros(int(SENT_GAP * SR), np.float32)]
        t += d + SENT_GAP
    voice = np.concatenate(pieces)
    voice = voice / max(1e-6, np.abs(voice).max()) * 0.89
    write_wav(os.path.join(B, "voice.wav"), voice)
    wps = nwords / t
    json.dump(dict(duration=round(t, 3), n_extra=n_extra, words=nwords, wps=round(wps, 3), sentences=timeline),
              open(os.path.join(B, "timeline.json"), "w"), indent=1)
    with open(os.path.join(HERE, "script.txt"), "w") as f:
        f.write('THE MAILMAN SKIPS OUR HOUSE\n(narrator: Eli; CAPS = red caption words)\n\n')
        for i, s in enumerate(timeline, 1):
            f.write(f"{i}. {s['text']}\n")
        f.write("(hard cut to black)\n")
    print(f"narration {t:.2f}s, {nwords} words, {wps:.2f} words/sec, {len(timeline)} sentences")
    if not 3.6 <= wps <= 4.2:
        print("WARNING: words/sec outside 3.6-4.2 -> adjust MM_LENGTH_SCALE")


if __name__ == "__main__":
    main()
