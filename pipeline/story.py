"""Story engine.

Pipeline per film:  brainstorm 10 premises -> score (hook, rule clarity, clever use,
reversal, originality, idea fit) -> pick best -> outline (beat sheet with timing
targets) -> draft -> automated critique -> rewrite -> timeline -> shotlist.json.

Sources of a story, in order:
  1. a hand-authored bank film (stories/<slug>.py) whose premise matches the idea or
     that hasn't been used yet ("surprise me");
  2. a local LLM via Ollama if one is installed (free, offline) — it writes the beat
     lines, everything else (scoring, critique, shots) stays rule-based here;
  3. the built-in template writer (rule archetypes x settings x heroes).
"""
import importlib.util
import json
import math
import os
import random
import re
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "stories")
FPS = 24

# ------------------------------------------------------------------------ DSL helpers


def cam(subject="hero", framing="ms", move="push_in", angle="eye", lens=35, az=20, **kw):
    d = dict(subject=subject, framing=framing, move=move, angle=angle, lens=lens, az=az)
    d.update(kw)
    return d


def A(who, action, **kw):
    d = {"who": who, "action": action}
    d.update(kw)
    return d


def shot(c, *acts, w=1.0, **kw):
    d = {"camera": c, "actions": list(acts), "w": w}
    d.update(kw)
    return d


def beat(say=None, *shots, pad=0.25, tension=None, kind=None, sfx=(), hold=0.0, label=None, **kw):
    """say = (speaker, text) or None (silent beat lasting `hold` seconds).
    extra kw: voice_fx = whisper | radio | echo."""
    d = {"say": say, "shots": list(shots), "pad": pad, "tension": tension, "kind": kind,
         "sfx": list(sfx), "hold": hold, "label": label}
    d.update(kw)
    return d


# ------------------------------------------------------------------ rule archetypes

RULES = [
    dict(id="dark", rule="It can only move in the dark.", monster="colossus", glow=(0.3, 0.85, 1.0),
         use="keep light on it from every side so it has no shadow to move in",
         reversal="its own shadow counts as dark", hook="At 11:52 the city went dark — and something took a step.",
         win="a single flashlight in its eye at the last second", look="night_blue"),
    dict(id="voice", rule="It hunts whoever speaks.", monster="stalker", glow=(1.0, 0.15, 0.6),
         use="throw your voice through radios so it chases decoys", reversal="the radios die and someone talks",
         hook="It has no eyes. It doesn't need them.", win="lead it into a tunnel where echoes come from everywhere",
         look="storm"),
    dict(id="water", rule="It can't cross water.", monster="warden", glow=(1.0, 0.35, 0.05),
         use="flood the streets so it is trapped", reversal="it builds a bridge out of buildings",
         hook="Everyone in the city ran for the canal.", win="jump into the one place it can't follow", look="ember"),
    dict(id="watched", rule="It freezes when anyone is looking at it.", monster="warden", glow=(0.7, 1.0, 0.3),
         use="take turns watching it so it never moves", reversal="the power cut means nobody can see it",
         hook="Don't blink. It moves when you blink.", win="a whole city of phone cameras on a livestream", look="toxic"),
    dict(id="count", rule="It takes one step every time a clock strikes.", monster="colossus", glow=(1.0, 0.8, 0.2),
         use="stop every clock in the city", reversal="phones chime the hour too", hook="Eleven steps left. Then it reaches us.",
         win="set every clock back an hour so it walks backwards", look="ember"),
    dict(id="mirror", rule="It copies whatever the nearest person does.", monster="colossus", glow=(0.5, 0.5, 1.0),
         use="make it copy you walking into the river", reversal="two people move at once", hook="Whatever you do, it does too.",
         win="lie down — and it lies down on its own fault line", look="night_blue"),
    dict(id="heat", rule="It can only see heat.", monster="stalker", glow=(1.0, 0.25, 0.1),
         use="hide in the cold — freezers, rain, the river", reversal="the rain stops", hook="It can't see you. It can see your heartbeat.",
         win="lure it into the cooling tower's steam", look="ember"),
    dict(id="sleep", rule="It only hunts while the city is awake.", monster="colossus", glow=(0.8, 0.3, 1.0),
         use="get the whole city to turn everything off", reversal="one alarm goes off", hook="Lights out. Phones down. Or it wakes up.",
         win="a lullaby over every speaker", look="night_blue"),
    dict(id="name", rule="It comes to whoever says its name.", monster="warden", glow=(0.3, 1.0, 0.8),
         use="say it from a moving train to drag it away", reversal="the news anchor says it on live TV",
         hook="Whatever you do — don't say its name.", win="write it instead of saying it", look="toxic"),
    dict(id="line", rule="It can't cross a painted line.", monster="colossus", glow=(1.0, 0.9, 0.3),
         use="paint lines across every street", reversal="the rain washes the paint away",
         hook="A can of road paint is the only weapon left.", win="paint a circle around it while it sleeps", look="night_blue"),
]
HEROES = [("Mia", "girl", "scared of the dark"), ("Theo", "boy", "never stops talking"), ("Nora", "girl_uk", "never leaves anything behind"),
          ("Sam", "boy", "always runs away"), ("Ivy", "girl", "doesn't trust anyone"), ("Kai", "boy", "always late")]
