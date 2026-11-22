"""Word-by-word captions: faster-whisper word timestamps, aligned to the script text
(so spelling is always the script's), grouped 1–2 words, rendered as big bold yellow
type with a thick black outline and a pop-in, placed in the lower-middle of frame
but moved off any face / monster head (screen boxes come from the Blender worker)."""
import difflib
import os
import re
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
SYSTEM_FONTS = ["/usr/share/fonts/opentype/inter/Inter-Black.otf",
                "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/impact.ttf",
                "/System/Library/Fonts/Supplemental/Arial Black.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

_MODEL = None


def font_path():
    os.makedirs(FONT_DIR, exist_ok=True)
    local = os.path.join(FONT_DIR, "Inter-Black.otf")
    if os.path.exists(local):
        return local
    for p in SYSTEM_FONTS:
        if os.path.exists(p):
            if "Inter-Black" in p:
                shutil.copy(p, local)
                return local
            return p
    return None


def _load_audio16k(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def whisper_words(wav_path, model="base.en"):
    global _MODEL
    from faster_whisper import WhisperModel
    if _MODEL is None:
        _MODEL = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = _MODEL.transcribe(_load_audio16k(wav_path), word_timestamps=True, vad_filter=False,
                                condition_on_previous_text=False)
    return [(w.word.strip(), float(w.start), float(w.end)) for s in segs for w in s.words]


def _norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align(script_text, wwords, dur):
    """Map script words onto whisper timings (difflib on normalised tokens);
    unmatched script words are interpolated between neighbours."""
    toks = script_text.split()
    a = [_norm(t) for t in toks]
    b = [_norm(w[0]) for w in wwords]
    times = [None] * len(toks)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (wwords[blk.b + k][1], wwords[blk.b + k][2])
    # number words etc: fill gaps by interpolation
    known = [i for i, t in enumerate(times) if t]
    if not known:
        step = dur / max(1, len(toks))
        return [(t, i * step, (i + 1) * step) for i, t in enumerate(toks)]
    for i in range(len(toks)):
        if times[i] is None:
            lo = max([k for k in known if k < i], default=None)
            hi = min([k for k in known if k > i], default=None)
            t0 = times[lo][1] if lo is not None else 0.0
            t1 = times[hi][0] if hi is not None else dur
            nl = (i - (lo if lo is not None else -1))
            span = (hi if hi is not None else len(toks)) - (lo if lo is not None else -1)
            s = t0 + (t1 - t0) * (nl - 1) / span
            e = t0 + (t1 - t0) * nl / span
            times[i] = (s, e)
    return [(toks[i], times[i][0], times[i][1]) for i in range(len(toks))]


def group_words(words, max_chars=13):
    """1–2 words per caption: pair short words, keep long words solo, never join across
    sentence punctuation."""
    out = []
    i = 0
    while i < len(words):
        w, s, e = words[i]
        if i + 1 < len(words) and not re.search(r"[.!?,—:]$", w):
            w2, s2, e2 = words[i + 1]
            if len(w) + len(w2) + 1 <= max_chars and (len(w) <= 4 or len(w2) <= 4):
                out.append((f"{w} {w2}", s, e2))
                i += 2
                continue
        out.append((w, s, e))
        i += 1
    # extend each caption to the next one's start (no flicker), cap hold at 0.9 s
    res = []
    for k, (w, s, e) in enumerate(out):
        nxt = out[k + 1][1] if k + 1 < len(out) else e + 0.4
        res.append((w, s, max(e, min(nxt, s + 0.9))))
    return res


class CaptionRenderer:
    def __init__(self, W=1080, H=1920, size=118, color=(255, 222, 26), stroke=12):
        fp = font_path()
        self.font = ImageFont.truetype(fp, size) if fp else ImageFont.load_default()
        self.W, self.H, self.size, self.color, self.stroke = W, H, size, color, stroke
        self._cache = {}

    def _sprite(self, text):
        if text in self._cache:
            return self._cache[text]
        txt = text.upper()
        font = self.font
        # shrink if too wide
        size = self.size
        while True:
            bbox = font.getbbox(txt, stroke_width=self.stroke)
            if bbox[2] - bbox[0] <= self.W * 0.9 or size < 50:
                break
            size -= 8
            font = ImageFont.truetype(font.path, size)
        w, h = bbox[2] - bbox[0] + 30, bbox[3] - bbox[1] + 30
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # drop shadow
        d.text((15 - bbox[0] + 6, 15 - bbox[1] + 8), txt, font=font, fill=(0, 0, 0, 150),
               stroke_width=self.stroke, stroke_fill=(0, 0, 0, 150))
        d.text((15 - bbox[0], 15 - bbox[1]), txt, font=font, fill=self.color + (255,),
               stroke_width=self.stroke, stroke_fill=(0, 0, 0, 255))
        self._cache[text] = im
        return im

    @staticmethod
    def pop_scale(age_s):
        # anticipation-free pop: 0.55 -> 1.12 overshoot -> 1.0 in ~0.2 s
        if age_s < 0.07:
            return 0.55 + (1.12 - 0.55) * age_s / 0.07
        if age_s < 0.2:
            return 1.12 - 0.12 * (age_s - 0.07) / 0.13
        return 1.0

    def place_y(self, boxes, cap_h):
        """Choose caption centre y (pixels, top-down). boxes: normalised, y bottom-up."""
        cands = [0.70, 0.78, 0.62, 0.86, 0.54, 0.40, 0.30]
        hard = [b["box"] for b in boxes if b["tag"] in ("face", "monster_head")]
        soft = [b["box"] for b in boxes if b["tag"] == "monster"]

        def hits(yc, bx):
            top = 1 - (yc - cap_h / 2 / self.H)
            bot = 1 - (yc + cap_h / 2 / self.H)
            x0, x1 = 0.08, 0.92
            return not (bx[2] < x0 or bx[0] > x1 or bx[3] < bot or bx[1] > top)

        for yc in cands:
            if not any(hits(yc, b) for b in hard):
                return int(yc * self.H)
        return int(0.86 * self.H)

    def overlay(self, frame_rgb, text, age_s, y_center):
        sp = self._sprite(text)
        s = self.pop_scale(age_s)
        if abs(s - 1.0) > 1e-3:
            sp = sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.BILINEAR)
        x = (self.W - sp.width) // 2
        y = y_center - sp.height // 2
        base = Image.fromarray(frame_rgb)
        base.paste(sp, (x, y), sp)
        return np.asarray(base)
