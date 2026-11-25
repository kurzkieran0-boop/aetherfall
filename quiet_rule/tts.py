"""Generate narration with Piper (free, offline) + word timestamps via faster-whisper.

Outputs:
  build/voice.wav        full narration timeline (mono 22.05k -> 48k)
  build/timeline.json    sentences with start/end and per-word timings
  script.txt             the final spoken script
"""
import json, os, re, subprocess, difflib, wave
import numpy as np
from story import build_script, S, EXTRA, MIN_AUDIO

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build")
TTS_DIR = os.path.join(B, "tts")
os.makedirs(TTS_DIR, exist_ok=True)
VOICE = os.path.join(HERE, "voices", "en_US-joe-medium.onnx")
LENGTH_SCALE = os.environ.get("QR_LENGTH_SCALE", "1.08")
SR = 48000
LEAD_IN = 0.15


def spoken(text):
    t = re.sub(r"\b([A-Z]{2,})\b", lambda m: m.group(1).lower(), text)
    t = t.replace("...", ",").replace("“", '"').replace("”", '"')
    return t


def synth(sid, text):
    out = os.path.join(TTS_DIR, f"{sid}.wav")
    key = os.path.join(TTS_DIR, f"{sid}.txt")
    if os.path.exists(out) and os.path.exists(key) and open(key).read() == text + LENGTH_SCALE:
        return out
    raw = os.path.join(TTS_DIR, f"{sid}_raw.wav")
    subprocess.run(["python3", "-m", "piper", "-m", VOICE, "--length-scale", LENGTH_SCALE,
                    "--noise-scale", "0.5", "--noise-w-scale", "0.6", "-f", raw],
                   input=spoken(text).encode(), check=True, capture_output=True)
    # slight pitch lift for a younger narrator, trim silence at both ends, resample to 48k
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af",
                    "rubberband=pitch=1.05,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "aresample=48000", "-ac", "1", out], check=True)
    open(key, "w").write(text + LENGTH_SCALE)
    return out


def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a


def tokens(text):
    out = []
    for raw in text.split():
        disp = raw.replace("“", "").replace("”", "").replace('"', "")
        disp = disp.strip(".,!;:")
        if not disp:
            continue
        letters = re.sub(r"[^A-Za-z]", "", disp)
        red = len(letters) > 1 and letters.isupper()
        norm = re.sub(r"[^a-z0-9]", "", disp.lower())
        out.append(dict(text=disp.upper(), red=red, norm=norm))
    return out


_model = None


def whisper_words(path):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, dtype=np.float32).copy()
    segs, _ = _model.transcribe(audio, word_timestamps=True, language="en", beam_size=5)
    words = []
    for s in segs:
        for w in s.words:
            n = re.sub(r"[^a-z0-9]", "", w.word.lower())
            if n:
                words.append((n, w.start, w.end))
    return words


def align(toks, words, dur):
    """Give each script token a (start,end) using whisper words; interpolate the rest."""
    a = [t["norm"] for t in toks]
    b = [w[0] for w in words]
    st = [None] * len(toks)
    en = [None] * len(toks)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            st[blk.a + k] = words[blk.b + k][1]
            en[blk.a + k] = words[blk.b + k][2]
    # anchors at both ends
    known = [i for i in range(len(toks)) if st[i] is not None]
    pts = [(-1, 0.0)] + [(i, st[i]) for i in known] + [(len(toks), dur)]
    for (i0, t0), (i1, t1) in zip(pts, pts[1:]):
        gap = list(range(i0 + 1, i1))
        if not gap:
            continue
        t_start = en[i0] if i0 >= 0 and en[i0] is not None else t0
        span = max(0.05, t1 - t_start)
        weights = [max(1, len(toks[g]["norm"])) for g in gap]
        tot = sum(weights)
        cur = t_start
        for g, w in zip(gap, weights):
            st[g] = cur
            cur += span * w / tot
            en[g] = cur
    for i in range(len(toks)):
        st[i] = max(0.0, min(st[i], dur))
        en[i] = max(st[i] + 0.05, min(en[i], dur))
    # enforce monotonic
    for i in range(1, len(toks)):
        if st[i] < st[i - 1] + 0.04:
            st[i] = st[i - 1] + 0.04
    return st, en


def main():
    all_sent = list(S) + [e[1] for e in EXTRA]
    durs = {}
    for sid, text, beats, light, pause in all_sent:
        p = synth(sid, text)
        durs[sid] = len(read_wav(p)) / SR

    def total(n):
        return LEAD_IN + sum(durs[s[0]] + s[4] for s in build_script(n))

    n_extra = 0
    while total(n_extra) < MIN_AUDIO and n_extra < len(EXTRA):
        n_extra += 1
    order = build_script(n_extra)
    print(f"base voice timeline {total(0):.1f}s -> using {n_extra} extra beats -> {total(n_extra):.1f}s")

    pieces = [np.zeros(int(LEAD_IN * SR), np.float32)]
    t = LEAD_IN
    timeline = []
    for sid, text, beats, light, pause in order:
        p = os.path.join(TTS_DIR, f"{sid}.wav")
        a = read_wav(p)
        d = len(a) / SR
        toks = tokens(text)
        cache = p + ".words.json"
        if os.path.exists(cache) and json.load(open(cache)).get("text") == text:
            ww = json.load(open(cache))["words"]
        else:
            ww = whisper_words(p)
            json.dump({"text": text, "words": ww}, open(cache, "w"))
        st, en = align(toks, ww, d)
        for tk, s0, e0 in zip(toks, st, en):
            tk["start"] = round(t + s0, 3)
            tk["end"] = round(t + e0, 3)
        timeline.append(dict(id=sid, text=text, start=round(t, 3), speech_end=round(t + d, 3),
                             end=round(t + d + pause, 3), light=light, beats=beats, words=toks))
        pieces.append(a)
        pieces.append(np.zeros(int(pause * SR), np.float32))
        t += d + pause
    voice = np.concatenate(pieces)
    voice = voice / max(1e-6, np.abs(voice).max()) * 0.89
    with wave.open(os.path.join(B, "voice.wav"), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((voice * 32767).astype(np.int16).tobytes())
    json.dump(dict(duration=round(t, 3), n_extra=n_extra, sentences=timeline),
              open(os.path.join(B, "timeline.json"), "w"), indent=1)
    with open(os.path.join(HERE, "script.txt"), "w") as f:
        f.write('THE QUIET RULE\n(narrator: Eli; CAPS = red caption words)\n\n')
        for i, s in enumerate(timeline, 1):
            f.write(f"{i}. {s['text']}\n")
        f.write("(hard cut to black)\n")
    print(f"voice timeline: {t:.2f}s, sentences: {len(timeline)}")


if __name__ == "__main__":
    main()
