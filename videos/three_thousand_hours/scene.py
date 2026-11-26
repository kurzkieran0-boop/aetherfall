"""In This Town, You Get 3,000 Hours Awake - cast, sets, world (Style B), per-frame storm / flood / bell hooks.

World: main street (y=0) with a fountain crossroads at x=0, 20 houses, bakery, school, bell tower, town hall + podium,
a river with levees south of town (y=-42), a north street up to a grassy hill with the old stone church (0, 102, z=9).
Interiors far away: Nora's bedroom (600, 0), her yard under the stars (600, 30), a sleeping house (600, -40),
the classroom (-600, 0).
"""
import json, math, random
from pathlib import Path

HERE = Path(__file__).resolve().parent

CAST = {
    "nora":   dict(shirt="#e0a030", pants="#3e5a8a", hair="#5a3420", skin="#e8c4a0", scale=0.78, kind="kid", start=1962),
    "mom":    dict(shirt="#5f8f7a", pants="#4a4038", hair="#6a4428", skin="#e2be96", scale=0.98, kind="mom", start=1180),
    "mayor":  dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor", start=640),
    "baker":  dict(shirt="#9ec1e6", pants="#9ec1e6", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker",
                   held=["loaf"], start=820),
    "mail":   dict(shirt="#4f6a8a", pants="#3e4652", hair="#1f1a16", skin="#96684a", scale=1.0, kind="mail",
                   held=["env"], label="NORA", start=455),
    "granny": dict(shirt="#a07aa0", pants="#5c4a58", hair="#d8d4cc", skin="#eccdb2", scale=0.92, kind="granny", start=312),
    "k1":     dict(shirt="#4f86c6", pants="#4a4a5a", hair="#2b211a", skin="#c49670", scale=0.76, kind="kid", start=2210),
    "k2":     dict(shirt="#d26f8f", pants="#5a4a6a", hair="#c09060", skin="#eac8a8", scale=0.74, kind="kid", start=2380),
    "k3":     dict(shirt="#6aa84f", pants="#4f4436", hair="#7a4e2a", skin="#a87a58", scale=0.75, kind="kid", start=2290),
    "t1":     dict(shirt="#a3593d", pants="#4f4436", hair="#2b211a", skin="#aa7a58", scale=0.98, kind="plain", start=1305),
    "t2":     dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="plain", start=990),
    "t3":     dict(shirt="#b8964a", pants="#5d5040", hair="#4a3426", skin="#e6c4a0", scale=0.97, kind="plain", start=1640),
    "t4":     dict(shirt="#7d4448", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain", start=760),
    "t5":     dict(shirt="#869468", pants="#4d4234", hair="#c09060", skin="#cca078", scale=1.0, kind="plain", start=1120),
    "t6":     dict(shirt="#6a5aa0", pants="#3e3a48", hair="#1f1a16", skin="#8a5e40", scale=1.0, kind="plain", start=1475),
}
HATS = {"mayor", "baker", "mail"}

# ------------------------------------------------------------------ geography
HX, HY, HR0, HR1, HH = 0.0, 100.0, 12.0, 36.0, 9.0      # hill: centre, plateau radius, base radius, height
BX, BY = 600.0, 0.0          # Nora's bedroom
YX, YY = 600.0, 30.0         # yard under the stars
SX, SY = 600.0, -40.0        # a sleeping house (three beds)
CX, CY = -600.0, 0.0         # classroom
TWX, TWY = 22.0, 12.0        # bell tower
SOUTH = [-70, -60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50]
NORTH = [-70, -60, -10, 10, 34, 44, 54]
NORA_HOUSE = -30
BEDS = (SX - 4.0, SX, SX + 4.0)


def hill_z(x, y):
    r = math.hypot(x - HX, y - HY)
    if r <= HR0:
        return HH
    if r >= HR1:
        return 0.0
    u = (HR1 - r) / (HR1 - HR0)
    return HH * u * u * (3 - 2 * u)


def line(lead, names, x0, y0, deg, gap=1.45, z=0.0, zig=0.25):
    """Single file of walkers behind `lead`, all facing deg."""
    fx, fy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    out = {lead: (x0, y0, deg, "walk", z)}
    for i, n in enumerate(names, 1):
        s = zig if i % 2 else -zig
        out[n] = (x0 - fx * gap * i - fy * s, y0 - fy * gap * i + fx * s, deg, "walk", z)
    return out


LINE_ORDER = ["mom", "baker", "mayor", "granny", "k1", "t1", "t2", "t3", "k2", "t4", "mail", "t6", "k3", "t5"]
LIE = lambda x, y, z=0.62: (x, y, -90, "lie", z)        # head toward +y, lying face up (see apply)

