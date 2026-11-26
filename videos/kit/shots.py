"""Shot planner: fit each sentence's beats to the narration (cut every ~1-2 s, never > HARD_MAX),
compile counter keyframes and SFX times -> videos/<slug>/shots.json

python3 kit/shots.py <slug>
"""
import json, math, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import video, bdir, vdir, args
import progress

FPS = 30
VARIANT = {"ecu": "cu", "cu": "ecu", "push": "orbit", "orbit": "push", "wide": "push", "low": "high",
           "high": "low", "ots": "cu", "whip": "cu", "drone": "high", "track": "low", "tilt": "cu",
           "dutch": "ecu", "pull": "push", "prop": "push", "sky": "cu", "chase": "track", "pan": "ecu_wall",
           "orbit_room": "pan", "tilt_wall": "ecu_wall", "ecu_wall": "pan", "shelf_pan": "ecu_wall", "ecu_hook": "prop",
           "hands": "cu", "counter": "mcu", "mcu": "counter"}


def main(slug):
    cfg, story, scene = video(slug)
    target = getattr(cfg, "SHOT_TARGET", 1.4)
    hard_max = getattr(cfg, "SHOT_MAX", 3.0) - 0.15
    min_len = getattr(cfg, "SHOT_MIN", 0.6)
    end_black = getattr(cfg, "END_BLACK", 0.8)
    tl = json.loads((bdir(slug) / "timeline.json").read_text())
    sents = tl["sentences"]
    shots = []
    for i, s in enumerate(sents):
        seg0 = 0.0 if i == 0 else s["start"]
        seg1 = sents[i + 1]["start"] if i + 1 < len(sents) else tl["duration"]
        D = seg1 - seg0
        beats = [dict(b) for b in s["beats"]]
        n = max(len(beats), math.ceil(D / target), math.ceil(D / hard_max))
        while n > 1 and D / n < min_len and n > math.ceil(D / hard_max):
            n -= 1
        while len(beats) > n:
            idx = max(j for j, b in enumerate(beats) if "card" not in b or j == len(beats) - 1)
            beats.pop(idx)
        k = 0
        while len(beats) < n:
            scene_idx = [jj for jj, b in enumerate(beats) if "card" not in b] or [0]
            j = scene_idx[k % len(scene_idx)]
            v = dict(beats[j])
            if "cam" in v:
                v["cam"] = VARIANT.get(v["cam"], "cu")
            beats.insert(j + 1, v)
            k += 2
        cands = [w["start"] - 0.04 for w in s["words"] if seg0 + min_len < w["start"] - 0.04 < seg1 - min_len]
        cuts = [seg0]
        for m in range(1, n):
            ideal = seg0 + D * m / n
            best = min(cands, key=lambda c: abs(c - ideal)) if cands else ideal
            c = best if abs(best - ideal) < 0.35 else ideal
            cuts.append(max(c, cuts[-1] + min_len))
        cuts.append(seg1)
        for m, b in enumerate(beats):
            bb = dict(b)
            bb.setdefault("light", s["light"])
            shots.append(dict(sentence=s["id"], t0=cuts[m], t1=cuts[m + 1], **bb))
    out = []
    for k, sh in enumerate(shots):
        f0, f1 = round(sh["t0"] * FPS), round(sh["t1"] * FPS)
        sh.update(id=f"shot_{k + 1:03d}", frame0=f0, frames=f1 - f0, dur=round((f1 - f0) / FPS, 3), seed=k * 7919 % 1000)
        sh["kind"] = "card" if "card" in sh else ("blind" if sh.get("blind") else "render")
        sh["paper"] = bool(sh.get("paper") or sh["kind"] == "card")
        sh["caption_words"] = [w["text"] for ss in sents for w in ss["words"] if sh["t0"] <= w["start"] < sh["t1"]]
        sh["location"] = sh.get("set", "card")
        sh["camera_move"] = sh.get("cam", "zoom")
        sh["characters"] = sorted(set(list(sh.get("acts", {})) + list(sh.get("faces", {})) +
                                      ([sh["tgt"]] if str(sh.get("tgt", "")).isidentifier() and sh.get("tgt") in scene.CAST else [])))
        sh["emotion"] = ",".join(f"{a}:{b}" for a, b in sh.get("faces", {}).items()) or "neutral"
        del sh["t0"], sh["t1"]
        out.append(sh)
    total_frames = round(tl["duration"] * FPS)
    out.append(dict(id=f"shot_{len(out) + 1:03d}", kind="black", frame0=total_frames, frames=round(end_black * FPS),
                    dur=end_black, sentence="end", caption_words=[]))

    # ---- counters: initial values + per-sentence keys (word-anchored)
    counters = {}
    if getattr(cfg, "COUNTER", None):
        for n, c in scene.CAST.items():
            if c.get("start") is not None:
                counters[n] = [(0.0, c["start"], "step")]
        by_id = {s["id"]: s for s in sents}
        for sid, specs in getattr(story, "COUNTERS", {}).items():
            if sid not in by_id:
                continue
            s = by_id[sid]
            words = s["words"]
            for n, spec in specs.items():
                keys = counters.setdefault(n, [])
                if isinstance(spec, (int, float)):
                    keys.append((s["start"], int(spec), "step"))
                    continue
                pos = 0
                for item in spec:
                    match, value = item[0], item[1]
                    mode = item[2] if len(item) > 2 else "ramp"
                    if isinstance(match, int):
                        w = words[min(match, len(words) - 1)]
                    elif match == "start":
                        w = dict(start=s["start"])
                    elif match == "end":
                        w = dict(start=s["speech_end"])
                    else:
                        hits = [j for j in range(pos, len(words)) if words[j]["norm"] == match.lower()]
                        if not hits:
                            raise SystemExit(f"{slug}: counter word '{match}' not found in {sid}")
                        pos = hits[0] + 1
                        w = words[hits[0]]
                    keys.append((round(w["start"], 3), int(value), mode))
        for n in counters:
            counters[n].sort(key=lambda k: k[0])

    # ---- sfx times
    sfx = {"heartbeat": [], "stone": []}
    by_id = {s["id"]: s for s in sents}
    for sid in getattr(story, "SFX", {}).get("heartbeat", []):
        if sid in by_id:
            sfx["heartbeat"].append((by_id[sid]["start"], by_id[sid]["end"]))
    for sid, word in getattr(story, "SFX", {}).get("stone", []):
        if sid in by_id:
            ws = [w for w in by_id[sid]["words"] if w["norm"] == word.lower()]
            if ws:
                sfx["stone"].append(ws[0]["start"])
    (vdir(slug) / "shots.json").write_text(json.dumps(dict(fps=FPS, shots=out, counters=counters, sfx=sfx), indent=1))
    content = [s for s in out if s["kind"] not in ("black", "blind")]
    durs = [s["dur"] for s in content]
    need = getattr(cfg, "MIN_SHOTS", 80)
    ok = len(content) >= need and max(durs) <= getattr(cfg, "SHOT_MAX", 3.0)
    progress.mark(slug, "shots", ok=ok, shots=len(content), cards=sum(s["kind"] == "card" for s in content),
                  max_shot=max(durs), render_frames=sum(s["frames"] for s in content if s["kind"] == "render"))
    print(f"[{slug}] {len(content)} shots ({sum(s['kind'] == 'card' for s in content)} cards), max {max(durs):.2f}s, "
          f"min {min(durs):.2f}s, {sum(s['frames'] for s in content if s['kind'] == 'render')} render frames")


if __name__ == "__main__":
    main(args()[0])
