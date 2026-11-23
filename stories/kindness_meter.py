"""THE KINDNESS METER — authored bank film #5 (rig v2: armatures, IK, face shape keys).

Premise (user's): a number above everyone's head counts how many times they've helped
someone. Everyone has thousands. The hero has a glowing red 0. During a server-wide meteor
storm the high-number players flee with their rare pets; the zero stays to rescue a
trapped default character. His 0 flips to a gold infinity — 0 meant he never did a fake
good deed for clout.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from story import A, beat, cam  # noqa: E402

# ------------------------------------------------------------------ geography (meter_city)
Z = 0.05
HERO = [0, -4, Z]                    # plaza spot
DOOR = [-18.55, -3.58, Z]            # in front of the TOYS door (door faces +X)
BRAM_IN = [-20.65, -3.58, Z]         # shopkeeper inside the door alcove
KID = [-5.5, -9.5, Z]
MOM = [-6.6, -11.0, Z]
WHISP = [-2.5, -12.5, Z]
OLD = [7.0, -8.0, Z]
LUXE_A = [3.0, -6.5, Z]
WATCH = [7.5, -13.5, Z]
FOUNT_MOM = [-3.0, 1.6, Z]
BENCH_H = [11.4, -25.35, Z]
BENCH_G = [12.65, -25.35, Z]
BR_KNEEL = [-8.0, -29.05, 0.58]
BR_TOY = [-7.6, -32.3, 0.58]
BR_POST = [-7.45, -31.0, 0.58]
PIN = [2.5, 33.4, Z]
DIG = [1.2, 32.2, Z]
LIFT = [0.55, 32.3, Z]
SAFE = [3.5, 25.0, Z]
CROSS0 = [9.0, -18.0, Z]
CROSS1 = [15.0, -18.0, Z]
SKY = [6, -60, 120]

HEROSPEC = {"name": "Me (the Zero)", "voice": "kokoro:am_michael:0.96", "accessory": "hair", "meter": "zero",
            "palette": {"shirt": (0.085, 0.09, 0.11), "pants": (0.11, 0.12, 0.16), "hair": (0.06, 0.04, 0.03),
                        "sleeve": (0.075, 0.08, 0.1), "shoes": (0.6, 0.12, 0.1)},
            "skin": (0.88, 0.69, 0.5), "mark": "plaza",
            "bio": "Narrator. Mid-teens, hoodie, quiet. Helps people only when nobody's around — so his meter has "
                   "never moved off a red 0. Want: one point, one person who doesn't flinch. Flaw: has stopped "
                   "expecting anyone to."}


def S(c, *acts, act="cold", w=1.0, sky="night", dmg=0.0, sa=None, **kw):
    """A shot in the meter city. act = colour-script lighting (cold | warm | red | gold)."""
    d = {"camera": c, "actions": list(acts), "w": w, "set": "meter_city", "act": act,
         "set_args": dict({"sky": sky, "damage": dmg}, **(sa or {}))}
    d.update(kw)
    return d


def R(c, *acts, **kw):          # red-sky disaster shot
    kw.setdefault("act", "red")
    kw.setdefault("sky", "red")
    kw.setdefault("sa", {"sirens": True})
    return S(c, *acts, **kw)


def mill(center=(0, -2, Z), n=26, r=13, seed=3, **kw):
    return dict({"kind": "mill", "center": list(center), "n": n, "radius": r, "seed": seed, "inner": 2.5}, **kw)


# ======================================================================= THE FILM
FILM = {
    "slug": "kindness-meter",
    "title": "The Kindness Meter",
    "rig": "v2",
    "rule_id": "meter",
    "rule": "A number above everyone's head counts how many times they've helped someone.",
    "logline": "In a city where a glowing number over every head counts your good deeds, the only person stuck at "
               "a red zero is the one who never helps for an audience — and when meteors fall, he's the only one "
               "who stays.",
    "genre": "emotional drama / disaster",
    "set": "meter_city", "seed": 7, "look": "kindness", "key": "D", "bpm": 92, "score_style": "kindness",
    "runtime_target": (135, 160),
    "hook_card": "In this world, a number floats above everyone's head showing how many times they've helped "
                 "someone, and mine was stuck at zero.",
    "fx": [],
    "thumb_text": "STUCK AT ZERO",
    "title_options": [
        "Everyone Had Thousands. He Had Zero.",
        "His Kindness Meter Was Stuck at Zero… Until the Meteors Hit",
        "The Kindness Meter",
    ],
    "hook_caption": "Everyone had thousands. He had a red zero. Then the meteors came. ☄️",
    "description": "In a city where a glowing number above your head counts every time you've helped someone, "
                   "everyone has thousands — except one kid with a red 0. Shops slam doors on him. VIPs mock him. "
                   "Then a server-wide meteor storm hits, the top helpers run for their rare pets, and the zero is the "
                   "only one who stays. Watch it twice: the clue is two frames long.",
    "hashtags": ["#animation", "#3danimation", "#shortfilm", "#storytime", "#blender", "#kindness", "#plottwist",
                 "#emotional", "#fyp", "#shorts"],
    "platform_tags": {
        "tiktok": ["#animation", "#3danimation", "#storytime", "#plottwist", "#kindness", "#fyp", "#foryou", "#emotional"],
        "reels": ["#animation", "#3danimation", "#shortfilm", "#reels", "#kindness", "#plottwist", "#explorepage", "#blender"],
        "shorts": ["#shorts", "#animation", "#3danimation", "#shortfilm", "#kindness", "#plottwist", "#storytime"],
    },
    "pinned_comment": "Be honest: if this number floated over YOUR head right now, would it be high… and would it be real? 👇",
    "thumb": {"kind": "flip_half"},
    "characters": {
        "hero": HEROSPEC,
        "vo": {"name": "Narration (his voice)", "voice": "kokoro:am_michael:0.94", "meter": None,
               "bio": "First-person voice-over: calm, close, a little tired."},
        "guest": {"name": "Guest", "voice": "kokoro:af_sky:1.0:2", "style": "default", "scale": 0.74,
                  "palette": {"shirt": (0.72, 0.73, 0.76), "pants": (0.6, 0.61, 0.64), "shoes": (0.45, 0.46, 0.5)},
                  "skin": (0.8, 0.81, 0.84), "meter": {"value": 2, "color": "grey"}, "mark": "pin",
                  "bio": "A brand-new default character: blank grey, dot eyes, meter at 2. The only person who doesn't "
                         "read the number before the face."},
        "luxe": {"name": "Luxe", "voice": "kokoro:af_bella:1.06", "accessory": "crown", "scale": 1.02,
                 "palette": {"shirt": (0.95, 0.58, 0.05), "pants": (0.96, 0.96, 0.98), "hair": (0.98, 0.9, 0.62),
                             "stripe": (1.0, 0.95, 0.9), "shoes": (0.95, 0.95, 0.97)},
                 "badge": (1.0, 0.72, 0.18), "meter": {"value": 9881, "color": "gold", "after": {"9": 9882}},
                 "bio": "#1 on the leaderboard (9,882). Helps beautifully — the moment a phone comes up."},
        "vance": {"name": "Vance", "voice": "kokoro:am_puck:1.04", "accessory": "shades", "scale": 1.06,
                  "palette": {"shirt": (0.94, 0.94, 0.96), "pants": (0.1, 0.1, 0.12), "hair": (0.15, 0.1, 0.06),
                              "stripe": (1.0, 0.72, 0.2), "shoes": (0.9, 0.7, 0.2)},
                  "badge": (1.0, 0.72, 0.18), "meter": {"value": 8409, "color": "gold", "after": {"15": 8410, "26": 8411}},
                  "bio": "#2 (8,410). Shades at night. Believes the number is the person."},
        "bram": {"name": "Mr. Bram", "voice": "kokoro:bm_george:0.98", "accessory": "beanie", "scale": 1.08,
                 "palette": {"shirt": (0.35, 0.22, 0.14), "pants": (0.2, 0.18, 0.18), "hat": (0.5, 0.12, 0.1),
                             "stripe": (0.92, 0.9, 0.85)},
                 "skin": (0.72, 0.52, 0.38), "meter": {"value": 3120}, "mark": "shop_in",
                 "bio": "Owner of TOYS. Reads numbers, not faces. Holds the door at the end — and says nothing."},
        "mom": {"name": "Shopper", "voice": "kokoro:af_sarah:1.04", "accessory": "ponytail",
                "palette": {"shirt": (0.3, 0.6, 0.55), "pants": (0.22, 0.2, 0.3), "hair": (0.45, 0.25, 0.1)},
                "skin": (0.62, 0.43, 0.3), "meter": {"value": 2455},
                "bio": "Won't take help from a zero. Will take it from a camera."},
        "kid": {"name": "Kid", "voice": "kokoro:af_nova:1.05", "accessory": "cap", "scale": 0.72,
                "palette": {"shirt": (0.95, 0.5, 0.2), "pants": (0.2, 0.3, 0.6), "hat": (0.2, 0.55, 0.95)},
                "meter": {"value": 118}, "bio": "Backs away from red numbers."},
        "oldman": {"name": "Old Man Pell", "voice": "kokoro:bm_lewis:0.95", "accessory": "glasses", "scale": 0.95,
                   "palette": {"shirt": (0.45, 0.4, 0.52), "pants": (0.25, 0.22, 0.2), "hair": (0.85, 0.85, 0.86)},
                   "skin": (0.95, 0.82, 0.66), "meter": {"value": 6004, "color": "gold"},
                   "bio": "Gets 'helped' a lot. Mostly on camera."},
    },
    "monster": None,
    "setting_note": "A blocky night city built around one plaza: the TOYS shop row (west), the gold VIP 5,000+ lounge "
                    "(east), the Spire with its TOP HELPERS leaderboard (north) and the canal footbridge (south). "
                    "Colour script: cold blue loneliness → burning red disaster → warm gold at the end.",
    "premises": [],
}

# ---------------------------------------------------------------------- writing process (shown in story.md)
FILM["outline"] = [
    ("Hook", "0:00-0:05", "ECU red 0 + on-screen hook text; reveal the face under it."),
    ("World & rule", "0:05-0:25", "Sea of thousands; VIP rope; shop door slammed; kid backs away; whispers; staged "
                                   "help ticks +1 only when phones rise. Plant: why won't mine move?"),
    ("His life", "0:25-0:50", "Offers help in public — refused/mocked ('a zero can't be trusted'); funny-sad box "
                               "catch by a VIP on camera; one tender bench scene with Guest (meter 2)."),
    ("Planted clue", "0:50-1:05", "Alone at night he fixes a bridge plank and returns a lost pet toy. The 0 glitches "
                                   "to gold ∞ for exactly 2 frames. VIP help stops the instant the phone drops."),
    ("Disaster", "1:05-1:25", "SERVER EVENT: METEOR STORM. Red sky, first impact on the plaza, signs tear off, "
                              "crowds stampede, the Spire cracks and leans."),
    ("Abandonment", "1:25-1:50", "VIPs grab legendary pets and run past people who need help; numbers flicker. "
                                 "'Move, zero!' — shoved down. Guest pinned under the Spire. Everyone passes."),
    ("Rescue", "1:50-2:10", "Countdown to the next impact. Dig, lift, slip, fall, get up, lift. 'Your number's "
                            "not going up.' 'Doesn't matter.' Meteor #2 hits the Spire as they clear it."),
    ("Twist", "2:10-2:25", "Silence. The red 0 cracks and flips to a gold ∞ in slow motion. The crowd stares. "
                           "The meter only counted help with an audience. VIP numbers drain red."),
    ("Payoff", "2:25-2:35", "The shopkeeper holds the door. Guest takes his hand. Push-in on ∞. Last line. Black."),
]
FILM["draft"] = """DRAFT v1 (rejected)
NARRATOR: Everyone in Bricktown has a kindness number.
NARRATOR: Mine is zero. Nobody knows why.
NARRATOR: The rich kids have thousands and they show it off.
NARRATOR: One day meteors started falling from the sky.
NARRATOR: Everyone ran away to save their pets.
NARRATOR: I saved a little kid who was stuck.
NARRATOR: My number turned into infinity because I was a true hero all along.
NARRATOR: The end. Be kind!"""
FILM["critique"] = [
    "HOOK — v1 opens on exposition ('Everyone in Bricktown has…'). No image, no stakes. FIX: open on an ECU of the "
    "red 0 with the full rule as an on-screen card; first spoken words land the sting ('mine was stuck at zero').",
    "TELL vs SHOW — v1 narrates every event. FIX: narrator only bridges; the rule is SHOWN (door slam, kid backing away, "
    "a +1 that only ticks when phones rise).",
    "TWIST FAIRNESS — v1's infinity comes from nowhere ('true hero all along'). FIX: plant it twice: (1) the 0 glitches to "
    "∞ for exactly 2 frames when he helps unseen; (2) VIP numbers only tick under cameras and help stops when the phone "
    "drops. The payoff line names the mechanism: the meter counted audiences.",
    "MIDDLE SAG — v1 jumps from 'shows it off' to meteors. FIX: a public-help attempt that fails comically (box catch on "
    "camera, 'literally over your head'), then one tender beat (Guest, meter 2) so we care who gets trapped later.",
    "STAKES — v1 rescue is one line. FIX: countdown overlay, a slip and fall (near-failure), the Spire leaning, a second "
    "meteor, and the kid telling him his number isn't moving ('Doesn't matter').",
    "EMOTION — v1 ends on a moral. FIX: silence before the flip; nobody speaks at the payoff; the shopkeeper who slammed "
    "the door now holds it; a quotable last line that reframes the title ('the only kind that counts').",
    "ESCALATION CADENCE — every 10-15 s there is a new reveal: door slam (0:11), +1 under cameras (0:19), the mock (0:35), "
    "Guest (0:42), 2-frame glitch (0:58), phone-drop (1:03), red sky (1:06), impact (1:12), Spire (1:22), shove (1:32), "
    "pinned kid (1:38), countdown (1:52), slip (1:58), meteor #2 (2:06), flip (2:14), numbers fall (2:20), door (2:27).",
]
FILM["rewrites"] = [
    "v2: added the plank + pet-toy clue scene, the camera-only VIP plant, Guest's bench scene, the shove.",
    "v3: cut 30% of narration words; replaced 'true hero' with the audience mechanism; moved 'Turns out…' to a title "
    "card in his voice; made the payoff wordless except the last line; 'You're welcome!' and 'literally over your head' "
    "added as the two comic beats; last line rewritten from 'Be kind' to 'That's the only kind that counts.'",
]
FILM["self_check"] = {
    "Is the hook sharp?": "Yes — a pulsing red 0 in ECU plus the rule in one card, and the sting in the first spoken line.",
    "Is the twist fair and surprising?": "Fair: planted twice (2-frame ∞ glitch, +1 only under cameras). Surprising: the "
                                          "audience assumes he never helped; the film shows he only ever helped unseen.",
    "Does the clue pay off?": "Yes — the exact ∞ glyph from the 2-frame glitch is what the 0 becomes; the camera-only plant "
                              "pays off when the VIP numbers drain.",
    "Does the middle ever sag?": "No beat runs longer than ~12 s without a new reveal or turn (see cadence list).",
    "Does it make people feel something?": "Rejection → tenderness (bench) → injustice (shove, everyone passing) → effort "
                                           "and near-failure → silence → release (gold ∞, held door, taken hand).",
}

# =================================================================== BEATS
B = []
# ---------------------------------------------------------------- HOOK 0:00
B.append(beat(("vo", "A number floats over everyone's head. How many times they've helped someone."),
              S(cam([0, -4, 2.86], "cu", "push_in", "low", 85, 4, fstop=1.4, amount=1.4, note="ECU red 0 → his eyes beneath it"),
                A("hero", "idle", at=HERO, facing=0, expr="lonely"),
                crowd=[mill((0, -9, Z), n=18, r=9, seed=11)], engine="cycles", spp=12, step=2, w=1.25),
              S(cam("hero", "cu", "pull_out", "low", 50, 8, fstop=2.0, note="reveal the face under it"),
                A("hero", "idle", at=HERO, facing=0, expr="lonely", look_at=[0, -4, 3.4]),
                crowd=[mill((0, -9, Z), n=18, r=9, seed=11)]),
              tension=0.25, kind="open", hook_card=True, pad=0.15))
B.append(beat(("vo", "Mine was stuck at zero."),
              S(cam("hero", "mcu", "push_in", "eye", 50, -14, fstop=2.0),
                A("hero", "idle", at=HERO, facing=0, exprs=[[0.0, "lonely"], [0.45, "sad"]]),
                crowd=[mill((0, -10, Z), n=16, r=9, seed=12)], step=2),
              tension=0.3, pad=0.35, hook_card=True))
# ---------------------------------------------------------------- WORLD 0:06
B.append(beat(("vo", "Everyone else had thousands."),
              S(cam("mark:plaza", "ws", "crane_up", "high", 28, 200, note="crane reveal: a sea of numbers"),
                A("hero", "idle", at=HERO, facing=0, expr="lonely"),
                crowd=[mill((0, -2, Z), n=32, r=11, seed=3, vip_frac=0.22)]),
              tension=0.32, pad=0.4))
B.append(beat(("vo", "Gold numbers got the velvet rope."),
              S(cam("luxe", "ms", "track", "low", 35, 28, note="low track along the red carpet"),
                A("luxe", "walk", path=[[11.5, 5, Z], [18.2, 5, Z]], expr="smug"),
                crowd=[{"kind": "stare", "center": [13.5, 0.5, Z], "n": 5, "radius": 2.2, "seed": 4, "face_to": "luxe",
                        "look_at": "luxe"}], act="warm"),
              tension=0.32, pad=0.3))
B.append(beat(("vo", "A zero got this."),
              S(cam("hero", "ms", "push_in", "eye", 35, 95, note="profile: he reaches for the door, shopkeeper inside"),
                A("hero", "walk", path=[[-15.2, -3.58, Z], DOOR], t1=0.55, expr="hopeful"),
                A("hero", "reach", t0=0.55, t1=1, expr="hopeful", facing=270),
                A("bram", "idle", at=BRAM_IN, facing=90, expr="neutral"),
                sa={"door": [[0.0, 75], [1.0, 75]]}, act="warm", w=1.1),
              S(cam("bram", "cu", "push_in", "low", 50, 10, note="his eyes go UP to the number"),
                A("bram", "idle", at=BRAM_IN, facing=90, exprs=[[0.0, "neutral"], [0.3, "wary"], [0.6, "disgust"]],
                  look_at=[-18.55, -3.58, 3.1]),
                A("hero", "idle", at=DOOR, facing=270, expr="hopeful"),
                sa={"door": [[0.0, 75], [1.0, 75]]}, act="warm", w=0.9),
              S(cam("hero", "cu", "static_drift", "eye", 35, 95, note="door SLAMS in his face"),
                A("hero", "idle", at=DOOR, facing=270, expr="hopeful", t1=0.32),
                A("hero", "flinch", t0=0.32, t1=1, expr="hurt"),
                A("bram", "idle", at=BRAM_IN, facing=90),
                sa={"door": [[0.0, 75], [0.22, 70], [0.32, -4], [0.37, 3], [0.42, 0]]},
                vfx=[{"kind": "shake", "t": 0.33, "at": DOOR, "shake": 0.5}], act="warm", w=1.0),
              tension=0.4, kind="hit", sfx=[{"kind": "door_slam", "at": 0.73}], pad=0.25, hold=3.9))
B.append(beat(("bram", "We're closed."),
              S(cam("hero", "mcu", "push_in", "eye", 40, 10, amount=0.6, note="he turns back to us, deadpan; OPEN glows behind"),
                A("hero", "idle", at=[-18.0, -3.9, Z], facing=95, exprs=[[0.0, "hurt"], [0.55, "lonely"]]),
                props=[{"kind": "neon", "text": "OPEN", "at": [-19.92, -6.0, 2.0], "rot": 90, "size": 0.55,
                        "color": [1.0, 0.25, 0.35]}],
                sa={"door": [[0.0, 0], [1.0, 0]]}, act="warm", step=2),
              tension=0.35, voice_fx="muffled", pad=0.45, hold=1.6))
B.append(beat(("vo", "Kids backed away."),
              S(cam("kid", "mcu", "pov", "low", 28, 0, subject2="hero", note="kid's POV up at the red 0"),
                A("kid", "idle", at=KID, face_to="hero"), A("hero", "idle", at=[-4.2, -7.6, Z], face_to=KID, expr="hopeful"),
                w=0.9),
              S(cam("kid", "ms", "push_in", "eye", 35, 15),
                A("kid", "back_away", path=[KID, [-6.4, -11.0, Z]], expr="fear"),
                A("mom", "idle", at=[-6.9, -12.4, Z], face_to=KID, expr="wary"),
                A("hero", "idle", at=[-4.2, -7.6, Z], face_to=KID, expr="hurt"), w=1.1),
              tension=0.4, pad=0.2, hold=2.8))
B.append(beat(("crowd", "That's him. The zero."),
              S(cam("hero", "ms", "ots", "eye", 35, 0, subject2=[-2.5, -12.5, 1.9], note="OTS: the whisper group"),
                A("hero", "idle", at=[-1.5, -8.2, Z], face_to=WHISP, expr="lonely"),
                crowd=[{"kind": "whisper", "center": WHISP, "n": 7, "radius": 2.6, "inner": 0.8, "seed": 6,
                        "face_to": [-1.5, -8.2, Z], "look_at": [-1.5, -8.2, 2.1]}]),
              tension=0.42, voice_fx="whisper", pad=0.25, hold=2.2))
B.append(beat(("vo", "And the helpers? They only helped when someone was watching."),
              S(cam("oldman", "ms", "dolly_left", "eye", 28, -35, note="old man drops his groceries; Luxe walks past"),
                A("oldman", "pickup", at=OLD, facing=200, expr="hurt"),
                A("luxe", "walk", path=[[2.2, -5.0, Z], [5.6, -6.8, Z]], t1=0.7, expr="smug"),
                A("luxe", "idle", t0=0.7, t1=1, facing=120, expr="smug"),
                props=[{"kind": "box", "at": [6.4, -8.9, 0.3], "size": [0.6, 0.45, 0.45], "rot": 25}], act="warm"),
              S(cam([7.5, -13.5, 1.6], "mws", "push_in", "low", 28, 0, note="phones go UP"),
                crowd=[{"kind": "watchers", "center": WATCH, "n": 6, "radius": 2.4, "inner": 0.6, "seed": 8,
                        "face_to": OLD, "look_at": [6.0, -8.2, 2.0]}], act="warm"),
              S(cam("luxe", "mcu", "push_in", "low", 40, 25, note="SWOOP: staged help + emote burst, +1 pops"),
                A("luxe", "pickup", at=[5.8, -7.8, Z], facing=150, t1=0.45, expr="determined"),
                A("luxe", "pose", t0=0.45, t1=1, kind="thumbs", expr="smug", facing=170),
                A("oldman", "idle", at=OLD, face_to=[5.8, -7.8, Z], expr="shock"),
                meters={"luxe": [[0.52, 9882, "tick"]]}, act="warm", flare=0.6),
              tension=0.5, kind="hit", sfx=[{"kind": "ding", "at": 0.86}], pad=0.25, hold=4.4))
B.append(beat(("luxe", "You're welcome!"),
              S(cam("luxe", "ms", "orbit_right", "low", 35, 10),
                A("luxe", "pose", at=[5.8, -7.8, Z], facing=170, kind="wave_crowd", expr="happy"),
                crowd=[{"kind": "cheer", "center": WATCH, "n": 6, "radius": 2.4, "inner": 0.6, "seed": 8, "face_to": "luxe"}],
                act="warm"),
              tension=0.45, sfx=[{"kind": "cheer", "at": 0.1}], pad=0.3, hold=1.5))
B.append(beat(("vo", "So why wouldn't mine move?"),
              S(cam([0, -4, 3.06], "cu", "tilt_down", "low", 35, 0, note="from the 0 down to his face"),
                A("hero", "look_up", at=HERO, facing=0, expr="lonely"),
                crowd=[mill((0, -10, Z), n=12, r=9, seed=14)], w=0.8),
              S(cam("hero", "cu", "push_in", "low", 50, -20, note="push in, red pulse on his face"),
                A("hero", "look_up", at=HERO, facing=0, expr="sad"), step=2),
              tension=0.45, pad=0.6, hold=3.0))
# ---------------------------------------------------------------- HIS LIFE 0:25
B.append(beat(("vo", "Every day, I tried."),
              S(cam("hero", "ms", "track", "low", 28, 30, note="he walks into frame, determined"),
                A("hero", "walk", path=[[-7, -6, Z], [-3.9, 0.4, Z]], expr="determined"),
                crowd=[mill((-2, -4, Z), n=14, r=10, seed=21)]),
              tension=0.4, pad=0.2, hold=1.6))
B.append(beat(("hero", "Need a hand?"),
              S(cam("hero", "ms", "push_in", "eye", 35, 80, note="two-shot profile: the offer"),
                A("hero", "offer", at=[-4.0, 0.6, Z], face_to=FOUNT_MOM, expr="hopeful"),
                A("mom", "idle", at=FOUNT_MOM, face_to=[-4.0, 0.6, Z], expr="neutral"),
                carry={"mom": "box"}),
              tension=0.4, pad=0.15, hold=1.4))
B.append(beat(("mom", "From a zero? I'm good."),
              S(cam("mom", "ms", "push_in", "eye", 40, 25),
                A("mom", "idle", at=FOUNT_MOM, face_to=[-4.0, 0.6, Z], exprs=[[0.0, "wary"], [0.4, "disgust"]]),
                A("hero", "offer", at=[-4.0, 0.6, Z], face_to=FOUNT_MOM, expr="hopeful", withdraw=0.5),
                carry={"mom": "box"}, step=2),
              tension=0.42, pad=0.1, hold=1.6))
B.append(beat(None,
              S(cam("mom", "ms", "static_drift", "eye", 28, 70, note="box slips — VANCE catches it, on camera"),
                A("mom", "walk", path=[FOUNT_MOM, [-1.4, 3.6, Z]], t1=0.35, expr="smug"),
                A("mom", "gasp", t0=0.35, t1=1, expr="shock"),
                A("vance", "run", path=[[2.8, 1.0, Z], [-0.6, 3.0, Z]], t1=0.45, expr="determined"),
                A("vance", "pose", t0=0.45, t1=1, kind="thumbs", facing=220, expr="smug"),
                A("luxe", "pose", at=[1.8, -0.8, Z], face_to=[-0.6, 3.0, Z], kind="selfie", expr="happy"),
                carry={"luxe": "phone", "vance": "box"},
                meters={"vance": [[0.55, 8410, "tick"]]}, w=1.0),
              tension=0.5, kind="hit", hold=2.2, sfx=[{"kind": "ding", "at": 0.58}, {"kind": "whoosh", "at": 0.3}]))
B.append(beat(("vance", "A zero can't be trusted, buddy. It's literally over your head."),
              S(cam("vance", "mcu", "push_in", "low", 40, 15, note="smug, points UP at the 0"),
                A("vance", "mock", at=[-0.6, 3.0, Z], face_to=[-4.0, 0.6, Z], expr="smug"),
                carry={"vance": "box"}, w=1.2, step=2),
              S(cam("hero", "mcu", "push_in", "eye", 50, 10, note="the offer hand drops"),
                A("hero", "offer", at=[-4.0, 0.6, Z], face_to=[-0.6, 3.0, Z], expr="hurt", withdraw=0.05),
                crowd=[{"kind": "laugh", "center": [-1, -3, Z], "n": 6, "radius": 3, "seed": 9, "face_to": [-4.0, 0.6, Z]}]),
              tension=0.5, sfx=[{"kind": "laugh", "at": 0.6}], pad=0.3, hold=3.8))
B.append(beat(("vo", "So everyone figured zero meant I'd never helped anyone."),
              S(cam("hero", "ws", "pull_out", "high", 28, 160, note="high angle, he walks away alone"),
                A("hero", "sad_walk", path=[[-4.0, 0.6, Z], [-6.5, -6.5, Z]], expr="lonely"),
                crowd=[mill((0, -2, Z), n=22, r=12, seed=17)]),
              tension=0.35, pad=0.3))
B.append(beat(("guest", "I like your number. It's red."),
              S(cam("hero", "mws", "push_in", "eye", 35, 200, note="from behind: bench, canal, city lights",
                    subject2="guest"),
                A("hero", "sit", at=BENCH_H, facing=0, slump=1.0, seated=True, expr="lonely"),
                A("guest", "walk", path=[[15.2, -23.6, Z], [12.9, -24.8, Z]], t1=0.5, expr="neutral"),
                A("guest", "sit", at=BENCH_G, t0=0.5, t1=1, facing=0, swing=1.0, expr="neutral"), act="cold"),
              S(cam("guest", "mcu", "push_in", "eye", 50, 15),
                A("guest", "sit", at=BENCH_G, facing=0, seated=True, swing=1.0, expr="happy", look_at=[11.4, -25.35, 3.1]),
                A("hero", "sit", at=BENCH_H, facing=0, seated=True, slump=0.6, expr="lonely"), step=2),
              tension=0.32, kind="reveal", pad=0.25, hold=3.2))
B.append(beat(("hero", "You're not scared of it?"),
              S(cam("hero", "cu", "push_in", "eye", 50, 42),
                A("hero", "sit", at=BENCH_H, facing=0, seated=True, slump=0.3, expr="hurt", look_at=[12.65, -25.35, 1.7]),
                A("guest", "sit", at=BENCH_G, facing=0, seated=True, swing=1.0), step=2),
              tension=0.32, pad=0.2, hold=1.5))
B.append(beat(("guest", "Mine's two. I'm new."),
              S(cam("guest", "ms", "orbit_left", "eye", 40, 0, subject2="hero", note="two-shot, both numbers"),
                A("guest", "sit", at=BENCH_G, facing=0, seated=True, swing=1.0, expr="happy", look_at=[11.4, -25.35, 2.0]),
                A("hero", "sit", at=BENCH_H, facing=0, seated=True, exprs=[[0.0, "hurt"], [0.55, "tender"]],
                  look_at=[12.65, -25.35, 1.6]), step=2),
              tension=0.3, kind="reveal", pad=0.6, hold=2.4))
B.append(beat(("vo", "Only one person ever sat with me."),
              S(cam("hero", "ws", "pull_out", "eye", 28, 185, subject2="guest", note="wide from behind, canal glow"),
                A("hero", "sit", at=BENCH_H, facing=0, seated=True, expr="tender"),
                A("guest", "sit", at=BENCH_G, facing=0, seated=True, swing=1.0, expr="happy")),
              tension=0.3, pad=0.7))
# ---------------------------------------------------------------- PLANTED CLUE 0:50
B.append(beat(("vo", "Late at night, when nobody was around…"),
              S(cam([-8, -30, 1.0], "ws", "crane_down", "high", 24, 60, note="empty bridge, mist on the canal"),
                A("hero", "walk", path=[[-8, -22.5, Z], [-8, -26.4, 0.58], BR_KNEEL], expr="neutral"),
                vfx=[{"kind": "dust", "at": [-8, -30, 0.5], "area": 14, "height": 4, "count": 200}]),
              tension=0.25, pad=0.1))
B.append(beat(None,
              S(cam("hero", "ms", "push_in", "low", 35, 40, note="he fixes the broken plank"),
                A("hero", "fix", at=BR_KNEEL, facing=0, expr="determined"),
                sa={"plank_fixed": [0.45, 0.8]}),
              S(cam([-8, -29.75, 0.6], "cu", "static_drift", "low", 50, 330, note="plank snaps flat"),
                A("hero", "fix", at=BR_KNEEL, facing=0, expr="determined"),
                sa={"plank_fixed": [0.1, 0.55]}),
              tension=0.25, hold=2.8, sfx=[{"kind": "thunk", "at": 0.6}, {"kind": "thunk", "at": 0.82}]))
B.append(beat(None,
              S(cam("hero", "ms", "dolly_right", "eye", 35, 80, note="a lost glowing pet toy — he sets it on the post"),
                A("hero", "pickup", at=BR_TOY, facing=10, t1=0.45),
                A("hero", "give", t0=0.45, t1=1, facing=90, expr="tender"),
                props=[{"kind": "toy", "at": [-7.6, -32.85, 0.62], "hide_at": 0.4},
                       {"kind": "toy", "at": [-6.65, -31.0, 1.42], "show_at": 0.78, "rot": 80}]),
              S(cam("hero", "mws", "static_drift", "eye", 40, 150, note="CLUE: the 0 glitches to ∞ for 2 frames",
                    fstop=4.0),
                A("hero", "walk", path=[BR_POST, [-8.0, -26.5, 0.58], [-8.2, -23.0, Z]], expr="calm"),
                zero={"glitch": 0.42, "glitch_frames": 2}, step=1, w=1.1),
              tension=0.28, hold=4.4, kind="reveal", sfx=[{"kind": "glitch_tiny", "at": 0.74, "gain": 0.5}]))
B.append(beat(("vo", "Nobody saw. The number never moved."),
              S(cam("hero", "cu", "pull_out", "low", 50, 180, note="the red 0, unchanged, as he walks away"),
                A("hero", "walk", path=[[-8.2, -23.0, Z], [-8.6, -19.5, Z]], expr="calm"), step=2),
              tension=0.3, pad=0.4))
B.append(beat(("vo", "Theirs only moved on camera."),
              S(cam("vance", "ms", "track", "eye", 35, 40, note="phone up → he 'helps' → +1"),
                A("vance", "walk", path=[CROSS0, CROSS1], expr="smug"),
                A("oldman", "walk", path=[[9.2, -18.9, Z], [15.2, -18.9, Z]], expr="neutral"),
                A("luxe", "pose", at=[12.0, -13.8, Z], face_to=CROSS0, kind="selfie", expr="happy"),
                carry={"luxe": "phone"}, meters={"vance": [[0.5, 8411, "tick"]]}, act="cold", w=1.0),
              S(cam("oldman", "ms", "static_drift", "eye", 35, 20, note="phone DOWN → he lets go mid-street"),
                A("vance", "walk", path=[CROSS1, [18.5, -15.5, Z]], expr="neutral"),
                A("oldman", "stagger", path=[[15.2, -18.9, Z], [15.8, -19.1, Z]], t1=0.5, expr="shock"),
                A("oldman", "tremble", t0=0.5, t1=1, facing=270, expr="hurt"),
                A("luxe", "idle", at=[12.0, -13.8, Z], facing=200, expr="neutral"), act="cold", w=1.0),
              tension=0.5, kind="hit", sfx=[{"kind": "ding", "at": 0.28}], pad=0.3, hold=3.4))
# ---------------------------------------------------------------- DISASTER 1:05
B.append(beat(("vo", "Then the sky turned red."),
              R(cam("hero", "ms", "whip_pan", "low", 24, 10, subject2=SKY, whip_at=0.35, note="whip pan to the burning sky"),
                A("hero", "look_up", at=HERO, facing=0, expr="shock"),
                crowd=[{"kind": "stare", "center": [0, -2, Z], "n": 16, "radius": 9, "seed": 31, "look_at": SKY}],
                vfx=[{"kind": "streaks", "t": 0.0, "n": 10}], flare=1.0),
              R(cam("mark:plaza", "ews", "drone_orbit", "high", 24, 160, note="wide: the whole plaza looks up"),
                crowd=[{"kind": "stare", "center": [0, -2, Z], "n": 26, "radius": 13, "seed": 32, "look_at": SKY}],
                vfx=[{"kind": "streaks", "t": 0.0, "n": 12}, {"kind": "meteor", "at": [40, 60, 0], "t": 1.3, "size": 4}]),
              tension=0.65, kind="braam", sfx=["siren", {"kind": "server_alarm", "at": 0.0}], pad=0.3, hold=3.4,
              banner="⚠ SERVER EVENT: METEOR STORM"))
B.append(beat(None,
              R(cam([6, 8, 22], "ews", "static_drift", "low", 24, 0, pos=[3, -16, 1.2], note="meteor screams in over the plaza"),
                vfx=[{"kind": "meteor", "at": "impact1", "t": 0.95, "size": 3.2, "travel": 30, "from": [0.3, 0.9, 1.0]},
                     {"kind": "streaks", "t": 0.0, "n": 8}], flare=1.4, w=0.9),
              R(cam("mark:impact1", "ews", "static_drift", "eye", 24, 200, note="IMPACT: flash, shockwave, debris",
                    shake=0.4),
                vfx=[{"kind": "impact", "at": "impact1", "t": 0.08, "power": 1.4, "shake": 1.6}],
                crowd=[{"kind": "flee", "center": [0, -4, Z], "n": 22, "radius": 12, "threat": "impact1", "seed": 41,
                        "t0": 0.08, "exits": [[40, 0], [-40, 0], [0, -40]]}], flare=1.4, w=1.3, act="red"),
              R(cam([-18.8, -6, 4.2], "ms", "static_drift", "low", 28, 0, pos=[-11.5, -9.5, 1.6], note="a neon sign tears free and falls"),
                vfx=[{"kind": "sign", "at": [-18.8, -6, 5.8], "t": 0.2, "text": "TOYS", "rot": 90},
                     {"kind": "shake", "t": 0.2, "at": "impact1", "shake": 0.5}],
                crowd=[{"kind": "run_past", "center": [-14, -6, Z], "dir": [0, -1, 0], "n": 5, "spacing": 1.6, "seed": 44}],
                dmg=1.0, w=0.8),
              tension=0.95, kind="hit", sfx=[{"kind": "meteor_fall", "at": 0.0}, {"kind": "impact", "at": 0.33}, {"kind": "crash", "at": 0.78}],
              hold=5.6))
B.append(beat(("crowd", "Run!"),
              R(cam([1, 0, 1.5], "ws", "handheld", "eye", 24, 0, pos=[-1.5, -13, 1.5], shake=0.9, note="stampede toward the lens, handheld"),
                crowd=[{"kind": "flee", "center": [2, 2, Z], "n": 24, "radius": 9, "threat": "impact1", "seed": 47,
                        "delay": [0, 4], "exits": [[0, -40], [-40, -4]]}], dmg=1.0),
              tension=0.9, pad=0.6, hold=2.2))
B.append(beat(("luxe", "Move! This dragon is legendary!"),
              R(cam("luxe", "ms", "track", "low", 28, 20, shake=0.6, note="Luxe sprints, clutching her rare pet"),
                A("luxe", "run", path=[[8, 10, Z], [2.5, 0, Z]], carry_pet=True, expr="scream"),
                carry={"luxe": "pet_dragon"}, meters={"luxe": [[0.3, 0.75, "flicker"]]},
                crowd=[{"kind": "flee", "center": [4, 4, Z], "n": 10, "radius": 6, "threat": "impact1", "seed": 49, "delay": [0, 3]}],
                dmg=1.0),
              tension=0.85, pad=0.2, hold=2.6))
B.append(beat(None,
              R(cam([0, 36, 24], "ews", "static_drift", "low", 20, 0, pos=[42, 30, 1.4], note="side-on: the Spire cracks and leans over the plaza"),
                sa={"spire_lean": [[0.0, 6.0], [0.4, 6.5], [0.55, 10.5], [0.62, 9.6], [1.0, 10.0]], "sirens": True},
                vfx=[{"kind": "dustcloud", "t": 0.5, "at": [0, 36, 0], "radius": 10}, {"kind": "shake", "t": 0.52, "at": "spire", "shake": 0.8},
                     {"kind": "sparks", "t": 0.53, "at": [0, 33, 18], "count": 50}], dmg=1.0, flare=1.0),
              tension=0.9, kind="braam", hold=2.8, sfx=[{"kind": "creak", "at": 0.3}, {"kind": "rumble", "at": 0.45}]))
# ---------------------------------------------------------------- ABANDONMENT 1:25
B.append(beat(("vo", "And the helpers ran."),
              R(cam("vance", "ms", "track", "low", 28, 30, shake=0.5, note="VIPs run past an old man who fell"),
                A("vance", "panic_sprint", path=[[6, 14, Z], [0.5, -2, Z]], carry_pet=True, expr="scream"),
                A("luxe", "run", path=[[8, 15.5, Z], [2.4, -1.0, Z]], carry_pet=True, expr="fear"),
                A("oldman", "pinned", at=[2.6, 7.5, Z], facing=200, expr="pain"),
                carry={"vance": "pet_fox", "luxe": "pet_dragon"},
                meters={"vance": [[0.2, 0.9, "flicker"]], "luxe": [[0.35, 0.95, "flicker"]]}, dmg=1.0),
              R(cam("oldman", "ms", "push_in", "eye", 35, 95, note="on his back, he reaches out; they're gone"),
                A("oldman", "pinned", at=[2.6, 7.5, Z], facing=200, expr="hurt"),
                crowd=[{"kind": "run_past", "center": [2.6, 7.5, Z], "dir": [0, -1, 0], "n": 6, "spacing": 2.0, "seed": 52,
                        "carry": "pets"}], dmg=1.0, w=0.8),
              tension=0.8, pad=0.3, hold=3.2))
B.append(beat(("vance", "Move, zero!"),
              R(cam("hero", "ms", "static_drift", "eye", 35, 60, shake=0.4, note="SHOVE"),
                A("hero", "idle", at=[1.0, 10.0, Z], facing=180, expr="fear", t1=0.3),
                A("hero", "shoved", t0=0.3, t1=0.55, dir=[1, 0.3, 0], dist=1.0),
                A("hero", "fall", t0=0.55, t1=1, expr="pain"),
                A("vance", "run", path=[[-1.6, 14.5, Z], [0.2, 10.6, Z]], t1=0.3, carry_pet=True, expr="angry"),
                A("vance", "shove", t0=0.3, t1=0.55, expr="angry"),
                A("vance", "run", t0=0.55, t1=1, path=[[0.2, 10.6, Z], [1.0, 4.0, Z]], carry_pet=True, expr="angry"),
                carry={"vance": "pet_fox"}, dmg=1.0),
              R(cam("hero", "cu", "push_in", "worm", 28, 0, note="face on the ground; numbers race past; he pushes up"),
                A("hero", "get_up", at=[2.3, 9.6, Z], facing=180, expr="pain", f1=80),
                crowd=[{"kind": "run_past", "center": [3.5, 9.6, Z], "dir": [0, -1, 0], "n": 5, "spacing": 1.4, "seed": 55}],
                dmg=1.0, w=0.8),
              tension=0.9, kind="hit", sfx=[{"kind": "thud", "at": 0.6}], pad=0.35, hold=3.2))
B.append(beat(("guest", "Help! Somebody!"),
              R(cam("hero", "mcu", "rack_focus", "low", 50, 160, subject2="guest", rack_reverse=True,
                    note="over his shoulder: rack focus to the pinned kid"),
                A("hero", "get_up", at=[2.3, 9.6, Z], facing=180, f0=-26, t1=0.55, expr="pain"),
                A("hero", "idle", t0=0.55, t1=1, facing=180, expr="shock"),
                A("guest", "pinned", at=PIN, facing=10, expr="fear"),
                vfx=[{"kind": "beam", "at": PIN, "rot": 15}], dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              R(cam("guest", "mws", "push_in", "high", 28, 300, note="the default kid pinned under the leaning Spire"),
                A("guest", "pinned", at=PIN, facing=10, expr="fear"),
                vfx=[{"kind": "beam", "at": PIN, "rot": 15}, {"kind": "embers", "at": PIN, "area": 16, "count": 200}],
                dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}, flare=0.8),
              tension=0.9, pad=0.5, hold=3.4))
B.append(beat(("vo", "One of them looked right at him."),
              R(cam("vance", "cu", "push_in", "eye", 50, 15, note="Vance slows… looks at the kid… looks at his own number"),
                A("vance", "run", path=[[7.5, 31.5, Z], [5.6, 30.4, Z]], t1=0.3, carry_pet=True, expr="fear"),
                A("vance", "pet_hug", t0=0.3, t1=1, face_to=PIN, exprs=[[0.3, "hurt"], [0.62, "wary"]],
                  look_at=[2.5, 33.4, 0.4]),
                carry={"vance": "pet_fox"}, dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              R(cam("guest", "ms", "static_drift", "high", 35, 270, subject2="vance", note="…and he runs"),
                A("guest", "pinned", at=PIN, facing=10, expr="hurt", look_at=[5.6, 30.4, 1.8]),
                A("vance", "panic_sprint", path=[[5.6, 30.4, Z], [9.5, 19.0, Z]], carry_pet=True, expr="fear"),
                carry={"vance": "pet_fox"}, meters={"vance": [[0.2, 0.8, "flicker"]]},
                vfx=[{"kind": "beam", "at": PIN, "rot": 15}], dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              tension=0.85, kind="hit", pad=0.3, hold=3.6))
B.append(beat(("vo", "Thousands of helpers. They ran right past."),
              R(cam("guest", "ms", "static_drift", "high", 35, 240, note="people run straight past him"),
                A("guest", "pinned", at=PIN, facing=10, expr="hurt"),
                crowd=[{"kind": "run_past", "center": [4.6, 31.0, Z], "dir": [0.2, -1, 0], "n": 7, "spacing": 1.3,
                        "seed": 61, "spread": [2, 14]}],
                vfx=[{"kind": "beam", "at": PIN, "rot": 15}], dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              R(cam("hero", "ews", "static_drift", "top", 28, 0, height=30, note="TOP: one red 0 against a river of thousands"),
                A("hero", "walk", path=[[2.3, 12.0, Z], [2.4, 18.0, Z]], expr="determined"),
                crowd=[{"kind": "run_past", "center": [2.4, 16.0, Z], "dir": [0, -1, 0], "n": 18, "spacing": 1.1,
                        "seed": 63, "spread": [-6, 16]}], dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              R(cam("hero", "cu", "dolly_zoom", "eye", 50, 0, note="DOLLY ZOOM: the decision"),
                A("hero", "idle", at=[2.4, 18.0, Z], facing=180, expr="determined"),
                dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}, engine="cycles", spp=12, step=2),
              tension=0.92, kind="braam", pad=0.3, hold=5.0))
B.append(beat(("hero", "Hang on!"),
              R(cam("hero", "ms", "track", "low", 24, 180, shake=0.7, note="he sprints INTO the danger"),
                A("hero", "sprint", path=[[2.4, 18.0, Z], [1.4, 30.6, Z]], expr="determined"),
                crowd=[{"kind": "run_past", "center": [2.0, 24.0, Z], "dir": [0, -1, 0], "n": 6, "spacing": 1.6, "seed": 66}],
                dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              tension=0.95, pad=0.4, countdown=10, hold=2.0))
# ---------------------------------------------------------------- RESCUE 1:50
B.append(beat(("guest", "Your number… it's not going up."),
              R(cam("hero", "ms", "orbit_left", "low", 35, 30, subject2="guest", shake=0.3, note="he digs"),
                A("hero", "dig", at=DIG, face_to=PIN, expr="strain", toss=True),
                A("guest", "pinned", at=PIN, facing=10, expr="hurt", look_at=[1.2, 32.2, 3.0]),
                vfx=[{"kind": "beam", "at": PIN, "rot": 15}, {"kind": "dust", "at": PIN, "area": 6, "height": 3}],
                dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              tension=0.9, pad=0.15, hold=2.6))
B.append(beat(("hero", "Doesn't matter."),
              R(cam("hero", "cu", "push_in", "low", 50, 20, note="dirt on his face, eyes on the kid"),
                A("hero", "dig", at=DIG, face_to=PIN, expr="determined"),
                vfx=[{"kind": "beam", "at": PIN, "rot": 15}], dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}, step=2),
              tension=0.92, pad=0.3, hold=2.0))
B.append(beat(None,
              R(cam("hero", "ms", "static_drift", "low", 28, 70, shake=0.4, note="LIFT — it slips — he falls back"),
                A("hero", "lift", at=LIFT, face_to=[2.2, 33.8, Z], t1=0.6, grip=0.25, up=0.9, height=0.2),
                A("hero", "fall", t0=0.6, t1=1, expr="pain"),
                A("guest", "pinned", at=PIN, facing=10, expr="fear"),
                vfx=[{"kind": "beam", "at": PIN, "rot": 15, "keys": [[0.0, 0], [0.3, 0], [0.55, 14], [0.62, 0]]},
                     {"kind": "dustcloud", "t": 0.63, "at": PIN, "radius": 3}],
                dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              R(cam(SKY, "ews", "static_drift", "low", 24, 0, pos=[2.5, 22, 1.2], note="second meteor locks on the Spire"),
                vfx=[{"kind": "meteor", "at": [0.5, 36.5, 0], "t": 3.6, "size": 4.0, "travel": 200, "from": [-0.4, -0.6, 1.0], "dist": 420},
                     {"kind": "streaks", "t": 0.0, "n": 6}], dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}, flare=1.2,
                w=0.7),
              tension=0.95, kind="hit", sfx=[{"kind": "crash", "at": 0.36}, {"kind": "meteor_fall", "at": 0.7}], hold=4.6))
B.append(beat(("hero", "Not without you."),
              R(cam("hero", "mcu", "push_in", "low", 40, 35, note="he gets up and lifts again — trembling"),
                A("hero", "get_up", at=[-0.2, 31.6, Z], face_to=PIN, t1=0.35, expr="pain"),
                A("hero", "lift", at=LIFT, face_to=[2.2, 33.8, Z], t0=0.35, t1=1, grip=0.2, up=0.85, height=0.45,
                  expr="strain", relief=True),
                A("guest", "pinned", at=PIN, facing=10, expr="fear", t1=0.8),
                A("guest", "sit_up", t0=0.8, t1=1, slide=[PIN, [2.0, 31.8, Z]], expr="awe"),
                vfx=[{"kind": "beam", "at": PIN, "rot": 15, "keys": [[0.0, 0], [0.45, 0], [0.85, 22], [1.0, 25]]},
                     {"kind": "meteor", "at": [0.5, 36.5, 0], "t": 1.5, "size": 4.0, "travel": 110, "from": [-0.4, -0.6, 1.0], "dist": 230}],
                dmg=1.0, sa={"spire_lean": 10.0, "sirens": True}),
              tension=1.0, pad=0.3, hold=3.2))
B.append(beat(None,
              R(cam("hero", "ws", "pull_out", "low", 24, 300, shake=0.8, note="they run — the meteor hits the Spire behind them"),
                A("hero", "run", path=[[1.6, 31.0, Z], [3.4, 24.6, Z]], t1=0.55, expr="determined"),
                A("hero", "fall", t0=0.55, t1=1, expr="pain"),
                A("guest", "run", path=[[2.4, 31.2, Z], [4.4, 25.1, Z]], t1=0.55, expr="fear"),
                A("guest", "fall", t0=0.56, t1=1, expr="pain"),
                vfx=[{"kind": "meteor", "at": [0.5, 36.5, 0], "t": 0.5, "size": 4.0, "travel": 30, "from": [-0.4, -0.6, 1.0], "dist": 60},
                     {"kind": "impact", "at": [0.5, 36.5, 0], "t": 0.5, "power": 1.6, "shake": 2.0, "crater": False}],
                sa={"spire_lean": [[0.0, 10.0], [0.5, 10.0], [0.75, 24.0], [1.0, 38.0]], "sirens": True},
                dmg=1.0, flare=1.6),
              tension=1.0, kind="hit", sfx=[{"kind": "impact", "at": 0.5}, {"kind": "collapse", "at": 0.6}], hold=3.2))
B.append(beat(("vo", "Nobody was watching. My number still said zero."),
              R(cam("hero", "mcu", "crane_down", "eye", 40, 20, note="dust; the 0 still red"),
                A("hero", "sit_up", at=[3.4, 24.0, Z], facing=200, expr="pain"),
                A("guest", "lie", at=[4.6, 24.6, Z], facing=160),
                vfx=[{"kind": "ash", "at": [3, 24, 0], "area": 14}, {"kind": "dustcloud", "t": 0.0, "at": [2, 30, 0], "radius": 9}],
                dmg=1.0, sa={"spire_lean": 38.0}, step=2),
              tension=0.6, pad=0.5, music_out=True, hold=3.8))
# ---------------------------------------------------------------- TWIST 2:10
B.append(beat(None,
              R(cam("hero", "ms", "push_in", "eye", 40, 30, subject2="guest", note="silence: he pulls the kid close"),
                A("hero", "hug", at=[3.4, 24.0, Z], facing=210, low=1.0, expr="tender"),
                A("guest", "idle", at=[3.0, 23.35, Z], facing=30, expr="awe", look_at=[3.4, 24.0, 2.6]),
                vfx=[{"kind": "ash", "at": [3, 24, 0], "area": 14}], dmg=1.0, sa={"spire_lean": 38.0}, act="red"),
              tension=0.2, hold=2.8, kind="silence"))
B.append(beat(None,
              R(cam([3.4, 24.0, 3.04], "cu", "push_in", "eye", 85, 20, fstop=2.0, amount=0.5,
                    note="SLOW MOTION: crack → glow burst → shards → gold ∞"),
                A("hero", "idle", at=[3.4, 24.0, Z], facing=210, expr="awe", look_at=[3.4, 24.0, 3.6]),
                zero={"flip": [0.14, 0.46, 0.86], "sparks": 160}, flare=1.6, dmg=1.0, sa={"spire_lean": 38.0}, act="gold",
                engine="cycles", spp=16, step=1, exposure=-0.2),
              R(cam("hero", "mcu", "pull_out", "low", 35, 15, note="his face in gold light"),
                A("hero", "idle", at=[3.4, 24.0, Z], facing=210, exprs=[[0.0, "awe"], [0.5, "tender"]],
                  look_at=[3.4, 24.0, 3.6]),
                A("guest", "idle", at=[3.0, 23.35, Z], facing=30, expr="happy", look_at=[3.4, 24.0, 3.3]),
                zero={"inf": True}, dmg=1.0, sa={"spire_lean": 38.0}, act="gold", engine="cycles", spp=12, step=2, w=0.6),
              tension=0.5, kind="swell", hold=6.0, sfx=[{"kind": "crack", "at": 0.1}, {"kind": "flip_burst", "at": 0.3}]))
B.append(beat(("vo", "Turns out, the meter never counted help. It counted audiences."),
              R(cam("hero", "ws", "pull_out", "low", 28, 200, note="the crowd comes back — and stares"),
                A("hero", "stand", at=[3.4, 24.0, Z], facing=210, expr="calm"),
                A("guest", "idle", at=[3.0, 23.35, Z], facing=210, expr="happy"),
                crowd=[{"kind": "stare", "center": [2.5, 16.5, Z], "n": 18, "radius": 6, "inner": 2.0, "seed": 71,
                        "face_to": [3.4, 24.0, Z], "look_at": [3.4, 24.0, 3.0], "sy": 0.6}],
                zero={"inf": True}, dmg=1.0, sa={"spire_lean": 38.0}, act="gold"),
              R(cam("luxe", "mcu", "push_in", "low", 40, 10, subject2="vance", note="VIP numbers glitch red and drain"),
                A("luxe", "pet_hug", at=[1.6, 17.4, Z], face_to=[3.4, 24.0, Z], expr="shock"),
                A("vance", "pet_hug", at=[0.2, 17.0, Z], face_to=[3.4, 24.0, Z], expr="hurt"),
                carry={"luxe": "pet_dragon", "vance": "pet_fox"},
                meters={"luxe": [[0.15, 0.5, "flicker"], [0.5, 4120, "fall_red"], [0.6, 610, "fall_red"], [0.7, 12, "fall_red"]],
                        "vance": [[0.2, 0.55, "flicker"], [0.55, 3900, "fall_red"], [0.66, 77, "fall_red"], [0.76, 3, "fall_red"]]},
                dmg=1.0, sa={"spire_lean": 38.0}, act="gold", flare=0.8),
              tension=0.5, kind="resolve", pad=0.3, hold=4.6, card="THE METER NEVER COUNTED HELP.\nIT COUNTED AUDIENCES.",
              sfx=[{"kind": "glitch", "at": 0.62}]))
B.append(beat(("vo", "Zero didn't mean I never helped."),
              R(cam("hero", "mcu", "orbit_right", "eye", 50, 20, note="gold light on his face"),
                A("hero", "stand", at=[3.4, 24.0, Z], facing=210, expr="tender"),
                A("guest", "idle", at=[3.0, 23.35, Z], facing=210, expr="happy", look_at=[3.4, 24.0, 2.4]),
                zero={"inf": True}, dmg=1.0, sa={"spire_lean": 38.0}, act="gold", step=2),
              tension=0.5, kind="resolve", pad=0.2, hold=2.3, card="ZERO DIDN'T MEAN I NEVER HELPED."))
B.append(beat(("vo", "It meant I never did it for clout."),
              R(cam("mark:plaza", "ws", "crane_up", "low", 24, 20, subject2="hero",
                    note="crane up: the staring crowd, their numbers flickering"),
                A("hero", "stand", at=[3.4, 24.0, Z], facing=210, expr="calm"),
                A("guest", "idle", at=[3.0, 23.35, Z], facing=210, expr="happy"),
                crowd=[{"kind": "stare", "center": [2.5, 16.5, Z], "n": 16, "radius": 6, "inner": 2.0, "seed": 72,
                        "face_to": [3.4, 24.0, Z], "look_at": [3.4, 24.0, 3.0], "flicker": [0.1, 0.6], "sy": 0.6}],
                zero={"inf": True}, dmg=1.0, sa={"spire_lean": 38.0}, act="gold", light_subject="hero"),
              tension=0.5, kind="resolve", pad=0.4, hold=2.6, card="IT MEANT I NEVER DID IT FOR CLOUT."))
# ---------------------------------------------------------------- PAYOFF 2:25
B.append(beat(None,
              S(cam("bram", "mws", "push_in", "eye", 28, 0, pos=[-14.6, -5.2, 1.7], auto_clear=False,
                    note="the shopkeeper opens the door — and holds it"),
                A("bram", "idle", at=[-20.5, -3.58, Z], facing=90, t1=0.3, expr="hurt"),
                A("bram", "offer", t0=0.3, t1=1, facing=90, expr="tender"),
                A("hero", "walk", path=[[-12.0, -3.2, Z], [-16.8, -3.5, Z]], expr="calm"),
                sa={"door": [[0.0, 0], [0.25, 0], [0.5, 88], [0.56, 82], [1.0, 84]], "sky": "red", "damage": 1.0},
                zero={"inf": True}, act="gold", w=1.1),
              S(cam("guest", "ms", "push_in", "low", 28, 180, note="from behind: a small grey hand takes his; warm light ahead"),
                A("guest", "take_hand", at=[-16.2, -4.0, Z], face_to=[-19.0, -3.58, Z], side=1, expr="happy"),
                A("hero", "take_hand", at=[-16.8, -3.5, Z], face_to=[-19.0, -3.58, Z], side=-1, expr="tender", look_down=1),
                sa={"door": [[0.0, 84], [1.0, 84]], "sky": "red", "damage": 1.0}, zero={"inf": True}, act="gold", w=0.9),
              tension=0.35, kind="resolve", hold=3.6))
B.append(beat(("vo", "Help when nobody's watching. That's the only kind that counts."),
              S(cam([-16.8, -3.5, 3.04], "cu", "push_in", "eye", 85, 200, amount=0.8, fstop=1.8,
                    note="last shot: slow push-in on the gold ∞ → hard cut to black"),
                A("hero", "take_hand", at=[-16.8, -3.5, Z], face_to=[-19.0, -3.58, Z], side=-1, expr="tender"),
                A("guest", "take_hand", at=[-16.2, -4.0, Z], face_to=[-19.0, -3.58, Z], side=1, expr="happy"),
                sa={"door": [[0.0, 84], [1.0, 84]], "sky": "red", "damage": 1.0}, zero={"inf": True}, act="gold",
                engine="cycles", spp=12, step=2),
              tension=0.3, kind="resolve", pad=1.1, hold=5.6, hard_cut=True))

FILM["beats"] = B
FILM["beat_map"] = [f"{o[1]} — {o[0]}: {o[2]}" for o in FILM["outline"]]