SETS = {
    # ---- daytime town
    "town": {"t3": (-24, 1.6, 0, "walk", 0), "t5": (-4, -1.8, 180, "walk", 0), "t6": (14, 2.2, 0, "walk", 0),
             "t1": (0.0, -1.0, -90, "sit", 0.15), "k1": (-36, -2.0, 0, "run", 0), "t2": (32, -1.6, 180, "walk", 0),
             "nora": (-28, -2.4, 0, "walk", 0), "mail": (-46, -2.4, 0, "walk", 0)},
    "street": {"nora": (-12, -1.8, 20, "idle", 0), "t3": (-20, 1.6, 0, "walk", 0), "t5": (-3, 2.0, 180, "walk", 0),
               "t2": (-17, -2.6, 70, "idle", 0), "k1": (-7, 2.6, -110, "idle", 0), "t6": (-27, -1.0, 0, "walk", 0),
               "mom": (-14.2, -0.6, -40, "idle", 0), "t4": (-9, -2.8, 150, "idle", 0)},
    "fountain": {"t1": (0.0, -1.0, -90, "sit", 0.15), "t3": (-5, -4.2, 10, "walk", 0), "t5": (5.5, 3.6, 200, "walk", 0),
                 "t2": (3.6, -2.4, 160, "idle", 0)},
    "bakery": {"baker": (-20, 8.6, -90, "give:loaf", 0), "t2": (-20, 5.9, 90, "idle", 0), "t3": (-15, 2.0, 180, "walk", 0)},
    "bakery_sleep": {"baker": (-21.3, 7.3, 180, "lie", 0.98), "t2": (-18.0, 5.4, 120, "idle", 0)},
    "mayor_bed": {"mayor": (71.2, 0.0, 180, "sit_talk", 0.36), "t3": (66.2, 1.7, -15, "idle", 0),
                  "t4": (66.0, -1.5, 12, "idle", 0), "t6": (65.0, 0.3, 0, "nod", 0), "granny": (64.6, -2.8, 20, "idle", 0)},
    "mail": {"mail": (-40, -2.0, 0, "walk", 0), "t5": (-28, 2.0, 180, "walk", 0), "k3": (-33, 6.0, -90, "idle", 0)},
    "horses": {"t4": (40.3, -2.4, 0, "sit", 1.38), "t6": (45.7, 2.2, 180, "sit", 1.38), "t2": (37, 2.6, -30, "idle", 0)},
    "classroom": {"k1": (CX - 3.5, CY - 2.3, 90, "sit", 0), "k2": (CX, CY - 2.3, 90, "sit", 0),
                  "k3": (CX + 3.5, CY - 2.3, 90, "sit", 0), "nora": (CX - 1.75, CY - 4.8, 90, "sit", 0),
                  "t5": (CX + 1.2, CY + 3.6, -90, "idle", 0)},
    "school": {"k1": (-44, 7.5, -90, "walk_down", 0), "k2": (-46.5, 8.2, -100, "walk", 0), "k3": (-41.5, 8.0, -75, "walk", 0),
               "t5": (-48, 4.0, 0, "idle", 0)},
    "tease": {"nora": (-38, 4.6, 180, "idle", 0), "k1": (-41.6, 4.2, 0, "point", 0), "k2": (-42.2, 5.8, -20, "laugh", 0),
              "k3": (-41.8, 2.6, 15, "laugh", 0)},
    "nora_intro": {"nora": (-30, -6.4, 90, "idle", 0), "t3": (-36, 1.6, 0, "walk", 0), "t2": (-22, 2.2, 180, "walk", 0)},
    # ---- Nora at night (bedroom / yard)
    "tent": {"nora": (BX + 2.4, BY + 2.7, -90, "read", 0.35)},
    "bed_nora": {"nora": LIE(BX + 2.4, BY + 0.75)},
    "bed_wake": {"nora": (BX + 2.4, BY + 2.6, -90, "idle", 0.35)},
    "tuck": {"nora": LIE(BX + 2.4, BY + 0.75), "mom": (BX + 0.75, BY + 2.0, 0, "sit", 0.0)},
    "yard": {"nora": (YX, YY, -90, "sit", -0.5)},
    # ---- birthday (golden)
    "birthday": {"nora": (-30, -9.3, 90, "idle", 0), "mom": (-28.3, -8.9, 190, "idle", 0),
                 "granny": (-31.8, -8.8, -10, "idle", 0), "k2": (-27.4, -6.4, 160, "idle", 0)},
    # ---- secret night walks (clear night)
    "night_walk": {"nora": (-14, -1.2, 0, "walk", 0)},
    "night_corner": {"nora": (-1.5, 3.6, 90, "walk", 0)},
    # ---- storm
    "flood": {"nora": (-8, -1.5, 0, "walk", 0)},
    "flood_run": {"nora": (10, -1.0, 25, "run", 0)},
    "tower": {"nora": (TWX, TWY - 3.1, -90, "idle", 0)},
    "knock": {"nora": (-9.7, -9.2, -90, "idle", 0)},
    "knock2": {"nora": (10.3, -9.2, -90, "idle", 0)},
    "knock_turn": {"nora": (-9.7, -9.0, 75, "idle", 0)},
    "knock_turn2": {"nora": (10.3, -9.0, 105, "idle", 0)},
    "stand": {"nora": (0.0, -2.0, 90, "idle", 0)},
    "bed_mayor": {"mayor": LIE(BEDS[1], SY - 1.3), "t4": LIE(BEDS[2], SY - 1.3)},
    "bed_baker": {"baker": LIE(BEDS[0], SY - 1.3), "t2": LIE(BEDS[1], SY - 1.3)},
    "bed_family": {"t1": LIE(BEDS[0], SY - 1.3), "t3": LIE(BEDS[1], SY - 1.3), "k2": LIE(BEDS[2], SY - 1.0)},
    "pull": {"t1": (BEDS[0] + 0.4, SY - 0.6, 0, "sit", 0.35), "nora": (BEDS[0] + 2.0, SY - 0.9, 180, "give", 0)},
    # ---- the line
    "line_street": line("nora", LINE_ORDER[:10], -6, -1.0, 0),
    "line_start": line("nora", LINE_ORDER[:3], -12, -6.2, 60),
    "hill": line("nora", LINE_ORDER, 0.0, 74.0, 90),
    "church": {"nora": (0.4, 93.6, 90, "idle", HH), "mom": (-1.1, 92.2, 80, "idle", HH), "baker": (1.6, 91.6, 100, "idle", HH),
               "mayor": (-0.4, 90.6, 90, "idle", HH), "granny": (-2.4, 90.4, 70, "idle", HH), "k1": (2.6, 89.8, 110, "idle", HH),
               "t1": (-3.2, 88.8, 60, "idle", HH), "t2": (0.9, 88.6, 95, "idle", HH), "t3": (3.4, 88.0, 120, "idle", HH),
               "k2": (-1.6, 88.2, 85, "idle", HH)},
    "sunrise": {"nora": (0.6, 89.0, -90, "idle", HH), "mom": (-0.9, 89.6, -60, "hug", HH), "baker": (2.4, 90.6, -100, "idle", HH),
                "mayor": (-2.6, 91.0, -80, "idle", HH), "granny": (4.0, 91.8, -110, "idle", HH), "k1": (-4.2, 90.2, -70, "idle", HH),
                "k2": (3.2, 88.4, -95, "idle", HH), "t1": (-1.8, 92.6, -90, "idle", HH), "t2": (1.2, 92.8, -90, "idle", HH),
                "t6": (-5.4, 92.0, -60, "idle", HH)},
    # ---- epilogue: the whole town plays the game
    "game": line("mayor", ["baker", "nora", "granny", "mom", "k1", "t1", "t2", "k3", "t3", "t6", "k2", "t5"], 8, 1.2, 0),
}
INTERIOR_SETS = {"tent", "bed_nora", "bed_wake", "tuck", "classroom", "bed_mayor", "bed_baker", "bed_family", "pull"}
ROOMS = {s: (BX - 4, BX + 4, BY - 4, BY + 4, 2.9) for s in ("tent", "bed_nora", "bed_wake", "tuck")}
ROOMS.update({s: (SX - 6, SX + 6, SY - 4, SY + 4, 3.0) for s in ("bed_mayor", "bed_baker", "bed_family", "pull")})
ROOMS["classroom"] = (CX - 6, CX + 6, CY - 5, CY + 5, 3.3)
SET_MOOD = {"classroom": "interior", "tuck": "interior"}
STORM_SETS = {"flood", "flood_run", "tower", "knock", "knock2", "knock_turn", "knock_turn2", "stand", "line_street",
              "line_start", "hill", "church", "town_storm", "river"}
SLEEP_SETS = {"bed_mayor", "bed_baker", "bed_family", "bakery_sleep", "fountain", "horses", "bed_nora"}
LINE_SETS = {"line_street", "line_start", "hill", "game"}
SETS["town_storm"] = {"nora": (-8, -1.5, 0, "walk", 0)}
SETS["river"] = {"nora": (-1.0, -30.5, -90, "idle", 0)}

PROPS = {
    "fountain": (0, 0, 1.0, -90), "stall": (-20, 7.3, 1.15, -90), "bell": (TWX, TWY, 13.6, -90),
    "tower": (TWX, TWY, 8.0, -90), "river": (0, -40, 0.6, 90), "breach": (0, -36.2, 0.9, 80),
    "church": (0, 103, 15, -90), "church_door": (0, 95.6, 10.4, -90), "cake": (-30, -8.1, 1.15, 90),
    "chalkboard": (CX, CY + 4.9, 1.9, -90), "school_bell": (-45, 14, 6.6, -90), "nora_house": (NORA_HOUSE, -14, 3.0, 90),
    "door_a": (-10, -10.45, 1.3, 90), "door_b": (10, -10.45, 1.3, 90), "window_b": (BX, BY + 3.9, 1.9, -90),
    "window_s": (SX, SY + 3.9, 1.9, -90), "tent": (BX + 2.4, BY + 2.4, 1.6, -90), "fireflies": (YX + 2, YY - 3, 1.6, -90),
    "dog": ("dog", 0.0, 0.0, (0.5, -90)), "hall_sign": (92 - 7.3, 0, 7.0, 180), "puddle": (-4, -1.5, 0.1, 60),
}
FAR_PROPS = {"tower", "church", "nora_house"}
STRAIGHT_PROPS = set()
DEFAULT_FACE = {}