SETTINGS = ["city_block", "plaza", "rooftop", "subway", "school", "forest", "lab", "bunker"]


def _used_rules():
    out_dir = os.path.join(ROOT, "output")
    used = set()
    if os.path.isdir(out_dir):
        for d in os.listdir(out_dir):
            p = os.path.join(out_dir, d, "film.json")
            if os.path.exists(p):
                try:
                    used.add(json.load(open(p)).get("rule_id"))
                except Exception:
                    pass
    return used


def score_premise(p, idea=""):
    """0-10 scores. Hook: short + concrete threat; clarity: rule fits in ~8 words;
    clever: a non-violent counter exists; reversal present; originality vs. past films."""
    words = len(p["rule"].split())
    clarity = max(0, 10 - max(0, words - 7) * 1.5)
    hook = 6 + (2 if len(p["hook"].split()) <= 10 else 0) + (1 if "?" not in p["hook"] else 0) + (1 if p["setting"] in ("city_block", "plaza") else 0)
    clever = 7 + (2 if any(k in p["use"] for k in ("radio", "light", "flood", "echo", "clock", "phone", "paint")) else 0)
    reversal = 8 if p.get("reversal") else 3
    original = 9 - (5 if p["rule_id"] in _used_rules() else 0)
    fit = 5
    if idea and idea.lower() not in ("surprise me", "surprise"):
        toks = set(re.findall(r"[a-z]+", idea.lower()))
        blob = " ".join([p["rule"], p["use"], p["hook"], p["setting"], p["reversal"]]).lower()
        fit = min(10, 3 + 2 * sum(1 for t in toks if len(t) > 3 and t in blob))
    s = dict(hook=hook, clarity=round(clarity, 1), clever_use=clever, reversal=reversal, originality=original, idea_fit=fit)
    s["total"] = round(hook * 1.5 + clarity * 1.2 + clever * 1.2 + reversal + original + fit * 1.5, 1)
    return s


def brainstorm(idea="surprise me", n=10, seed=None):
    rng = random.Random(seed if seed is not None else hash(idea) & 0xffff)
    out = []
    rules = RULES[:]
    rng.shuffle(rules)
    for i in range(n):
        r = rules[i % len(rules)]
        hero = rng.choice(HEROES)
        setting = rng.choice(SETTINGS[:4] if i % 3 else SETTINGS)
        p = dict(rule_id=r["id"], rule=r["rule"], hook=r["hook"], use=r["use"], reversal=r["reversal"], win=r["win"],
                 hero=hero[0], voice=hero[1], flaw=hero[2], setting=setting,
                 premise=f"{hero[0]}, a kid who {hero[2]}, faces a giant that obeys one rule — {r['rule'].lower()} "
                         f"— in a {setting.replace('_', ' ')} at night, and must {r['use']}.")
        p["scores"] = score_premise(p, idea)
        out.append(p)
    out.sort(key=lambda p: -p["scores"]["total"])
    return out


