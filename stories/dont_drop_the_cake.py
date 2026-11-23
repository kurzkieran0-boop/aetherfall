"""DON'T DROP THE CAKE — a daytime comedy in Brickton.  (authored bank film #4, 2:30)

Rule: the mayor's birthday cake must never touch the ground.
Twist: every 'obstacle' was the town stalling Benny for his own surprise party."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from story import A, beat, cam  # noqa: E402

# --- geography (town set) ---------------------------------------------------
BAKERY_DOOR = [-10.2, -64, 0.24]
B0 = [-7, -64, 0.24]           # Benny outside the bakery
ROADBLOCK = [0, -36, 0.05]
PLUM = [1.5, -38, 0.05]
ALLEY_IN = [-9, -20, 0.05]
GRANDMA = [-25, -21, 0.05]
LANE = [-40, -10, 0.05]
FIG_CAR = [-40, 4, 0]
PARK_IN = [-36, 18, 0.05]
PARK_OUT = [-14, 46, 0.05]
SQ_IN = [0, 46, 0.12]
SQ = [0, 57, 0.12]
CROWD_S = [0, 48.5, 0.12]          # the town hides at the square's entrance, BEHIND Benny
NAMED = {"mayor": [0, 50.5, 0.12], "pip": [-2.6, 51.5, 0.12], "dough": [2.8, 51.2, 0.12], "plum": [5.2, 52, 0.12],
         "grandma": [-5.2, 52.2, 0.12], "fig": [7.6, 50.8, 0.12]}


def town(acts="cheer", n=10, seed=9, t_hide=None):
    a = [["cheer", 0, 1]] if acts == "cheer" else [["hide", 0, 1]]
    if t_hide is not None:
        a = [["hide", 0, t_hide], ["cheer", t_hide + 0.02, 1]]
    return {"center": CROWD_S, "n": n, "radius": 6, "inner": 3.8, "seed": seed, "face": [0, 57, 0], "actions": a}
PIP_HIDE = [-13.5, 76, 0.12]

TOWER = [0, 92, 18]


def S(c, *acts, w=1.0, cake=True, clock=None, **kw):
    """A shot in Brickton. Benny carries the cake unless cake=False."""
    d = {"camera": c, "actions": list(acts), "w": w, "set": "town", "fx": kw.pop("fx", [])}
    if cake:
        d.setdefault("carry", {})["benny"] = "cake"
    if clock is not None:
        d["set_args"] = {"clock": [[1, clock]]}
    d.update(kw)
    if "carry" in kw and cake and "benny" not in kw["carry"]:
        d["carry"]["benny"] = "cake"
    return d


def cu(who, lens=50, az=10, move="push_in", angle="eye", **kw):
    return cam(who, "cu", move, angle, lens, az, **kw)


def mcu(who, lens=50, az=15, move="push_in", angle="eye", **kw):
    return cam(who, "mcu", move, angle, lens, az, **kw)


def ms(who, lens=35, az=20, move="push_in", angle="eye", **kw):
    return cam(who, "ms", move, angle, lens, az, **kw)


def wide(who, lens=24, az=20, move="pull_out", angle="low", framing="ws", **kw):
    return cam(who, framing, move, angle, lens, az, **kw)


PIP_SHOT = dict(crowd={"center": [-16.5, 80, 0.12], "n": 4, "radius": 2.5, "inner": 1.0, "seed": 4,
                       "actions": [["hide", 0, 1]]},
                carry={"pip": "phone"})
STALL_PROPS = []
BAND = dict(crowd={"center": [0, 26, 0.05], "n": 9, "radius": 6, "inner": 1.5, "seed": 12, "accessory": "helmet",
                   "palette": {"shirt": [0.85, 0.1, 0.12], "pants": [0.95, 0.95, 0.95], "hat": [0.95, 0.95, 0.98], "stripe": [0.95, 0.8, 0.1]},
                   "actions": [["walk", 0, 1]], "facing": 270})

FILM = {
    "slug": "dont-drop-the-cake",
    "title": "Don't Drop the Cake",
    "rule_id": "cake",
    "rule": "The mayor's cake must never touch the ground.",
    "logline": "Benny, twelve and extremely confident, has to carry the mayor's seven-layer birthday cake across "
               "Brickton by noon — but the whole town seems determined to slow him down. They are. It's his birthday.",
    "genre": "comedy",
    "set": "town", "seed": 21, "look": "sunny", "key": "F", "bpm": 132, "score_style": "playful",
    "voice_speed": 0.86,
    "runtime_target": (145, 155),
    "fx": [],
    "thumb_text": "DON'T DROP THE CAKE",
    "hook_caption": "The whole town tried to stop him delivering this cake. There was a reason. 🎂",
    "description": "Benny has one job: get the mayor's cake to the town square by noon without it touching the ground. "
                   "A road closure, forty grocery bags, the slowest parking in history and a park full of sprinklers "
                   "later… watch it twice. Every obstacle is a clue.",
    "hashtags": ["#shorts", "#animation", "#comedy", "#3danimation", "#blender", "#story", "#birthday", "#plottwist",
                 "#funny", "#fyp"],
    "thumb": None,
    "characters": {
        "benny": {"name": "Benny", "voice": "boy", "accessory": "cap",
                  "palette": {"shirt": [0.95, 0.32, 0.12], "pants": [0.15, 0.2, 0.45], "hat": [0.1, 0.45, 0.9]},
                  "bio": "12. Talks fast, thinks faster (he thinks). Calls himself a professional. Want: deliver the cake "
                         "by noon. Flaw: so sure of himself he never notices the obvious."},
        "pip": {"name": "Pip", "voice": "girl", "accessory": "ponytail",
                "palette": {"shirt": [0.3, 0.75, 0.55], "pants": [0.2, 0.2, 0.3], "hair": [0.55, 0.3, 0.08]},
                "bio": "12. Benny's best friend, on the walkie-talkie. Deadpan. Secretly running the whole operation."},
        "dough": {"name": "Mrs. Dough", "voice": "baker", "accessory": "hair", "scale": 1.05,
                  "palette": {"shirt": [0.98, 0.95, 0.92], "pants": [0.95, 0.5, 0.65], "hair": [0.35, 0.18, 0.08]},
                  "bio": "The baker. Says 'take the long way' like it's a threat."},
        "plum": {"name": "Officer Plum", "voice": "cop", "accessory": "cap", "scale": 1.1,
                 "palette": {"shirt": [0.12, 0.2, 0.45], "pants": [0.08, 0.1, 0.2], "hat": [0.1, 0.12, 0.3], "stripe": [0.95, 0.8, 0.1]},
                 "bio": "Closes roads 'for reasons'. The reasons are big."},
        "grandma": {"name": "Grandma Rose", "voice": "grandma", "accessory": "glasses", "scale": 0.92,
                    "palette": {"shirt": [0.7, 0.55, 0.9], "pants": [0.3, 0.25, 0.4], "hair": [0.9, 0.9, 0.92]},
                    "skin": [0.98, 0.85, 0.7], "bio": "Has thirty bags of groceries. Has forty."},
        "fig": {"name": "Mr. Fig", "voice": "gruff", "accessory": "glasses",
                "palette": {"shirt": [0.45, 0.55, 0.2], "pants": [0.3, 0.22, 0.15], "hair": [0.2, 0.12, 0.05]},
                "bio": "Has been parking since Tuesday."},
        "lead": {"name": "Bandleader Brass", "voice": "man", "accessory": "helmet",
                 "palette": {"shirt": [0.85, 0.1, 0.12], "pants": [0.95, 0.95, 0.95], "hat": [0.95, 0.95, 0.98], "stripe": [0.95, 0.8, 0.1]},
                 "bio": "Leads the Brickton Marching Band. Is practicing. For nothing."},
        "mayor": {"name": "Mayor Bloom", "voice": "mayor", "accessory": "helmet", "scale": 1.1,
                  "palette": {"shirt": [0.15, 0.15, 0.2], "pants": [0.12, 0.12, 0.15], "hat": [0.1, 0.1, 0.1], "stripe": [0.9, 0.1, 0.2]},
                  "bio": "Wears a sash and a hard hat (he was opening a library). It was never his birthday."},
    },
    "monster": None,
    "setting_note": "Brickton, a sunny pastel brick town: Main Street (bakery at the south end), the alley, the back lane, "
                    "the park with its sprinklers, and the Town Square with the clock tower, fountain, market stalls and bunting.",
    "dressing": {"town": [
        {"kind": "police_car", "at": [5, -33, 0], "rot": 0, "name": "plumcar"},
        {"kind": "barrier", "at": [-2, -34, 0]}, {"kind": "barrier", "at": [3, -34, 0]},
        {"kind": "sedan", "at": [8.5, -50, 0], "rot": 90, "color": [0.3, 0.6, 0.9], "name": "parked1"},
        {"kind": "sedan", "at": [8.5, 10, 0], "rot": 90, "color": [0.95, 0.8, 0.2], "name": "parked2"},
        {"kind": "sedan", "at": [-8.5, 26, 0], "rot": -90, "color": [0.9, 0.3, 0.3], "name": "parked3"},
    ]},
    "premises": [
        {"premise": "A kid must carry the mayor's cake across town by noon; the town keeps stalling him — for his own surprise party.",
         "scores": {"hook": 9, "clarity": 10, "clever_use": 8, "reversal": 10, "originality": 8, "total": 45}},
        {"premise": "A town's mayor is accidentally replaced by a goat and nobody notices for a week.",
         "scores": {"hook": 8, "clarity": 9, "clever_use": 6, "reversal": 6, "originality": 8, "total": 37}},
        {"premise": "A boy's sneeze is so strong it moves houses; the town wants him for the annual parade.",
         "scores": {"hook": 8, "clarity": 8, "clever_use": 7, "reversal": 6, "originality": 8, "total": 37}},
        {"premise": "Every statue in the square swaps places at night; a girl tries to prove it.",
         "scores": {"hook": 8, "clarity": 8, "clever_use": 7, "reversal": 7, "originality": 7, "total": 37}},
        {"premise": "A pizza delivery that has to be on time — to a house that keeps moving down the street.",
         "scores": {"hook": 8, "clarity": 8, "clever_use": 7, "reversal": 6, "originality": 7, "total": 36}},
        {"premise": "The town clock is five minutes fast and a kid has five minutes to fix it before the wedding.",
         "scores": {"hook": 7, "clarity": 8, "clever_use": 6, "reversal": 6, "originality": 6, "total": 33}},
        {"premise": "Two rival bakers bake a cake so big it blocks Main Street.",
         "scores": {"hook": 7, "clarity": 9, "clever_use": 5, "reversal": 5, "originality": 6, "total": 32}},
        {"premise": "A kid lies that he can juggle; the whole town shows up to the talent show.",
         "scores": {"hook": 8, "clarity": 9, "clever_use": 6, "reversal": 7, "originality": 6, "total": 36}},
        {"premise": "A lost balloon ties the whole town together, literally.",
         "scores": {"hook": 6, "clarity": 7, "clever_use": 6, "reversal": 5, "originality": 7, "total": 31}},
        {"premise": "A grandma enters a go-kart race against the mayor.",
         "scores": {"hook": 7, "clarity": 9, "clever_use": 6, "reversal": 6, "originality": 6, "total": 34}},
    ],
    "chosen": 0,
    "why": "Clear ticking clock (noon) + one simple rule (the cake never touches the ground) + escalating comic obstacles, "
           "and a twist that recontextualises every obstacle — so the ending pays off AND the film rewards a second watch.",
    "outline": [
        ("Hook", "0-6s", "Deep trailer narrator, ridiculous stakes: the cake must never touch the ground."),
        ("Hero", "6-20s", "Benny, 12, 'a professional'. Mrs. Dough: noon sharp — and take the long way."),
        ("Ally", "20-32s", "Pip on the walkie, deadpan. Clock tower: eleven minutes to noon."),
        ("Obstacle 1", "32-48s", "Officer Plum closes the road 'for reasons'. Big ones."),
        ("Obstacle 2", "48-66s", "Grandma Rose and her thirty (forty) bags of groceries — stacked on the cake."),
        ("Obstacle 3", "66-80s", "Mr. Fig has been parking since Tuesday."),
        ("Obstacle 4", "80-98s", "Shortcut through the park. The sprinklers go off. Nope nope nope."),
        ("All is lost", "98-110s", "Benny bursts into the square at noon. It's empty."),
        ("Twist", "110-128s", "'Turn around.' SURPRISE! It's his birthday — every obstacle was the town stalling him."),
        ("Button", "128-150s", "He carried his own birthday cake across town. The cake never touched the ground. It touched his face."),
    ],
    "draft": """NARRATOR: In the town of Brickton there is a tradition that the mayor's birthday cake must never touch the ground.