# fireflies (deterministic, shared by build and apply)
_r = random.Random(3)
FIREFLIES = [(YX + _r.uniform(-9, 9), YY + _r.uniform(-9, 7), _r.uniform(0.4, 2.8)) for _ in range(22)] + \
            [(BX + _r.uniform(-4, 4), BY + _r.uniform(5.5, 10), _r.uniform(0.8, 2.8)) for _ in range(8)]
LAMPS = [(-50, 6.6), (-26, 6.6), (-4, 6.6), (16, 6.6), (40, 6.6), (60, 6.6), (-38, -6.6), (5, -6.6), (28, -6.6)]


# ================================================================== build
def build(kit):
    T, B = kit.town, kit.blocks
    import bpy
    rnd = random.Random(21)
    T.ground(roads=[(-10, 0, 146, 8), (0, 37, 7, 58)], plazas=[(76, 0, 26, 26), (0, 0, 18, 16)],
             keep_clear=[(-40, 40, 60, 140), (-160, 160, -52, -34)])
    walls = ["#c8b08a", "#b9a07c", "#a88f72", "#cdbb98", "#9fa38a", "#b59a86", "#8fa0a8", "#c2a88a"]
    roofs = ["#7a4a36", "#6a5040", "#5d4a3c", "#80563c", "#5a5f62", "#6e4434"]
    for i, x in enumerate(SOUTH):
        if x == NORA_HOUSE:
            B.house("nora_house", x, -14, 90, w=7, d=7, h=3.8, wall="#8b9aa6", roof="#5e4c3e")
        else:
            B.house(f"house_s{i}", x, -14, 90, w=6.6, d=7, h=3.3 + (i % 3) * 0.4, wall=walls[i % 8], roof=roofs[i % 6])
    for i, x in enumerate(NORTH):
        B.house(f"house_n{i}", x, 14, -90, w=6.8, d=7, h=3.4 + (i % 2) * 0.5, wall=walls[(i + 3) % 8], roof=roofs[(i + 2) % 6])
    T.bakery(-20, 14)
    T.school(-45, 14)
    T.town_hall(92, 0, podium=(76.6, 0))
    for k, (a, b) in enumerate([((-74, -9.6), (-66, -9.6)), ((-56, -9.6), (-54, -9.6)), ((44, -9.6), (56, -9.6)),
                                ((-76, 9.6), (-64, 9.6)), ((38, 9.6), (60, 9.6)), ((-34, -9.6), (-26, -9.6))]):
        B.fence(f"fence{k}", a, b)
    T.utilities(xs=(-66, -45, -25, -5, 15, 35, 55), y=-6.4, lamps_x=(), barrels_at=[
        (-25.5, 8.6), (-26.3, 9.3), (-14, 8.4), (6, 8.8), (6.8, 9.5), (30, -8.6), (-55, 8.8), (48, 8.4), (70, -8), (70.8, -8.7)])
    for i, (lx, ly) in enumerate(LAMPS):
        B.lamp(f"lamp{i}", lx, ly)
        T.emissive(bpy.data.objects[f"lamp{i}_glow"], 5.0)
        lt = T.point_light(f"lamp{i}_light", (lx, ly - 0.4 * (1 if ly > 0 else -1), 3.9), 450, (1.0, 0.78, 0.5))
        lt.data.shadow_soft_size = 0.3
    T.trees([(-80, 24), (-58, 28), (-30, 30), (-12, 34), (14, 32), (30, 26), (60, 26), (-80, -24), (-46, -24),
             (-15, -25), (16, -25), (45, -24), (70, -22), (88, 22), (-90, 6)], style="B")
    T.sign("tower_sign", TWX + 3.2, 8.4, -90, "BELL\nTOWER", w=2.2, h=1.0, size=0.3, post=2.2)
    # ---- fountain (crossroads)
    ring = [(1.0, 0.6, 0.7, 2.4 * math.cos(a), 2.4 * math.sin(a), 0.35, "#9a9488", a + math.pi / 2)
            for a in [k * 2 * math.pi / 16 for k in range(16)]]
    ring += [(0.8, 0.8, 2.0, 0, 0, 1.0, "#9a9488"), (1.6, 1.6, 0.25, 0, 0, 2.05, "#8f877a"), (0.4, 0.4, 0.6, 0, 0, 2.4, "#9a9488")]
    B.multibox("fountain_stone", ring, loc=(0, 0, 0))
    B.multibox("fountain_water", [(4.4, 4.4, 0.1, 0, 0, 0.5, "#3f6f8f")])
    jet = B.multibox("fountain_jet", [(0.12, 0.12, 0.6, 0, 0, 2.9, "#cfe6f0"), (1.2, 1.2, 0.08, 0, 0, 2.25, "#cfe6f0")])
    T.emissive(jet, 0.6)
    # ---- bell tower
    tw = [(4.6, 4.6, 12, TWX, TWY, 6, "#9a9488"), (5.2, 5.2, 0.4, TWX, TWY, 0.2, "#7c7a74"),
          (5.0, 5.0, 0.4, TWX, TWY, 12.1, "#7c7a74"), (1.4, 0.2, 2.6, TWX, TWY - 2.35, 1.3, "#5b4030"),
          (1.0, 0.2, 1.4, TWX, TWY - 2.35, 7.5, "#3d4a55"), (5.0, 5.0, 0.4, TWX, TWY, 15.6, "#7c7a74")]
    tw += [(0.8, 0.8, 3.4, TWX + sx * 1.9, TWY + sy * 1.9, 13.9, "#9a9488") for sx in (-1, 1) for sy in (-1, 1)]
    B.multibox("bell_tower", tw)
    B.poly("bell_tower_roof", [(TWX - 2.7, TWY - 2.7, 15.8), (TWX + 2.7, TWY - 2.7, 15.8), (TWX + 2.7, TWY + 2.7, 15.8),
                               (TWX - 2.7, TWY + 2.7, 15.8), (TWX, TWY, 19.2)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], "#7a4a36")
    piv = B.empty("bell_pivot", (TWX, TWY, 15.1))
    bell = [(0.7, 0.7, 0.35, 0, 0, -0.35, "#b08a3a"), (1.0, 1.0, 0.45, 0, 0, -0.75, "#b08a3a"), (1.3, 1.3, 0.45, 0, 0, -1.15, "#b08a3a"),
            (1.55, 1.55, 0.2, 0, 0, -1.45, "#9a7430"), (0.22, 0.22, 0.6, 0, 0, -1.55, "#4a3a2a"), (0.36, 0.36, 0.25, 0, 0, -1.9, "#4a3a2a"),
            (0.25, 0.25, 0.3, 0, 0, -0.05, "#5e4a38")]
    B.multibox("bell", bell, parent=piv)
    B.cyl("bell_rope", 0.04, 13.0, (TWX + 0.85, TWY - 2.45, 0.9), "#c8b080", seg=6)
    B.cyl("bell_rope_grip", 0.07, 0.6, (TWX + 0.85, TWY - 2.45, 0.9), "#a03a30", seg=6)
    # ---- river with levees + breach
    B.multibox("river_water", [(320, 11, 0.1, 0, -42, 0.12, "#3f6f8f")])
    B.multibox("river_bed", [(320, 12, 0.05, 0, -42, 0.02, "#6e553e")])
    lv = [(146, 0.9, 1.1, -77, -36.2, 0.55, "#9a9488"), (146, 0.9, 1.1, 77, -36.2, 0.55, "#9a9488"),
          (320, 0.9, 1.1, 0, -47.8, 0.55, "#9a9488")]
    lv += [(rnd.uniform(0.5, 1.1), rnd.uniform(0.5, 1.0), rnd.uniform(0.3, 0.7), rnd.uniform(-5, 5), -36.2 + rnd.uniform(-1.5, 2.5),
            0.2, "#7c7a74", rnd.uniform(0, 3)) for _ in range(14)]
    B.multibox("levees", lv)
    spill = B.multibox("breach_spill", [(7.6, 5.0, 0.12, 0, -33.8, 0.45, "#3f6f8f"), (7.0, 0.5, 0.5, 0, -36.2, 0.9, "#dbe8f0"),
                                        (6.0, 0.8, 0.2, 0, -31.6, 0.4, "#dbe8f0")])
    spill.rotation_euler.x = 0.03
    # ---- horses + dog
    for k, (hx, hy, hf) in enumerate(((40.0, -2.4, 0), (46.0, 2.2, 180))):
        col = ("#7a5636", "#d8ccb0")[k]
        hb = [(2.2, 0.8, 0.9, 0, 0, 1.4, col), (0.55, 0.6, 1.0, 1.15, 0, 2.0, col), (0.9, 0.5, 0.45, 1.6, 0, 2.45, col),
              (0.25, 0.55, 0.55, 1.0, 0, 2.3, "#3a2a1e"), (0.15, 0.15, 0.9, -1.15, 0, 1.1, "#3a2a1e"),
              (0.9, 0.85, 0.12, -0.2, 0, 1.88, "#8a3a30"), (0.12, 0.12, 0.25, 1.75, 0.15, 2.8, col), (0.12, 0.12, 0.25, 1.75, -0.15, 2.8, col)]
        hb += [(0.24, 0.24, 1.0, sx, sy, 0.5, col) for sx in (-0.85, 0.85) for sy in (-0.28, 0.28)]
        hb += [(0.06, 0.04, 0.06, 1.95, sy, 2.55, "#1a1410") for sy in (-0.2, 0.2)]
        B.multibox(f"horse{k}", hb, loc=(hx, hy, 0), rot_z=math.radians(hf))
    dog = B.empty("dog", (0, 0, -100))
    db = [(0.75, 0.32, 0.32, 0, 0, 0.5, "#c8a070"), (0.32, 0.3, 0.3, 0.45, 0, 0.75, "#c8a070"), (0.16, 0.18, 0.14, 0.66, 0, 0.7, "#e8d8b8"),
          (0.06, 0.06, 0.06, 0.74, 0, 0.74, "#1a1410"), (0.1, 0.06, 0.18, 0.42, 0.13, 0.95, "#8a6040"), (0.1, 0.06, 0.18, 0.42, -0.13, 0.95, "#8a6040"),
          (0.32, 0.07, 0.07, -0.48, 0, 0.72, "#c8a070", 0), (0.04, 0.04, 0.04, 0.6, 0.1, 0.82, "#1a1410"), (0.04, 0.04, 0.04, 0.6, -0.1, 0.82, "#1a1410"),
          (0.25, 0.34, 0.06, 0.15, 0, 0.67, "#a03a30")]
    db += [(0.1, 0.1, 0.36, sx, sy, 0.18, "#c8a070") for sx in (-0.28, 0.28) for sy in (-0.1, 0.1)]
    B.multibox("dog_body", db, parent=dog)
    # ---- mayor's bed on the plaza + attendee chairs
    bed = [(3.0, 1.8, 0.45, 70, 0, 0.32, "#6a4a30"), (2.9, 1.7, 0.25, 70, 0, 0.7, "#e8e0cc"), (1.9, 1.75, 0.12, 69.5, 0, 0.86, "#a3302a"),
           (0.5, 1.2, 0.2, 71.15, 0, 0.9, "#f0ece4"), (0.15, 1.8, 1.5, 71.6, 0, 0.95, "#6a4a30"), (0.15, 1.8, 0.8, 68.45, 0, 0.6, "#6a4a30")]
    bed += [(0.9, 0.6, 0.06, 69.0, 0.2, 0.95, "#efe5c8", 0.3)]     # papers on the blanket
    B.multibox("mayor_bed", bed)
    T.sign("meeting_sign", 66.0, 4.6, -100, "TOWN\nMEETING", w=2.4, h=1.1, size=0.3, post=1.8, board="#4f6b4a")
    # ---- birthday table + cake (in front of Nora's house)
    tb = [(2.6, 1.1, 0.1, NORA_HOUSE, -8.1, 0.88, "#7a5534")]
    tb += [(0.1, 0.1, 0.86, NORA_HOUSE + sx, -8.1 + sy, 0.43, "#5e4028") for sx in (-1.2, 1.2) for sy in (-0.45, 0.45)]
    tb += [(2.8, 1.2, 0.03, NORA_HOUSE, -8.1, 0.94, "#f0e8e0")]
    B.multibox("bday_table", tb)
    B.cyl("cake", 0.38, 0.32, (NORA_HOUSE, -8.1, 0.95), "#f2d8e0", seg=14)
    B.cyl("cake_top", 0.39, 0.05, (NORA_HOUSE, -8.1, 1.27), "#d86a8a", seg=14)
    cand = B.multibox("candles", [(0.04, 0.04, 0.14, NORA_HOUSE + 0.16 * math.cos(a), -8.1 + 0.16 * math.sin(a), 1.37, "#f0f0ff")
                                  for a in (0, 2.1, 4.2)])
    fl = B.multibox("candle_flames", [(0.05, 0.05, 0.07, NORA_HOUSE + 0.16 * math.cos(a), -8.1 + 0.16 * math.sin(a), 1.48, "#ffc050")
                                      for a in (0, 2.1, 4.2)])
    T.emissive(fl, 8.0)
    T.text("bday_banner_t", "HAPPY BIRTHDAY", (NORA_HOUSE, -10.19, 3.08), math.pi, 0.28, "#a3302a")
    B.multibox("bday_banner", [(3.6, 0.06, 0.5, NORA_HOUSE, -10.27, 3.08, "#f0e8d2")])
    # ---- school lullaby notes
    for k in range(4):
        nb = [(0.32, 0.12, 0.24, 0, 0, 0, "#f4f0e6"), (0.06, 0.06, 0.8, 0.13, 0, 0.4, "#f4f0e6"), (0.25, 0.06, 0.08, 0.24, 0, 0.78, "#f4f0e6")]
        n_ob = B.multibox(f"note{k}", nb, loc=(-47 + k * 1.4, 9.0 - k * 0.3, 7.5 + k * 0.6))
        T.emissive(n_ob, 1.5)
    # ---- hill, path, church, fences, trees on the slope
    rings = [0, 3, 6, 9, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 37.5]
    na = 56
    vs, fs = [], []
    for r in rings:
        for k in range(na):
            a = 2 * math.pi * k / na
            x, y = HX + r * math.cos(a), HY + r * math.sin(a)
            vs.append((x, y, hill_z(x, y) - (0.05 if r > HR1 else 0) + 0.01))
    for i in range(len(rings) - 1):
        for k in range(na):
            a0, a1 = i * na + k, i * na + (k + 1) % na
            fs.append((a0, a1, a1 + na, a0 + na))
    B.poly("hill", vs, fs, "#8c8a5c")
    pv, pf = [], []
    ys = [60 + 1.0 * k for k in range(37)]
    for y in ys:
        for x in (-1.7, 1.7):
            pv.append((x, y, hill_z(x, y) + 0.06))
    for k in range(len(ys) - 1):
        pf.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
    B.poly("hill_path", pv, pf, "#a68a66")
    for k, y in enumerate(range(66, 88, 3)):
        for sx in (-2.6, 2.6):
            z = hill_z(sx, y)
            B.multibox(f"hfence{k}_{sx}", [(0.16, 0.16, 1.1, 0, 0, 0.55, "#7d6448"), (0.08, 3.0, 0.12, 0, -1.5, 0.85, "#8a7052")],
                       loc=(sx, y, z))
    for k, (tx, ty) in enumerate([(-9, 76), (8, 72), (-14, 92), (13, 96), (-10, 110), (12, 112), (-20, 84), (20, 86)]):
        z = hill_z(tx, ty)
        h = 2.6 + (k % 3) * 0.5
        B.cyl(f"htree{k}", 0.3, h, (tx, ty, z), "#5c4634", seg=7)
        B.multibox(f"htree{k}_top", [(3.2, 3.2, 2.0, 0, 0, h + 0.9, "#5f6b3e"), (2.4, 2.4, 1.6, 0.2, -0.1, h + 2.3, "#6a7244")],
                   loc=(tx, ty, z), rot_z=k * 0.7)
    cz = HH
    ch = [(9, 12, 6.5, 0, 103, cz + 3.25, "#7c7a74"), (9.6, 12.6, 0.5, 0, 103, cz + 0.25, "#6d6252"),
          (3.4, 3.4, 12.5, 0, 96.6, cz + 6.25, "#9a9488"), (1.6, 0.2, 2.9, 0, 94.85, cz + 1.45, "#5b4030"),
          (2.2, 0.25, 0.3, 0, 94.8, cz + 3.0, "#6e5e52"), (1.0, 0.2, 1.6, 0, 94.85, cz + 7.6, "#3d4a55"),
          (0.2, 0.1, 1.2, 0, 94.8, cz + 10.6, "#e8e0cc"), (0.8, 0.1, 0.2, 0, 94.8, cz + 10.8, "#e8e0cc")]
    for wy in (99.5, 103, 106.5):
        for sx in (-1, 1):
            ch += [(0.2, 1.0, 2.0, sx * 4.55, wy, cz + 3.5, "#3d4a55"), (0.25, 1.2, 0.2, sx * 4.6, wy, cz + 4.6, "#e8e0cc")]
    B.multibox("church", ch)
    B.poly("church_roof", [(-5, 96.6, cz + 6.4), (5, 96.6, cz + 6.4), (5, 109.4, cz + 6.4), (-5, 109.4, cz + 6.4),
                           (0, 96.6, cz + 10.2), (0, 109.4, cz + 10.2)], [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5)], "#4a4440")
    B.poly("church_spire", [(-1.9, 94.7, cz + 12.4), (1.9, 94.7, cz + 12.4), (1.9, 98.5, cz + 12.4), (-1.9, 98.5, cz + 12.4),
                            (0, 96.6, cz + 17.5)], [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], "#5a5f62")
    T.sign("church_sign", 3.4, 92.0, -90, "OLD CHURCH", w=2.6, h=0.6, size=0.26, post=1.6)
    bpy.data.objects["church_sign_post"].location.z += HH
    bpy.data.objects["church_sign_board"].location.z += HH
    for o in bpy.data.objects:
        if o.name.startswith("church_sign_txt"):
            o.location.z += HH
    # ---- flood water (translucent) + puddles + rain + lightning windows
    fm = bpy.data.materials.new("FLOOD")
    fm.use_nodes = True
    nt = fm.node_tree
    bs = nt.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = B.srgb("#2f6488") + [1]
    bs.inputs["Roughness"].default_value = 0.12
    bs.inputs["Alpha"].default_value = 0.78
    bs.inputs["Emission Color"].default_value = B.srgb("#3a6e96") + [1]
    bs.inputs["Emission Strength"].default_value = 0.25
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.4
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    try:
        fm.surface_render_method = "DITHERED"
    except Exception:
        pass
    try:
        fm.blend_method = "HASHED"
    except Exception:
        pass
    B.poly("flood", [(-130, -48, 0), (130, -48, 0), (130, 84, 0), (-130, 84, 0)], [(0, 1, 2, 3)], fm, loc=(0, 0, -5))
    pud = [(rnd.uniform(1.5, 4), rnd.uniform(1, 2.5), 0.02, rnd.uniform(-60, 60), rnd.uniform(-3.5, 3.5), 0.05, "#3f6f8f",
            rnd.uniform(0, 3)) for _ in range(26)]
    pud += [(rnd.uniform(1, 2.5), rnd.uniform(1, 2), 0.02, rnd.uniform(-2, 2), rnd.uniform(12, 60), 0.05, "#3f6f8f") for _ in range(8)]
    B.multibox("puddles", pud)
    streaks = []
    for _ in range(1500):
        x, y, z = rnd.uniform(-20, 20), rnd.uniform(-20, 20), rnd.uniform(0, 12)
        for dz in (0, 12):
            streaks.append((0.022, 0.022, 0.75, x, y, z + dz, "#bcd8ff"))
    rain = B.multibox("rain", streaks)
    rain.data.materials[0] = B.mat("#bcd8ff", emit=1.6)
    far = []
    for _ in range(1300):
        x, y, z = rnd.uniform(-75, 75), rnd.uniform(-75, 75), rnd.uniform(0, 14)
        for dz in (0, 14):
            far.append((0.07, 0.07, 2.2, x, y, z + dz, "#bcd8fe"))
    rf = B.multibox("rain_far", far)
    rf.data.materials[0] = B.mat("#bcd8fe", emit=1.2)
    for nm, (wx, wy) in (("win_glow_b", (BX, BY + 3.9)), ("win_glow_s", (SX, SY + 3.9))):
        g = B.multibox(nm, [(1.3, 0.03, 0.9, wx, wy, 1.9, "#9fc1e9")])
        g.data.materials[0] = B.mat("#9fc1e9", emit=0.4)
    # ---- Nora's bedroom (+ tent, flashlight, book) and her yard
    T.bedroom(BX, BY, wall="#a8b4c0")
    tent = [(2.0, 2.4, 0.1, 0, 0, 2.5, "#7a8fb0"), (0.1, 2.4, 1.7, -1.0, 0, 1.65, "#7a8fb0"), (0.1, 2.4, 1.7, 1.0, 0, 1.65, "#7a8fb0"),
            (2.0, 0.1, 1.7, 0, 1.2, 1.65, "#7a8fb0"), (0.6, 0.12, 0.35, -0.65, -1.15, 2.3, "#7a8fb0", 0.3)]
    B.multibox("tent", tent, loc=(BX + 2.4, BY + 2.2, 0))
    fl_ob = B.multibox("flashlight", [(0.08, 0.26, 0.08, 0, 0, 0, "#3a3a44"), (0.11, 0.06, 0.11, 0, 0.14, 0, "#d8d8d0")])
    fl_ob.location = (0, 0, -100)
    lens = B.multibox("flashlight_lens", [(0.08, 0.02, 0.08, 0, 0.175, 0, "#fff6d8")], parent=fl_ob)
    T.emissive(lens, 12.0)
    T.point_light("flash_light", (0, 0, -100), 6, (1.0, 0.92, 0.75))
    for nm in ("nora_book", "mom_book"):
        bk = B.multibox(nm, [(0.42, 0.3, 0.06, 0, 0, 0, "#8a3a30"), (0.38, 0.28, 0.07, 0, 0, 0.005, "#f0e8d6")])
        bk.location = (0, 0, -100)
    B.multibox("bed_chair", [(0.7, 0.7, 0.1, BX + 0.75, BY + 2.0, 0.5, "#6a4a30"), (0.1, 0.7, 0.9, BX + 0.4, BY + 2.0, 0.95, "#6a4a30")]
               + [(0.08, 0.08, 0.5, BX + 0.75 + sx, BY + 2.0 + sy, 0.25, "#5e4028") for sx in (-0.3, 0.3) for sy in (-0.3, 0.3)])
    B.multibox("bedroom_shelf", [(1.6, 0.4, 0.08, BX - 1.8, BY + 3.75, 1.5, "#6a4a30")] +
               [(0.12, 0.25, 0.32, BX - 2.4 + 0.15 * k, BY + 3.75, 1.7, ("#a3593d", "#4f6a8a", "#6aa84f", "#b8964a")[k % 4]) for k in range(8)])
    stars = [(s, s, s, YX + rnd.uniform(-60, 60), YY + rnd.uniform(-20, 80), rnd.uniform(28, 60), "#fffbe8")
             for s in [rnd.uniform(0.15, 0.4) for _ in range(380)]]
    st = B.multibox("stars", stars)
    st.data.materials[0] = B.mat("#fffbe8", emit=9.0)
    for k, (fx, fy, fz) in enumerate(FIREFLIES):
        f = B.multibox(f"ff{k}", [(0.07, 0.07, 0.07, 0, 0, 0, "#e8ff70")], loc=(fx, fy, fz))
        f.data.materials[0] = B.mat("#e8ff70", emit=25.0)
    B.fence("yard_fence", (YX - 9, YY + 8), (YX + 9, YY + 8))
    B.fence("yard_fence2", (YX + 9, YY + 8), (YX + 9, YY - 9))
    B.house("yard_house", YX - 2, YY - 12, 90, w=8, d=6, h=3.6, wall="#8b9aa6", roof="#5e4c3e")
    for k, (tx, ty) in enumerate([(YX - 8, YY + 4), (YX + 7, YY + 5)]):
        B.cyl(f"ytree{k}", 0.3, 2.8, (tx, ty, 0), "#5c4634", seg=7)
        B.multibox(f"ytree{k}_top", [(3.0, 3.0, 2.0, 0, 0, 3.7, "#5f6b3e"), (2.2, 2.2, 1.4, 0, 0, 5.0, "#6a7244")], loc=(tx, ty, 0))
    # ---- sleeping house (three beds)
    T.room("home", SX, SY, W=12, D=8, floor="#8a6a4a", wall="#c9b48e")
    for k, bx in enumerate(BEDS):
        cover = ("#7a8fb0", "#a3593d", "#6aa84f")[k]
        B.multibox(f"home_bed{k}", [(1.8, 3.0, 0.5, bx, SY, 0.35, "#6a4a30"), (1.7, 2.9, 0.25, bx, SY, 0.72, "#e8e0cc"),
                                    (1.7, 1.9, 0.12, bx, SY - 0.45, 0.86, cover), (1.2, 0.5, 0.18, bx, SY + 1.15, 0.9, "#f0ece4"),
                                    (1.8, 0.15, 1.2, bx, SY + 1.55, 0.9, "#6a4a30")])
    B.multibox("home_props", [(1.4, 0.06, 1.0, SX, SY + 3.97, 1.9, "#8fb0c4"), (1.6, 0.08, 0.1, SX, SY + 3.95, 1.35, "#e8e0cc"),
                              (0.6, 0.6, 0.7, SX - 2, SY + 1.6, 0.35, "#8a6a4a"), (0.6, 0.6, 0.7, SX + 2, SY + 1.6, 0.35, "#8a6a4a"),
                              (3.0, 2.0, 0.02, SX, SY - 2.6, 0.11, "#7d4b40")])
    T.point_light("home_lamp", (SX - 2, SY + 1.6, 1.4), 18, (1.0, 0.8, 0.55))
    # ---- classroom
    T.room("class", CX, CY, W=12, D=10, H=3.4, floor="#8a6a4a", wall="#c2a88a")
    B.multibox("chalkboard", [(5.2, 0.1, 2.0, CX, CY + 4.93, 1.9, "#2f4a3a"), (5.4, 0.14, 0.12, CX, CY + 4.9, 0.85, "#6a4a30")])
    T.text("chalk1", "2 + 2 = 22", (CX - 0.9, CY + 4.86, 2.3), 0, 0.32, "#f0f0e8")
    T.text("chalk2", "HOMEWORK  ZZZ", (CX + 0.4, CY + 4.86, 1.55), 0, 0.26, "#f0f0e8")
    desks = []
    for dx in (-3.5, 0, 3.5):
        for row in (0, 1):
            dy = CY - 1.5 - row * 2.5
            desks += [(1.3, 0.8, 0.08, CX + dx + (-1.75 if row else 0), dy, 0.74, "#7a5534"),
                      (0.08, 0.7, 0.72, CX + dx + (-1.75 if row else 0) - 0.55, dy, 0.36, "#5e4028"),
                      (0.08, 0.7, 0.72, CX + dx + (-1.75 if row else 0) + 0.55, dy, 0.36, "#5e4028"),
                      (0.5, 0.36, 0.01, CX + dx + (-1.75 if row else 0), dy - 0.1, 0.79, "#f4f0e6")]
    desks += [(0.75, 0.75, 0.1, CX + dx, CY - 2.3, 0.5, "#6a4a30") for dx in (-3.5, 0, 3.5)]
    desks += [(0.75, 0.75, 0.1, CX - 1.75, CY - 4.8, 0.5, "#6a4a30")]
    B.multibox("desks", desks)
    for k, dx in enumerate((-3.5, 0, 3.5)):
        T.text(f"redx{k}", "X", (CX + dx + 0.05, CY - 1.62, 0.8), 0, 0.22, "#c83a30").rotation_euler.x = 0.0
    T.point_light("class_lamp", (CX, CY - 1, 3.1), 260, (1.0, 0.9, 0.75))
    # ---- Nora's stone eyelids (parented to her head at render time)
    for side in ("L", "R"):
        lid = B.multibox(f"nora_lid{side}", [(0.13, 0.04, 0.11, 0, 0, 0, "#8a8780"), (0.13, 0.045, 0.015, 0, 0, -0.01, "#5a5852")])
        lid.location = (0, 0, -100)