# --------------------------------------------------------------------- bank stories

def bank_films():
    films = []
    if not os.path.isdir(BANK):
        return films
    for f in sorted(os.listdir(BANK)):
        if f.endswith(".py") and not f.startswith("_"):
            spec = importlib.util.spec_from_file_location(f[:-3], os.path.join(BANK, f))
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            films.append(m.FILM)
    return films


def pick_bank(idea):
    films = bank_films()
    if not films:
        return None
    if idea and idea.lower() not in ("surprise me", "surprise"):
        toks = [t for t in re.findall(r"[a-z]+", idea.lower()) if len(t) > 2]
        best, bs = None, 0
        for f in films:
            blob = " ".join([f["slug"], f["title"], f["rule"], f.get("logline", "")]).lower()
            sc = sum(1 for t in toks if t in blob)
            if sc > bs:
                best, bs = f, sc
        return best if bs >= 1 else None
    used = set(os.listdir(os.path.join(ROOT, "output"))) if os.path.isdir(os.path.join(ROOT, "output")) else set()
    for f in films:
        if f["slug"] not in used:
            return f
    return None


# ----------------------------------------------------------------- Ollama (optional)

def ollama_available():
    return shutil.which("ollama") is not None


def llm_lines(premise, model="llama3.1"):
    prompt = (
        "Write narration and dialogue for a 75-second vertical monster short. Return JSON list of beats, each "
        '{"type": one of hook,rule,hero,escalate,clever,reversal,climax,win,ending, "speaker": "narrator" or "hero" or '
        '"ally", "text": max 12 words}. 16-22 beats. Hook in first line. State the rule by beat 3. Twist or clever win. '
        "Complete ending, no cliffhanger. Short punchy natural lines.\nPremise: " + premise["premise"] +
        "\nRule: " + premise["rule"] + "\nClever use: " + premise["use"] + "\nReversal: " + premise["reversal"] +
        "\nWin: " + premise["win"])
    try:
        p = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=600)
        txt = p.stdout
        js = json.loads(txt[txt.index("["):txt.rindex("]") + 1])
        return [(b["type"], b["speaker"], b["text"]) for b in js]
    except Exception:
        return None


# --------------------------------------------------------- template writer + shots

OUTLINE = [("hook", "0-2s", "hook line + giant reveal"), ("rule", "2-10s", "rule stated and shown"),
           ("hero", "10-18s", "hero, want and flaw"), ("escalate", "18-30s", "threat escalates"),
           ("clever", "30-45s", "hero uses the rule"), ("reversal", "45-58s", "rule tested / broken"),
           ("climax", "58-70s", "all-is-lost + last idea"), ("win", "70-80s", "clever win / twist"),
           ("ending", "80-90s", "complete resolution + button")]


def template_lines(p):
    H = p["hero"]
    return [
        ("hook", "narrator", p["hook"]),
        ("rule", "narrator", f"One rule kept us alive. {p['rule']}"),
        ("rule", "narrator", "Break it, and it comes for you."),
        ("hero", "narrator", f"{H} had one problem. {H} {p['flaw']}."),
        ("hero", "hero", "Okay. Okay. Think."),
        ("escalate", "narrator", "Then it got closer. Much closer."),
        ("escalate", "ally", "We can't stop it!"),
        ("clever", "hero", "We don't have to stop it. We use the rule."),
        ("clever", "narrator", f"So {H} decided to {p['use']}."),
        ("clever", "narrator", "And for a moment — it worked."),
        ("reversal", "narrator", f"Until it learned something new: {p['reversal']}."),
        ("reversal", "ally", f"{H}! Behind you!"),
        ("climax", "narrator", f"Everything {H} feared was standing right there."),
        ("climax", "hero", "Then let's finish it."),
        ("win", "narrator", f"So {H} tried one last thing: {p['win']}."),
        ("win", "narrator", "And the giant never moved again."),
        ("ending", "narrator", "By morning, the city was quiet."),
        ("ending", "narrator", f"And {H} wasn't afraid anymore."),
    ]