BENNY: That's no problem for me, I'm basically a professional cake delivery person.
NARRATOR: Benny was only twelve years old and was definitely not a professional.
MRS. DOUGH: Please take this cake to the town square by twelve o'clock, and make sure you take the long way.
BENNY: Why would I take the long way when the square is right there?
PIP: Benny, do you have the cake?
BENNY: Yes, I have the cake, Pip.
NARRATOR: On the way, a police officer stopped him and told him the road was closed.
NARRATOR: Then his grandmother asked him to help carry her groceries.
NARRATOR: Then Mr. Fig blocked the lane while parking his car very slowly.
NARRATOR: Benny decided to take a shortcut through the park, but the sprinklers turned on.
NARRATOR: When he finally arrived at the square, there was nobody there.
PIP: Turn around.
EVERYONE: Surprise!
NARRATOR: It was actually Benny's birthday, and the whole town had been delaying him to set up a party.
NARRATOR: Then Benny tripped and fell into the cake.""",
    "critique": [
        "The hook is a sentence about a tradition. Comedy hook = absurd stakes delivered DEAD serious: give the trailer narrator one line, then cut to the kid.",
        "Benny needs a running bit, not a description: 'I'm a professional' becomes the callback that lands the ending ('Professionally.').",
        "'Take the long way' is the first clue — make it suspicious ('Long. Way.') so a rewatch catches it.",
        "Every obstacle is narrated, not played. Each needs its own two-hander with a punchline: Plum's 'reasons', Grandma's thirty-then-forty bags, Fig 'parking since Tuesday'.",
        "No ticking clock is visible. Cut to the clock tower between obstacles — eleven, eight, three, zero minutes.",
        "Pip is just a voice. Show her — hiding behind a market stall IN THE SQUARE, with people crouched behind her. Viewers won't notice the first time.",
        "The empty square is the all-is-lost beat: let it breathe with a full music drop and the bells.",
        "The twist is explained in one flat line. Instead: rapid callback cuts — Plum, Grandma, Fig — each with a guilty wink and their own line back.",
        "Ending pratfall needs a set-up/payoff: narrator 'the cake never touched the ground' → beat → '…it touched Benny's face.'",
        "Pace: 2:30 of comedy needs fast lines (≤ 10 words), overlaps, and a cut every ~2 s. Voices sped up ~14%.",
    ],
    "beat_map": ["Laugh/reveal every 8–12 s: professional (8s) → 'Long. Way.' (18s) → 'spiritually' (28s) → 'big reasons' (40s) → "
                 "forty bags (58s) → parking since Tuesday (74s) → sprinklers (88s) → empty square (102s) → SURPRISE (112s) → "
                 "callbacks (120-132s) → splat (142s)."],
    "beats": [
        # ---------------------------------------------------------------- HOOK
        beat(("narrator", "In Brickton, the mayor's birthday cake has one rule."),
             S(cam("mark:tower", "ews", "crane_down", "high", 24, 0, pos=[22, 40, 34], pos2=[14, 30, 22]), cake=False, clock=11),
             tension=0.3, kind=None, sfx=[{"kind": "bell", "at": 0.1, "gain": 0.6}]),
        beat(("narrator", "It never. Touches. The ground."),
             S(cam("benny", "mcu", "push_in", "worm", 24, 35), A("benny", "idle", at=B0, facing=200, expr="determined")),
             tension=0.45, kind="hit"),
        # ---------------------------------------------------------------- HERO
        beat(("narrator", "Three hundred years. Not one crumb on the floor."),
             S(cam("mark:tower", "ws", "tilt_up", "worm", 24, 0, pos=[-4, -58, 0.6], pos2=[-4, -57, 0.8]),
               A("benny", "idle", at=B0, facing=180, expr="determined")),
             tension=0.4),
        beat(("benny", "Which is fine. Because I'm a professional."),
             S(ms("benny", az=25, move="orbit_right"), A("benny", "talk", at=B0, facing=200, expr="sly")),
             tension=0.4),
        beat(("narrator", "Benny was twelve. He was not a professional."),
             S(wide("benny", az=30, move="pull_out", angle="high"), A("benny", "idle", at=B0, facing=180, expr="happy")),
             tension=0.35),
        beat(("dough", "Town square. Noon sharp. And Benny?"),
             S(mcu("dough", az=-20), A("dough", "talk", at=BAKERY_DOOR, facing=100, expr="sly"),
               A("benny", "idle", at=B0, facing=260), w=1.0),
             tension=0.4),
        beat(("dough", "Take the long way."),
             S(cu("dough", az=-10, move="push_in"), A("dough", "talk", at=BAKERY_DOOR, facing=100, expr="sly"), cake=False),
             tension=0.45, kind="riser"),
        beat(("benny", "The long way? It's literally right there!"),
             S(ms("benny", lens=24, az=160, angle="low", move="push_in"), A("benny", "point", at=B0, facing=180, expr="shock"),
               clock=11),
             tension=0.45),
        beat(("dough", "Long. Way."),
             S(cu("dough", lens=85, az=0, move="static_drift"), A("dough", "idle", at=BAKERY_DOOR, facing=100, expr="angry"), cake=False),
             tension=0.5, kind="hit", sfx=[{"kind": "bonk", "at": 0.6}]),
        # ---------------------------------------------------------------- PIP
        beat(("pip", "Benny, it's Pip. Do you have the cake?"),
             S(mcu("pip", az=20, move="push_in"), A("pip", "talk", at=PIP_HIDE, facing=200, expr="sly"), cake=False, **PIP_SHOT),
             tension=0.4, voice_fx="radio"),
        beat(("benny", "Do I have the cake. Pip. I am the cake. Spiritually."),
             S(cam("benny", "mws", "track", "eye", 35, 0), A("benny", "walk", path=[[-6, -60, 0.24], [-6, -50, 0.24]], expr="sly")),
             tension=0.45),
        beat(("pip", "That doesn't mean anything."),
             S(cu("pip", az=-15, move="static_drift"), A("pip", "talk", at=PIP_HIDE, facing=200, expr="neutral"), cake=False, **PIP_SHOT),
             tension=0.45, voice_fx="radio"),
        beat(("narrator", "Eleven minutes to noon."),
             S(cam(TOWER, "ms", "tilt_up", "low", 35, 0, pos=[0, 60, 2]), cake=False, clock=11),
             tension=0.5, kind="hit", sfx=[{"kind": "bell", "at": 0.0, "gain": 0.4}]),
        # ---------------------------------------------------------------- OBSTACLE 1: PLUM
        beat(("plum", "Stop right there, son!"),
             S(cam("plum", "ms", "whip_pan", "low", 24, 0, subject2="benny", whip_at=0.15),
               A("plum", "point", at=PLUM, facing=0, expr="angry"), A("benny", "freeze", at=[-1, -44, 0.05], facing=180, expr="shock")),
             tension=0.6, kind="hit", sfx=[{"kind": "siren", "at": 0.0, "gain": 0.5}]),
        beat(("benny", "Officer, I can explain. It's a cake. It's a legal cake—"),
             S(mcu("benny", az=-15, move="handheld", shake=0.3), A("benny", "talk", at=[-1, -44, 0.05], facing=180, expr="fear")),
             tension=0.55, pad=0.05),
        beat(("plum", "Road's closed."),
             S(cam("plum", "mcu", "push_in", "worm", 24, 10), A("plum", "idle", at=PLUM, facing=0, expr="determined"), cake=False),
             tension=0.5),
        beat(("benny", "Why?"),
             S(cu("benny", az=10, move="static_drift"), A("benny", "gasp", at=[-1, -44, 0.05], facing=180, expr="shock")),
             tension=0.5, pad=0.15),
        beat(("plum", "Reasons."),
             S(cu("plum", az=-10, move="push_in", lens=85), A("plum", "idle", at=PLUM, facing=0, expr="sly"), cake=False),
             tension=0.5, pad=0.2),
        beat(("benny", "What reasons?!"),
             S(ms("benny", az=30, move="orbit_left"), A("benny", "panic", at=[-1, -44, 0.05], facing=180, expr="angry")),
             tension=0.55),
        beat(("plum", "Big ones. Go around."),
             S(cam("plum", "ms", "ots", "eye", 35, 180, subject2="benny"), A("plum", "point", at=PLUM, facing=10, expr="sly"),
               A("benny", "idle", at=[-1, -44, 0.05], facing=180, expr="sad")),
             tension=0.5, kind="hit"),
        # ---------------------------------------------------------------- OBSTACLE 2: GRANDMA
        beat(("benny", "Is it a big reason or a—"),
             S(mcu("benny", az=20, move="push_in", angle="low"), A("benny", "talk", at=[-1, -44, 0.05], facing=180, expr="sly")),
             tension=0.5, pad=0.0),
        beat(("plum", "Bigger than you."),
             S(cam("plum", "mcu", "push_in", "worm", 24, -15), A("plum", "idle", at=PLUM, facing=0, expr="angry"), cake=False),
             tension=0.55, kind="hit", sfx=[{"kind": "bonk", "at": 0.5}]),
        beat(("narrator", "Around meant the alley. The alley meant Grandma Rose."),
             S(cam("benny", "ws", "crane_up", "high", 24, 0, pos=[-6, -12, 3], pos2=[-7, -14, 12]),
               A("benny", "walk", path=[[-8, -20, 0.05], [-18, -20, 0.05]])),
             tension=0.45),
        beat(("grandma", "Benny, sweetie! Help me with my groceries?"),
             S(mcu("grandma", az=20, move="push_in", angle="low"), A("grandma", "talk", at=GRANDMA, facing=270, expr="happy"),
               props=[{"kind": "crate", "at": [-26.5, -22, 0], "size": 0.6}, {"kind": "crate", "at": [-27, -20.5, 0], "size": 0.6}]),
             tension=0.4),
        beat(("benny", "Grandma, I'm holding a seven-layer cake!"),
             S(ms("benny", az=-30, move="push_in"), A("benny", "talk", at=[-20, -20, 0.05], facing=90, expr="fear")),
             tension=0.45),
        beat(("grandma", "Just thirty bags, dear."),
             S(cu("grandma", az=-10, move="static_drift"), A("grandma", "idle", at=GRANDMA, facing=270, expr="happy"), cake=False),
             tension=0.45, kind="hit", sfx=[{"kind": "bonk", "at": 0.7}]),
        beat(("benny", "Grandma, you live alone!"),
             S(cu("benny", az=-20, move="push_in"), A("benny", "talk", at=[-20, -20, 0.05], facing=90, expr="shock")),
             tension=0.45),
        beat(("grandma", "I'm a big eater, dear."),
             S(mcu("grandma", az=25, move="static_drift"), A("grandma", "idle", at=GRANDMA, facing=270, expr="sly"), cake=False),
             tension=0.45, kind="hit"),
        beat(("narrator", "It was not thirty bags."),
             S(cam("benny", "ms", "tilt_up", "worm", 24, 0), A("benny", "walk", path=[[-20, -20, 0.05], [-24, -16, 0.05]], expr="sad"),
               carry={"benny": "cake_bags"}, cake=False),
             tension=0.5),
        beat(("narrator", "It was forty."),
             S(cam("benny", "ws", "pull_out", "high", 24, 40), A("benny", "walk", path=[[-26, -14, 0.05], [-34, -8, 0.05]], expr="sad"),
               A("grandma", "cheer", at=[-25, -21, 0.05], facing=300), carry={"benny": "cake_bags"}, cake=False),
             tension=0.5, kind="hit", sfx=[{"kind": "bonk", "at": 0.2}]),
        beat(("pip", "Eight minutes, Benny!"),
             S(mcu("pip", az=30, move="push_in"), A("pip", "talk", at=PIP_HIDE, facing=200, expr="sly"), cake=False, **PIP_SHOT),
             tension=0.55, voice_fx="radio"),
        beat(("benny", "I know, Pip!"),
             S(cu("benny", az=0, move="handheld", shake=0.3), A("benny", "run", path=[[-38, -12, 0.05], [-40, -6, 0.05]], expr="angry")),
             tension=0.6, voice_fx=None),
        # ---------------------------------------------------------------- OBSTACLE 3: FIG
        beat(("narrator", "Then Mr. Fig tried to park."),
             S(cam("mark:lane", "ws", "drone_orbit", "high", 24, 0, pos=[-26, -14, 18], pos2=[-30, -18, 16]),
               A("benny", "freeze", at=LANE, facing=180, expr="shock"), A("fig", "idle", at=[-34, 6, 0.05], facing=90),
               props=[{"kind": "sedan", "at": [-44, 4, 0], "rot": 0, "color": [0.45, 0.55, 0.2], "name": "figcar",
                       "move": {"to": [-37, 4, 0], "f0": 1, "f1": 40}}]),
             tension=0.5, sfx=[{"kind": "horn", "at": 0.3}]),
        beat(("fig", "Almost… almost… nope."),
             S(mcu("fig", az=-20, move="push_in"), A("fig", "talk", at=[-34, 6, 0.05], facing=90, expr="determined"), cake=False,
               props=[{"kind": "sedan", "at": [-37, 4, 0], "rot": 0, "color": [0.45, 0.55, 0.2], "name": "figcar",
                       "move": {"to": [-43, 4, 0], "f0": 1, "f1": 40}}]),
             tension=0.5),
        beat(("benny", "Mr. Fig! You've been parking since Tuesday!"),
             S(ms("benny", az=-20, angle="low", move="push_in"), A("benny", "point", at=LANE, facing=180, expr="angry"),
               props=[{"kind": "sedan", "at": [-43, 4, 0], "rot": 0, "color": [0.45, 0.55, 0.2], "name": "figcar"}]),
             tension=0.6, kind="hit", sfx=[{"kind": "horn", "at": 0.8}]),
        beat(("fig", "Parking is an art, son."),
             S(cu("fig", az=10, move="static_drift"), A("fig", "idle", at=[-34, 6, 0.05], facing=90, expr="sly"), cake=False),
             tension=0.5),
        beat(("benny", "It's a car, Mr. Fig! Not a painting!"),
             S(ms("benny", az=30, move="orbit_right", angle="low"), A("benny", "point", at=LANE, facing=150, expr="angry")),
             tension=0.55),
        beat(("narrator", "Benny had one move left."),
             S(cu("benny", lens=85, az=0, move="dolly_zoom"), A("benny", "idle", at=LANE, facing=180, expr="determined")),
             tension=0.6, kind="riser"),
        beat(("benny", "Shortcut. Through. The park."),
             S(cam("benny", "cu", "push_in", "worm", 35, 20), A("benny", "idle", at=LANE, facing=200, expr="determined")),
             tension=0.7, kind="hit"),
        # ---------------------------------------------------------------- OBSTACLE 4: SPRINKLERS
        beat(("pip", "Benny, the sprinklers go off at—"),
             S(mcu("pip", az=-20, move="push_in"), A("pip", "talk", at=PIP_HIDE, facing=200, expr="shock"), cake=False, **PIP_SHOT),
             tension=0.6, voice_fx="radio", pad=0.0),
        beat(None,
             S(cam("mark:park", "ws", "push_in", "low", 24, 0, pos=[-22, 12, 1.0], pos2=[-23, 15, 1.2]),
               A("benny", "run", path=[PARK_IN, [-28, 26, 0.05]]),
               fx=[{"kind": "spray", "at": [-30, 26, 0.1], "count": 400, "height": 4}, {"kind": "spray", "at": [-22, 32, 0.1], "count": 400, "height": 4},
                   {"kind": "spray", "at": [-26, 40, 0.1], "count": 400, "height": 4}]),
             hold=1.6, tension=0.75, kind="hit", sfx=[{"kind": "sprinkler", "at": 0.0}]),
        beat(("pip", "…now."),
             S(cu("pip", az=0, move="static_drift"), A("pip", "idle", at=PIP_HIDE, facing=200, expr="sly"), cake=False, **PIP_SHOT),
             tension=0.6, voice_fx="radio"),
        beat(("benny", "Nope, nope, nope, nope, nope, nope!"),
             S(cam("benny", "ms", "track", "eye", 24, 0), A("benny", "panic_run", path=[[-28, 26, 0.05], [-20, 36, 0.05]]),
               fx=[{"kind": "spray", "at": [-22, 32, 0.1], "count": 400, "height": 4}, {"kind": "spray", "at": [-26, 40, 0.1], "count": 400, "height": 4}], w=1.0),
             S(cam("benny", "ws", "orbit_right", "low", 24, 40), A("benny", "panic_run", path=[[-20, 36, 0.05], PARK_OUT]),
               fx=[{"kind": "spray", "at": [-22, 32, 0.1], "count": 400, "height": 4}, {"kind": "spray", "at": [-26, 40, 0.1], "count": 400, "height": 4}], w=1.0),
             tension=0.85, sfx=[{"kind": "sprinkler", "at": 0.0}]),
        beat(("narrator", "The cake stayed dry. Benny did not."),
             S(ms("benny", az=40, move="push_in", angle="low"), A("benny", "idle", at=PARK_OUT, facing=230, expr="sad")),
             tension=0.5, kind="hit"),
        beat(("narrator", "And then, of course, the marching band."),
             S(cam("benny", "ws", "push_in", "high", 24, 0, pos=[10, 18, 9], pos2=[8, 20, 7]),
               A("benny", "freeze", at=[-2, 22, 0.05], facing=180, expr="shock"), **BAND),
             tension=0.6, kind="hit", sfx=[{"kind": "band", "at": 0.0}]),
        beat(("benny", "Cake coming through! Excuse me! Cake!"),
             S(cam("benny", "ms", "track", "eye", 24, 20), A("benny", "sneak", path=[[-2, 22, 0.05], [2, 30, 0.05]], expr="fear"), **BAND),
             tension=0.7, sfx=[{"kind": "band", "at": 0.0}]),
        beat(("lead", "Sorry, kid! We're practicing!"),
             S(mcu("lead", az=10, move="push_in", angle="low"), A("lead", "talk", at=[4, 28, 0.05], facing=270, expr="happy"), cake=False, **BAND),
             tension=0.6),
        beat(("benny", "Practicing for what?!"),
             S(cu("benny", az=-15, move="handheld", shake=0.3), A("benny", "talk", at=[2, 30, 0.05], facing=90, expr="angry"), **BAND),
             tension=0.6),
        beat(("lead", "…Nothing!"),
             S(cu("lead", az=0, move="static_drift"), A("lead", "idle", at=[4, 28, 0.05], facing=270, expr="sly"), cake=False, **BAND),
             tension=0.55, kind="hit", sfx=[{"kind": "bonk", "at": 0.5}]),
        beat(("pip", "Two minutes! Where are you?"),
             S(mcu("pip", az=10, move="push_in"), A("pip", "talk", at=PIP_HIDE, facing=200, expr="fear"), cake=False, **PIP_SHOT),
             tension=0.7, voice_fx="radio"),
        beat(("benny", "Coming in hot!"),
             S(cam("benny", "mws", "track", "low", 24, 0), A("benny", "run", path=[[0, 34, 0.05], [0, 48, 0.12]], expr="determined"), clock=1),
             tension=0.9, kind="hit"),
        # ---------------------------------------------------------------- ALL IS LOST
        beat(("narrator", "Benny burst into the town square, and…"),
             S(cam("benny", "ws", "pull_out", "low", 24, 0), A("benny", "run", path=[SQ_IN, SQ], facing=180, expr="determined"),
               crowd=town("hide"), clock=0),
             tension=0.6, kind="riser"),
        beat(None,
             S(cam("benny", "ews", "pull_out", "high", 24, 0, pos=[12, 74, 14], pos2=[16, 80, 22]),
               A("benny", "idle", at=SQ, facing=180, expr="shock"), crowd=town("hide"), clock=0),
             hold=2.0, tension=0.1, kind="drop", sfx=[{"kind": "bells", "at": 0.0}]),
        beat(("benny", "Hello? Mayor? Anybody? I have… a cake?"),
             S(mcu("benny", az=0, move="push_in"), A("benny", "idle", at=SQ, facing=180, expr="sad"), crowd=town("hide"), clock=0),
             tension=0.2),
        beat(("benny", "Wrong day? Is it Tuesday? Mr. Fig, is it Tuesday?!"),
             S(cam("benny", "ms", "handheld", "low", 24, 30, shake=0.4), A("benny", "panic", at=SQ, facing=180, expr="fear"),
               crowd=town("hide"), clock=0),
             tension=0.3, kind="hit"),
        beat(("benny", "Pip, nobody's here. Is there a second town square?!"),
             S(ms("benny", az=-25, move="orbit_left"), A("benny", "talk", at=SQ, facing=180, expr="fear"), crowd=town("hide"), clock=0),
             tension=0.3),
        beat(("pip", "Benny. Turn around."),
             S(mcu("benny", az=0, move="push_in", lens=35), A("benny", "idle", at=SQ, facing=180, expr="fear"),
               A("pip", "hide", at=NAMED["pip"], facing=180), crowd=town("hide"), clock=0),
             tension=0.4, kind="riser"),
        beat(("crowd", "Surprise!"),
             S(cam("benny", "ms", "ots", "eye", 24, 180, subject2=[0, 50, 1.6]), A("benny", "turn", at=SQ, facing=180, to=360, expr="shock"),
               *[A(k, "cheer", at=v, facing=180) for k, v in NAMED.items()], crowd=town(t_hide=0.15)),
             tension=0.95, kind="hit", sfx=[{"kind": "cheer", "at": 0.15}]),
        beat(("mayor", "Happy birthday, Benny!"),
             S(cam("mayor", "mcu", "push_in", "low", 35, 0), *[A(k, "cheer", at=v, facing=180) for k, v in NAMED.items()],
               crowd=town(), cake=False),
             tension=0.8),
        beat(("benny", "…It's my birthday?"),
             S(cu("benny", az=0, move="push_in"), A("benny", "idle", at=SQ, facing=0, expr="shock")),
             tension=0.5, pad=0.4),
        beat(("pip", "It's your birthday."),
             S(mcu("pip", az=10, move="push_in"), A("pip", "idle", at=NAMED["pip"], facing=170, expr="happy"), crowd=town(), cake=False),
             tension=0.5),
        beat(("narrator", "The road closure. The groceries. The world's slowest parking."),
             S(mcu("plum", az=25, move="push_in", angle="low"), A("plum", "idle", at=NAMED["plum"], facing=200, expr="sly"), crowd=town(), cake=False),
             S(mcu("grandma", az=-25, move="push_in", angle="low"), A("grandma", "idle", at=NAMED["grandma"], facing=160, expr="sly"), crowd=town(), cake=False),
             S(mcu("fig", az=30, move="push_in", angle="low"), A("fig", "idle", at=NAMED["fig"], facing=210, expr="sly"), crowd=town(), cake=False),
             tension=0.55),
        beat(("narrator", "The whole town had been stalling him for an hour."),
             S(cam("benny", "ws", "drone_orbit", "high", 24, 180), A("benny", "idle", at=SQ, facing=0, expr="shock"),
               *[A(k, "cheer", at=v, facing=180) for k, v in NAMED.items()], crowd=town()),
             tension=0.6, kind="hit"),
        beat(("grandma", "Forty bags, dear. Forty!"),
             S(mcu("grandma", az=-15, move="push_in", angle="low"), A("grandma", "talk", at=NAMED["grandma"], facing=160, expr="happy"),
               crowd=town(), cake=False),
             tension=0.5),
        beat(("plum", "Big reasons."),
             S(cu("plum", az=15, move="static_drift"), A("plum", "idle", at=NAMED["plum"], facing=200, expr="sly"), crowd=town(), cake=False),
             tension=0.5),
        beat(("benny", "So the cake…"),
             S(mcu("benny", az=-20, move="push_in"), A("benny", "idle", at=SQ, facing=0, expr="sad")),
             tension=0.45),
        beat(("dough", "Was always for you, sweetie."),
             S(mcu("dough", az=10, move="push_in"), A("dough", "talk", at=NAMED["dough"], facing=190, expr="happy"), crowd=town(), cake=False),
             tension=0.45, kind="resolve"),
        beat(("benny", "I carried my own birthday cake across the entire town?!"),
             S(cam("benny", "ms", "orbit_right", "low", 24, 0), A("benny", "panic", at=SQ, facing=0, expr="shock")),
             tension=0.6),
        beat(("pip", "Professionally."),
             S(cu("pip", az=10, move="static_drift"), A("pip", "idle", at=NAMED["pip"], facing=170, expr="sly"), crowd=town(), cake=False),
             tension=0.4, pad=0.4, kind="hit"),
        beat(("benny", "…Professionally."),
             S(cu("benny", az=-10, move="push_in"), A("benny", "idle", at=SQ, facing=0, expr="happy")),
             tension=0.4, pad=0.35),
        # ---------------------------------------------------------------- BUTTON
        beat(("narrator", "And the cake never touched the ground."),
             S(cam("benny", "ms", "push_in", "low", 35, 0, pos=[6.5, 56.5, 1.0], pos2=[5.5, 56, 1.0]),
               A("benny", "walk", path=[SQ, [0, 55, 0.12]], facing=0, expr="happy"), crowd=town()),
             tension=0.5),
        beat(None,
             S(cam("benny", "ms", "push_in", "low", 35, 0, pos=[5, 53, 1.1], pos2=[4.5, 53.5, 1.0]),
               A("benny", "fall", at=[0, 55, 0.12], facing=0), splat={"who": "benny", "f": 14},
               crowd={**town(), "actions": [["cheer", 0, 0.3], ["gasp", 0.3, 1]]}),
             hold=1.5, tension=0.2, kind="drop", sfx=[{"kind": "splat", "at": 0.38}, {"kind": "bonk", "at": 0.32}]),
        beat(("narrator", "It touched Benny's face."),
             S(cam("benny", "cu", "push_in", "eye", 35, 0, pos=[2.2, 52.6, 0.9], pos2=[1.8, 52.9, 0.8]),
               A("benny", "fall", at=[0, 55, 0.12], facing=0, t0=0.0, t1=0.05), splat={"who": "benny", "f": 1}),
             tension=0.3, kind="hit"),
        beat(("benny", "Still counts!"),
             S(cam("benny", "ws", "crane_up", "low", 24, 0, pos=[9, 58, 1.5], pos2=[11, 60, 8]),
               A("benny", "cheer", at=[0, 55, 0.12], facing=0), *[A(k, "cheer", at=v, facing=180) for k, v in NAMED.items()],
               splat={"who": "benny", "f": 1}, crowd=town(n=12)),
             tension=0.6, kind="resolve", sfx=[{"kind": "cheer", "at": 0.3}]),
        beat(("narrator", "Happy birthday, Benny."),
             S(cam("mark:tower", "ews", "crane_up", "high", 24, 0, pos=[8, 38, 6], pos2=[16, 28, 34]),
               A("benny", "cheer", at=[0, 55, 0.12], facing=0), *[A(k, "cheer", at=v, facing=180) for k, v in NAMED.items()],
               splat={"who": "benny", "f": 1}, crowd=town(n=12), clock=0),
             tension=0.3, pad=2.0, sfx=[{"kind": "bells", "at": 0.3}]),
    ],
}

# comedic timing: a beat of air after every punchline / reveal
for _b in FILM["beats"]:
    if _b.get("kind") == "hit":
        _b["pad"] = _b.get("pad", 0.25) + 0.35