# ================================================================== per-frame hooks
_TL = {}
FLOOD = {"s15": (0.0, 0.12), "s16": (0.12, 0.45), "s17": (0.45, 0.5), "s18": (0.5, 0.56), "s19": (0.56, 0.62),
         "s20": (0.62, 0.74), "s21": (0.74, 0.8), "s22": (0.8, 0.83)}
STORM = {f"s{k:02d}" for k in range(15, 29)}


def _timeline():
    if not _TL:
        try:
            tl = json.loads((HERE / "build" / "timeline.json").read_text())
            _TL["s"] = {s["id"]: s for s in tl["sentences"]}
            _TL["order"] = [s["id"] for s in tl["sentences"]]
            stone = [w["start"] for w in _TL["s"].get("s22", {}).get("words", []) if w["norm"] == "stone"]
            _TL["stone"] = stone[0] if stone else 1e9
        except Exception:
            _TL.update(s={}, order=[], stone=1e9)
    return _TL


def _sidx(sid):
    try:
        return int(sid[1:]) if sid.startswith("s") else int(sid[1:]) + 0
    except Exception:
        return 0


def flood_level(sid, gt):
    tl = _timeline()
    k = _sidx(sid) if sid.startswith("s") else 0
    if sid in FLOOD:
        a, b = FLOOD[sid]
        s = tl["s"].get(sid)
        u = 0.5 if not s else min(1, max(0, (gt - s["start"]) / max(0.1, s["end"] - s["start"])))
        return a + (b - a) * u
    if sid.startswith("s") and 23 <= k <= 28:
        return 0.85
    return 0.0