SHOT_GRAMMAR = {
    # beat type -> list of shot templates (camera + hero/monster action)
    "hook": [shot(cam("mark:street_n", "ews", "crane_up", "high", 24, 180), A("monster", "walk", path=["monster", "street_n"])),
             shot(cam("monster", "ws", "tilt_up", "worm", 24, 0), A("monster", "roar"))],
    "rule": [shot(cam("monster", "ms", "push_in", "low", 35, 10), A("monster", "freeze")),
             shot(cam("hero", "mcu", "push_in", "eye", 85, 15), A("hero", "look_up", look_at="monster"))],
    "hero": [shot(cam("hero", "ms", "orbit_right", "eye", 35, 25), A("hero", "idle")),
             shot(cam("hero", "cu", "push_in", "eye", 85, -10), A("hero", "idle", expr="determined"))],
    "escalate": [shot(cam("monster", "ws", "whip_pan", "low", 24, 0, subject2="hero"), A("monster", "walk", path=["monster", "street_n"])),
                 shot(cam("hero", "mws", "track", "eye", 35, 0), A("hero", "panic_run", path=["hero", "street_s"]))],
    "clever": [shot(cam("hero", "mcu", "push_in", "low", 50, 25), A("hero", "point", expr="determined")),
               shot(cam("monster", "mws", "orbit_left", "low", 24, 0), A("monster", "freeze"))],
    "reversal": [shot(cam("monster", "cu", "push_in", "low", 85, 0), A("monster", "roar")),
                 shot(cam("hero", "cu", "handheld", "eye", 85, 0, shake=0.5), A("hero", "gasp"))],
    "climax": [shot(cam("hero", "ms", "ots", "eye", 35, 180, subject2="monster"), A("hero", "freeze", facing=180)),
               shot(cam("monster", "ws", "push_in", "worm", 24, 0), A("monster", "swipe"))],
    "win": [shot(cam("monster", "ws", "pull_out", "low", 24, 0), A("monster", "collapse")),
            shot(cam("hero", "mcu", "push_in", "eye", 50, 15), A("hero", "cheer"))],
    "ending": [shot(cam("mark:street_n", "ews", "drone_orbit", "high", 24, 0)),
               shot(cam("hero", "cu", "push_in", "eye", 85, 10), A("hero", "idle", expr="happy"))],
}


