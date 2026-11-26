"""Fit visual beats to the narration timeline -> shots.json (cut every ~1-2s, never >3s)."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
TARGET = 1.25   # preferred max shot length (s): a cut every ~1-1.5 s
HARD_MAX = 2.5
MIN_LEN = 0.55
END_BLACK = 0.8

VARIANT = {"ecu": "cu", "cu": "ecu", "push": "orbit", "orbit": "push", "wide": "push", "low": "high",
           "high": "low", "ots": "cu", "whip": "cu", "drone": "high", "track": "low", "tilt": "cu",
           "dutch": "ecu", "pull": "push", "prop": "push", "sky": "cu", "chase": "track", "pan": "ecu_wall",
           "orbit_room": "pan", "tilt_wall": "ecu_wall", "ecu_wall": "pan", "shelf_pan": "ecu_wall", "ecu_hook": "prop",
           "hands": "cu"}


def main():
    tl = json.load(open(os.path.join(HERE, "build", "timeline.json")))
    sents = tl["sentences"]
    shots = []
    for i, s in enumerate(sents):
        seg0 = 0.0 if i == 0 else s["start"]
        seg1 = sents[i + 1]["start"] if i + 1 < len(sents) else tl["duration"]
        D = seg1 - seg0
        beats = [dict(b) for b in s["beats"]]
        n = max(len(beats), math.ceil(D / TARGET))
        while n > 1 and D / n < MIN_LEN:
            n -= 1
        # too many beats for the segment: drop from the end (keep cards)
        while len(beats) > n:
            idx = max(i for i, b in enumerate(beats) if "card" not in b or i == len(beats) - 1)
            beats.pop(idx)
        # too few: interleave camera variants of scene beats
        k = 0
        scene_idx = [j for j, b in enumerate(beats) if "card" not in b]
        while len(beats) < n:
            j = scene_idx[k % len(scene_idx)]
            v = dict(beats[j]); v["cam"] = VARIANT.get(v["cam"], "cu")
            pos = beats.index(beats[j]) + 1
            beats.insert(pos, v)
            scene_idx = [jj for jj, b in enumerate(beats) if "card" not in b]
            k += 2
        # cut times: equal split snapped to word starts
        cands = [w["start"] - 0.04 for w in s["words"] if seg0 + MIN_LEN < w["start"] - 0.04 < seg1 - MIN_LEN]
        cuts = [seg0]
        for m in range(1, n):
            ideal = seg0 + D * m / n
            best = min(cands, key=lambda c: abs(c - ideal)) if cands else ideal
            c = best if abs(best - ideal) < 0.35 else ideal
            c = max(c, cuts[-1] + MIN_LEN)
            cuts.append(c)
        cuts.append(seg1)
        for m, b in enumerate(beats):
            a, e = cuts[m], cuts[m + 1]
            bb = dict(b); bb.setdefault("light", s["light"])
            shots.append(dict(sentence=s["id"], t0=a, t1=e, **bb))
    # frame quantisation on the global timeline
    out = []
    for k, sh in enumerate(shots):
        f0 = round(sh["t0"] * FPS)
        f1 = round(sh["t1"] * FPS)
        sh["id"] = f"shot_{k + 1:03d}"
        sh["frame0"] = f0
        sh["frames"] = f1 - f0
        sh["dur"] = round((f1 - f0) / FPS, 3)
        sh["seed"] = k * 7919 % 1000
        sh["kind"] = "card" if "card" in sh else "render"
        sh["paper"] = bool(sh.get("paper") or sh["kind"] == "card")
        if "light" in sh and sh["kind"] == "render":
            pass
        words = [w["text"] for ss in sents for w in ss["words"] if sh["t0"] <= w["start"] < sh["t1"]]
        sh["caption_words"] = words
        sh["location"] = sh.get("set", "card")
        sh["camera_move"] = sh.get("cam", "zoom")
        sh["characters"] = sorted(set(list(sh.get("acts", {}).keys()) + list(sh.get("faces", {}).keys()) +
                                      ([sh["tgt"]] if sh.get("tgt", "").isalnum() else [])))
        sh["emotion"] = ",".join(f"{k2}:{v}" for k2, v in sh.get("faces", {}).items()) or "neutral"
        del sh["t0"], sh["t1"]
        out.append(sh)
    total_frames = round(tl["duration"] * FPS)
    out.append(dict(id=f"shot_{len(out) + 1:03d}", kind="black", frame0=total_frames,
                    frames=round(END_BLACK * FPS), dur=END_BLACK, sentence="end", caption_words=[]))
    json.dump(dict(fps=FPS, shots=out), open(os.path.join(HERE, "shots.json"), "w"), indent=1)
    durs = [s["dur"] for s in out]
    print(f"{len(out)} shots ({sum(1 for s in out if s['kind']=='card')} cards), "
          f"max {max(durs):.2f}s, min {min(durs):.2f}s, total {sum(durs):.2f}s")


if __name__ == "__main__":
    main()