def _attach(stage, name, parent, loc, rot=(0, 0, 0)):
    ob = stage.ob[name]
    par = stage.ob[parent]
    if ob.parent != par:
        ob.parent = par
        ob.matrix_parent_inverse.identity()
    ob.location = loc
    ob.rotation_euler = rot


def apply(stage, sh, t, gt):
    from render import lerp, smooth, lin
    ob = stage.ob
    sid = sh.get("sentence", "")
    k = _sidx(sid) if sid.startswith("s") else 0
    sset = sh["set"]
    actors = stage.actors_for(sh)
    acts = sh.get("acts", {})
    light = getattr(stage.scene, "SET_MOOD", {}).get(sset, sh.get("light", "day"))
    night = light == "night"
    storm = sid in STORM and sset not in INTERIOR_SETS
    # ---- lamp lights only at night / dusk in town
    for i in range(len(LAMPS)):
        ob[f"lamp{i}_light"].hide_render = light not in ("night", "dusk")
    # ---- lying actors: face up (kit 'lie' rotates face-down), sleepers keep eyes shut
    for n, spec in actors.items():
        act = acts.get(n, spec[3])
        root = ob[n + "_root"]
        if act == "lie":
            root.rotation_euler.x = 1.5
            root.location.z = spec[4] + 0.28 * CAST[n]["scale"]
            ob[n + "_head"].rotation_euler = (0, 0, 0.06 * math.sin(0.7 * t))
        if sset in SLEEP_SETS and n not in sh.get("faces", {}) and (act == "lie" or sset in ("fountain", "horses") and n in ("t1", "t4", "t6")):
            stage.set_face(n, "blank")
        if sset in LINE_SETS:
            if n not in sh.get("faces", {}):
                stage.set_face(n, "blank")
            if act == "walk":
                ph = hash(n) % 7
                ob[n + "_armR"].rotation_euler = (1.15 + 0.06 * math.sin(3 * t + ph), 0, -0.15)
                ob[n + "_armL"].rotation_euler = (-0.55, 0, 0.1)
                if n == spec and False:
                    pass
        if sset in ("hill", "church", "sunrise"):
            x, y = root.location.x, root.location.y
            if act != "lie":
                root.location.z = hill_z(x, y) + (root.location.z - spec[4])
    if sset in LINE_SETS and "nora" in actors and actors["nora"][3] == "walk" and sset != "game":
        ob["nora_armR"].rotation_euler = (1.45 + 0.08 * math.sin(2.2 * t), 0.15 * math.sin(1.3 * t), 0)
    # sitting up in bed / on the grass looking up
    if sset in ("tent", "bed_wake"):
        root = ob["nora_root"]
        s = CAST["nora"]["scale"]
        root.location.z = 0.35 + 0.56 - 0.9 * s
        ob["nora_legL"].rotation_euler.x = ob["nora_legR"].rotation_euler.x = 1.57
        if sset == "bed_wake":
            ob["nora_armL"].rotation_euler = (0.6, -0.5 * smooth(t / 0.4), 0)
            ob["nora_armR"].rotation_euler = (0.6, 0.5 * smooth(t / 0.4), 0)
    if sset == "yard":
        ob["nora_head"].rotation_euler.x = 0.5 + 0.06 * math.sin(0.8 * t)
        ob["nora_head"].rotation_euler.z = 0.25 * math.sin(0.5 * t)
        ob["nora_armR"].rotation_euler = (2.6 + 0.15 * math.sin(3 * t), 0, 0)
    # knocking / ringing
    if sh.get("knock"):
        ob["nora_armR"].rotation_euler = (1.55 + 0.35 * abs(math.sin(9 * t)), 0, 0)
        ob["nora_armL"].rotation_euler = (1.2 + 0.3 * abs(math.sin(9 * t + 1.2)), 0, 0)
    ring = sset == "tower"
    sw = math.sin(4.2 * gt)
    ob["bell_pivot"].rotation_euler.x = (0.55 * sw) if (ring or sid in ("s18",)) else 0.0
    if ring:
        ob["nora_armR"].rotation_euler = (2.7 - 0.6 * abs(sw), 0, 0)
        ob["nora_armL"].rotation_euler = (2.6 - 0.6 * abs(sw), 0, 0)
    # ---- props that follow actors
    if "mail" in actors:
        r = ob["mail_root"]
        f = (math.cos(r.rotation_euler.z + math.pi / 2), math.sin(r.rotation_euler.z + math.pi / 2))
        ob["dog"].location = (r.location.x + f[0] * 1.7 + f[1] * 0.75, r.location.y + f[1] * 1.7 - f[0] * 0.75, 0.0)
        ob["dog"].rotation_euler.z = math.atan2(f[1], f[0])
        ob["dog"].location.z = 0.03 * abs(math.sin(9 * t))
    else:
        ob["dog"].location = (0, 0, -100)
    ob["tent"].hide_render = sset != "tent"
    if sset == "tent":
        _attach(stage, "flashlight", "nora_armL", (0.05, 0.2, -0.8), (0.3, 0, 0))
        ob["nora_armL"].rotation_euler = (1.0, 0, -0.2)
        _attach(stage, "nora_book", "nora_armR", (0, 0.18, -0.86), (0.4, 0, 0))
        hp = ob["nora_head"].matrix_world.translation
        ob["flash_light"].location = (hp.x, hp.y - 0.9, hp.z + 0.2)
    else:
        ob["flashlight"].parent = None
        ob["flashlight"].location = (0, 0, -100)
        ob["nora_book"].parent = None
        ob["nora_book"].location = (0, 0, -100)
        ob["flash_light"].location = (0, 0, -100)
    if sset == "tuck":
        _attach(stage, "mom_book", "mom_armR", (0, 0.15, -0.86), (0.3, 0, 0))
    else:
        ob["mom_book"].parent = None
        ob["mom_book"].location = (0, 0, -100)
    # ---- fireflies + lullaby notes
    for i, (fx, fy, fz) in enumerate(FIREFLIES):
        ob[f"ff{i}"].location = (fx + 0.5 * math.sin(0.6 * gt + i), fy + 0.4 * math.cos(0.5 * gt + 2 * i), fz + 0.3 * math.sin(1.1 * gt + i))
        ob[f"ff{i}"].hide_render = (int(gt * 1.3 + i * 0.37) % 3 == 0)
    for i in range(4):
        ob[f"note{i}"].location.z = 7.5 + i * 0.6 + 0.4 * math.sin(1.6 * gt + i)
        ob[f"note{i}"].hide_render = sset != "school"
    ob["candle_flames"].hide_render = sset != "birthday"
    # ---- flood, puddles, rain, breach
    lvl = flood_level(sid, gt) if sid in FLOOD or (sid.startswith("s") and 23 <= k <= 28) else 0.0
    ob["flood"].location.z = (-0.25 + lvl * 1.05) if lvl > 0 else -5
    ob["puddles"].hide_render = not (sid.startswith("s") and k >= 29)
    ob["breach_spill"].hide_render = not (sid.startswith("s") and 16 <= k <= 28)
    ob["river_water"].location.z = 0.5 if (sid.startswith("s") and 15 <= k <= 28) else 0.0
    ob["fountain_jet"].hide_render = storm or night
    if storm:
        tl = _timeline()
        try:
            pos = stage.cam_rig(sh, t, actors, 0.0)[0]
        except Exception:
            pos = None
        if pos is not None:
            ob["rain"].location = (pos.x, pos.y, -((gt * 16.0) % 12.0) + max(0.0, pos.z - 8))
            ob["rain"].hide_render = False
        T = stage.target(sh["tgt"], actors)[0] if sh.get("tgt") else None
        if T is not None:
            ob["rain_far"].location = (T.x, T.y, -((gt * 14.0) % 14.0))
            ob["rain_far"].hide_render = False
    else:
        ob["rain"].hide_render = True
        ob["rain_far"].hide_render = True
    # ---- lightning: flash windows (bright sun + sky for a few frames)
    flash = False
    if sid in STORM and (sh.get("flash") or (sh["seed"] % 4 == 0)):
        u = t / max(0.01, sh["dur"])
        flash = 0.54 <= u <= 0.66 or 0.18 <= u <= 0.22
    if night:
        el, az, st, sc, hz, mid, top, bgs = stage.moods["night"]
        stage.sun.data.energy = st * (9.0 if flash else (0.85 if storm else 1.0))
        stage.sun.data.color = (0.85, 0.9, 1.0) if flash else lin(sc)[:3]
        stage.bg.inputs["Strength"].default_value = bgs * (3.2 if flash else (0.8 if storm else 1.0))
    for nm in ("win_glow_b", "win_glow_s"):
        m = ob[nm].data.materials[0]
        m.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 9.0 if flash else (0.5 if night else 1.5)
    # ---- Nora: counter hold-then-tick during the countdown, stone eyelids after "STONE"
    keys = stage.ckeys.get("nora", [])
    if keys and "nora" in actors and stage.counter:
        for (ta, va, _), (tb, vb, _) in zip(keys, keys[1:]):
            if ta <= gt < tb and va > vb and va <= 300 and tb - ta < 6.0:
                hold = min(0.35, (tb - ta) * 0.4)
                v = va if gt < ta + hold else round(lerp(va, vb, (gt - ta - hold) / max(0.05, tb - ta - hold)))
                if gt < tb:
                    v = max(v, vb + 1) if gt < tb - 0.02 else vb
                stage.set_counter("nora", v, gt)
                break
    tl = _timeline()
    stone = (k > 22) or (k == 22 and gt >= tl.get("stone", 1e9) - 0.05)
    if stone and "nora" in actors:
        for side, x in (("L", 0.113), ("R", -0.113)):
            _attach(stage, f"nora_lid{side}", "nora_head", (x, 0.33, 0.375))
            ob[f"nora_lid{side}"].hide_render = False
        stage.set_face("nora", "blank")
    else:
        for side in ("L", "R"):
            ob[f"nora_lid{side}"].hide_render = True