def template_film(idea, premise, lines=None):
    lines = lines or template_lines(premise)
    r = next(x for x in RULES if x["id"] == premise["rule_id"])
    beats = []
    k = {}
    for typ, spk, text in lines:
        i = k.get(typ, 0)
        k[typ] = i + 1
        sh = json.loads(json.dumps(SHOT_GRAMMAR[typ][i % len(SHOT_GRAMMAR[typ])]))
        sh["cast"] = ["hero"]
        beats.append(beat((spk if spk != "hero" else "hero", text), sh,
                          tension={"hook": .5, "rule": .4, "hero": .3, "escalate": .6, "clever": .5, "reversal": .85,
                                   "climax": .95, "win": .7, "ending": .2}[typ],
                          kind={"hook": "hit", "reversal": "braam", "win": "hit", "ending": "resolve"}.get(typ) if i == 0 else None))
    slug = re.sub(r"[^a-z0-9]+", "-", (premise["hero"] + " " + r["id"]).lower()).strip("-")
    return {
        "slug": slug, "title": f"{premise['hero']} and the {r['rule'].split()[2].title()} Rule",
        "rule_id": r["id"], "rule": r["rule"], "logline": premise["premise"], "genre": "monster thriller",
        "premises": None, "set": premise["setting"] if premise["setting"] in ("city_block", "plaza") else "city_block",
        "seed": random.randint(1, 99), "look": r["look"], "fx": ["rain"],
        "characters": {"hero": {"name": premise["hero"], "voice": premise["voice"], "accessory": "cap",
                                "palette": {"shirt": [0.1, 0.4, 0.8], "pants": [0.1, 0.1, 0.2]}},
                       "ally": {"name": "Officer Diaz", "voice": "cop", "accessory": "cap",
                                "palette": {"shirt": [0.05, 0.08, 0.2], "pants": [0.05, 0.05, 0.1], "hat": [0.05, 0.05, 0.15]}}},
        "monster": {"kind": r["monster"], "height": 52, "glow": list(r["glow"]), "seed": 3, "eyes": 2},
        "dressing": {"city_block": [{"kind": "police_car", "at": [8, -6, 0], "rot": 30}, {"kind": "barrier", "at": [-4, -10, 0]}]},
        "beats": beats, "draft": None, "critique": None, "source": "template",
    }


# ---------------------------------------------------------------- critique / rewrite

def critique(film, line_durs=None):
    notes = []
    lines = [(i, b["say"]) for i, b in enumerate(film["beats"]) if b["say"]]
    if not lines:
        return ["no lines"]
    first = lines[0][1][1]
    if len(first.split()) > 12:
        notes.append(f"HOOK too long ({len(first.split())} words) — must land in ~2 s.")
    rule_idx = next((i for i, (bi, (s, t)) in enumerate(lines) if any(w in t.lower() for w in ("only", "can't", "rule", "hunts", "never"))), None)
    if rule_idx is None or rule_idx > 4:
        notes.append("RULE stated too late — must be within the first ~8 s.")
    for bi, (s, t) in lines:
        n = len(t.split())
        if n > 14:
            notes.append(f"Line {bi} has {n} words — split or cut (punchy lines ≤ 12).")
    txt = " ".join(t for _, (s, t) in lines).lower()
    for bad in ("to be continued", "part 2", "next time", "find out", "will return"):
        if bad in txt:
            notes.append(f"Cliffhanger phrase '{bad}' — ending must be complete.")
    if film["beats"][-1].get("kind") != "resolve" and not any(b.get("kind") == "resolve" for b in film["beats"][-4:]):
        notes.append("No musical/emotional resolve in the final beats.")
    if line_durs:
        t, last_esc = 0.0, 0.0
        for b, d in zip(film["beats"], line_durs):
            t += d + b.get("pad", 0.25) + b.get("hold", 0)
            if b.get("kind") in ("hit", "braam") or (b.get("tension") or 0) >= 0.8:
                if t - last_esc > 16:
                    notes.append(f"Escalation gap of {t - last_esc:.0f}s before {t:.0f}s — need a reveal every 10-15 s.")
                last_esc = t
        if t < 60 or t > 120:
            notes.append(f"Runtime {t:.0f}s outside 60-120 s.")
    return notes or ["PASS — hook, rule timing, line length, escalation cadence, complete ending."]


def rewrite(film, notes):
    """Mechanical fixes for template/LLM drafts: split long lines at commas/dashes, trim filler."""
    filler = re.compile(r"\b(just|really|very|actually|suddenly|basically)\b ?", re.I)
    new = []
    for b in film["beats"]:
        if b["say"]:
            s, t = b["say"]
            t = filler.sub("", t).strip()
            if len(t.split()) > 14 and re.search(r"[,—;]", t):
                a, c = re.split(r"[,—;]", t, 1)
                b1 = dict(b, say=(s, a.strip() + ".")); b2 = dict(b, say=(s, c.strip()), kind=None)
                b2["shots"] = b["shots"][1:] or b["shots"]
                b1["shots"] = b["shots"][:1]
                new += [b1, b2]
                continue
            b = dict(b, say=(s, t))
        new.append(b)
    film["beats"] = new
    return film


# ------------------------------------------------------------------------ timeline

def build_timeline(film, line_durs, lead=0.08):
    """line_durs: list aligned with beats (0 for silent). Produces shotlist with absolute
    times/frames, per-shot camera plan, dialogue windows and audio cues."""
    shots, lines, cues = [], [], []
    t = 0.0
    sid = 0
    for bi, (b, d) in enumerate(zip(film["beats"], line_durs)):
        blen = max(d + b.get("pad", 0.25), b.get("hold", 0.0), 1.45) if b["say"] else max(b.get("hold", 1.0), 1.45)
        if b["say"]:
            lines.append({"beat": bi, "speaker": b["say"][0], "text": b["say"][1], "start": round(t + lead, 3),
                          "dur": round(d, 3)})
        cues.append({"t": round(t, 3), "tension": b.get("tension"), "kind": b.get("kind"), "beat": bi,
                     "sfx": b.get("sfx", []), "len": blen})
        bshots = list(b["shots"])
        # never cut faster than ~1.3 s: drop the lightest coverage until every shot is long enough
        while len(bshots) > 1 and blen * min(s.get("w", 1.0) for s in bshots) / sum(s.get("w", 1.0) for s in bshots) < 1.3:
            bshots.remove(min(bshots, key=lambda s: s.get("w", 1.0)))
        ws = [s.get("w", 1.0) for s in bshots]
        tot = sum(ws)
        tt = t
        for s, w in zip(bshots, ws):
            sl = blen * w / tot
            nfr = max(12, int(round(sl * FPS)))
            s2 = json.loads(json.dumps(s))
            sid += 1
            s2["id"] = f"s{sid:03d}"
            s2["beat"] = bi
            s2["start"] = round(tt, 3)
            s2["frames"] = nfr
            s2.setdefault("set", film["set"])
            # cast: everyone referenced by actions or explicitly listed
            cast = set(s2.get("cast", []))
            for a in s2["actions"]:
                if a["who"] != "monster":
                    cast.add(a["who"])
            s2["cast"] = sorted(cast)
            # dressing per set
            s2["props"] = film.get("dressing", {}).get(s2["set"], []) + s2.get("props", [])
            # fractional action timing t0/t1 -> frames
            for a in s2["actions"]:
                if "t0" in a:
                    a["f0"] = max(1, int(a.pop("t0") * nfr))
                if "t1" in a:
                    a["f1"] = max(2, int(a.pop("t1") * nfr))
            # mouth flaps for on-screen speaker
            if b["say"] and b["say"][0] in s2["cast"]:
                ls = max(1, int((t + lead - tt) * FPS) + 1)
                le = min(nfr, int((t + lead + d - tt) * FPS))
                if le > ls:
                    s2["talk"] = {"who": b["say"][0], "f0": ls, "f1": le}
            if "fx" not in s2:
                s2["fx"] = list(film.get("fx", []))
            s2["fx"] = s2["fx"] + film.get("set_fx", {}).get(s2["set"], [])
            tt += nfr / FPS
            shots.append(s2)
        t = tt
    # absolute frames
    f = 0
    for s in shots:
        s["start_frame"] = f
        s["start"] = round(f / FPS, 3)
        f += s["frames"]
    return {"shots": shots, "lines": lines, "cues": cues, "total_frames": f, "duration": round(f / FPS, 2)}


# ------------------------------------------------------------------------- documents