def cam_override(stage, sh, t, actors, T, f, u):
    """Lying sleepers: look down at their faces / chest counters from above."""
    from mathutils import Vector
    from render import lerp, rot2
    tgt, cam = sh.get("tgt"), sh["cam"]
    if tgt in actors and actors[tgt][3] == "lie" and sh.get("acts", {}).get(tgt, "lie") == "lie":
        H = stage.head_pos(tgt) - Vector((0, 0, 0.3))
        down = -f              # toward the feet is +f (facing), head is opposite
        if cam in ("ecu", "cu", "dutch"):
            d = 1.25 if cam == "ecu" else 1.7
            pos = H + Vector((0, 0, lerp(d, d * 0.85, u))) + f * 0.55 + rot2(f, 90) * 0.15
            return pos, H, 40, (8 if cam == "dutch" else 0)
        if cam in ("counter", "mcu"):
            C = stage.ob[tgt + "_torso"].matrix_world @ Vector((0, 0.3, 1.43))
            pos = C + Vector((0, 0, lerp(2.0, 1.7, u) if cam == "counter" else lerp(2.8, 2.4, u))) + f * 0.4
            look = C if cam == "counter" else (C + H) / 2
            return pos, look, 40
        if cam in ("high", "push", "orbit", "low", "wide"):
            pos = H + f * lerp(2.4, 1.9, u) + rot2(f, 50) * 0.6 + Vector((0, 0, lerp(2.2, 1.9, u)))
            return pos, H + f * 0.6, 30
    if sh["set"] == "tent" and tgt == "nora" and cam in ("cu", "ecu", "mcu", "push"):
        H = stage.head_pos("nora")
        d = {"ecu": 1.1, "cu": 1.5, "mcu": 1.9, "push": lerp(2.6, 1.6, u)}[cam]
        pos = H + f * d + Vector((0.12, 0, -0.05))
        return pos, H - Vector((0, 0, 0.2 if cam == "mcu" else 0.0)), 36
    if tgt == "tent":
        pos = Vector((BX + 2.4 + lerp(-1.2, -0.6, u), BY - 2.2, lerp(2.2, 1.9, u)))
        return pos, Vector((BX + 2.4, BY + 2.2, 1.4)), 30
    if sh["set"] == "yard" and cam == "sky":
        H = stage.head_pos("nora")
        pos = H + Vector((0.3, -1.6, -0.2))
        return pos, H + Vector((0, lerp(4, 7, u), lerp(6, 11, u))), 22
    if tgt in ("door_a", "door_b") and cam == "ots":
        n = "nora"
        O = stage.head_pos(n)
        pos = O + Vector((0.7, 1.5, 0.3))
        return pos, T, 36
    return None