def write_docs(film, timeline, outdir, notes):
    os.makedirs(outdir, exist_ok=True)
    # story.md — the story bible
    L = [f"# {film['title']}", "", f"**Rule:** {film['rule']}  ", f"**Logline:** {film['logline']}  ",
         f"**Genre:** {film.get('genre', 'monster thriller')} · **Set:** {film['set']} · **Look:** {film['look']} · "
         f"**Runtime:** {timeline['duration']:.1f}s · **Shots:** {len(timeline['shots'])}", ""]
    if film.get("premises"):
        L += ["## 1 · Brainstorm — 10 premises, scored", "",
              "| # | Premise | Hook | Clarity | Clever | Reversal | Orig. | Total |", "|---|---|---|---|---|---|---|---|"]
        for i, p in enumerate(film["premises"]):
            sc = p["scores"]
            star = " ✅" if i == film.get("chosen", 0) else ""
            L.append(f"| {i + 1}{star} | {p['premise']} | {sc['hook']} | {sc['clarity']} | {sc['clever_use']} | "
                     f"{sc['reversal']} | {sc['originality']} | **{sc['total']}** |")
        L += ["", f"**Picked #{film.get('chosen', 0) + 1}:** {film.get('why', '')}", ""]
    L += ["## 2 · Characters", ""]
    for cid, c in film["characters"].items():
        L.append(f"- **{c.get('name', cid)}** ({c.get('voice')} voice) — {c.get('bio', '')}")
    m = film["monster"]
    L += ["", f"## 3 · The monster — {m.get('name', 'The Giant')}", "",
          f"{m.get('bio', '')}  ", f"Build: procedural `{m['kind']}`, {m['height']} m tall, glow RGB {m['glow']}, "
          f"{m.get('eyes', 2)} eyes. Signature: {m.get('signature', 'heavy stomp + roar')}.", ""]
    if film.get("outline"):
        L += ["## 4 · Outline", ""] + [f"{i + 1}. **{o[0]}** ({o[1]}) — {o[2]}" for i, o in enumerate(film["outline"])] + [""]
    if film.get("draft"):
        L += ["## 5 · Draft v1", "", "```", film["draft"].strip(), "```", ""]
    if film.get("critique"):
        L += ["## 6 · Critique (ruthless)", ""] + [f"- {c}" for c in film["critique"]] + [""]
    L += ["## 7 · Rewrite → final script", "", "See `script.md`. Automated checks on the final:", ""] + [f"- {n}" for n in notes] + [""]
    if film.get("beat_map"):
        L += ["## 8 · Beat map", ""] + [f"- {x}" for x in film["beat_map"]] + [""]
    open(os.path.join(outdir, "story.md"), "w").write("\n".join(L))
    # script.md
    S = [f"# {film['title']} — script", "", f"_Rule: {film['rule']}_", ""]
    names = {cid: c.get("name", cid).upper() for cid, c in film["characters"].items()}
    names["narrator"] = "NARRATOR"
    for ln in timeline["lines"]:
        mm, ss = divmod(ln["start"], 60)
        S.append(f"`{int(mm)}:{ss:05.2f}` **{names.get(ln['speaker'], ln['speaker'].upper())}:** {ln['text']}")
    S.append("")
    S.append(f"_Runtime {timeline['duration']:.1f}s · {len(timeline['shots'])} shots_")
    open(os.path.join(outdir, "script.md"), "w").write("\n".join(S))
    # shotlist.json — camera plan per shot
    plan = []
    for s in timeline["shots"]:
        c = s["camera"]
        plan.append({"id": s["id"], "beat": s["beat"], "start": s["start"], "dur": round(s["frames"] / FPS, 2),
                     "frames": s["frames"], "set": s["set"],
                     "camera": {"move": c.get("move"), "framing": c.get("framing"), "angle": c.get("angle"),
                                "lens_mm": c.get("lens"), "subject": c.get("subject"), "subject2": c.get("subject2"),
                                "az": c.get("az"), "note": c.get("note", "")},
                     "action": [f"{a['who']}:{a['action']}" for a in s["actions"]], "fx": s.get("fx", []),
                     "spec": s})
    json.dump({"title": film["title"], "duration": timeline["duration"], "fps": FPS, "shots": plan},
              open(os.path.join(outdir, "shotlist.json"), "w"), indent=1)
