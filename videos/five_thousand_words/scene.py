"""In This Town, You Get 5,000 Words - cast, blocking, set dressing (Style B), boat/dog/duck animation hooks."""
import math

CAST = {
    "finn":   dict(shirt="#e07a3a", pants="#3d5a8a", hair="#7a4a2a", skin="#e8c4a0", scale=0.78, kind="kid",
                   held=["whiteboard"], label="SAVING WORDS", start=4812),
    "mom":    dict(shirt="#4f9a8a", pants="#5c4a40", hair="#6a4428", skin="#e6c4a0", scale=0.98, kind="mom", start=15),
    "pip":    dict(shirt="#f0d860", pants="#e8c850", hair="#c89a5a", skin="#f0d0b0", scale=0.5, kind="baby", start=5000),
    "baker":  dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker",
                   held=["loaf"], start=1),
    "mayor":  dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor", start=1404),
    "granny": dict(shirt="#8b6f85", pants="#5c4a58", hair="#d8d4cc", skin="#eccdb2", scale=0.94, kind="granny", start=38),
    "man":    dict(shirt="#5a6a9a", pants="#3e4652", hair="#2f2620", skin="#c49670", scale=1.02, kind="plain", start=212),
    "old":    dict(shirt="#8a8a80", pants="#4d4a44", hair="#d0d0c8", skin="#d8b898", scale=0.98, kind="plain", start=0),
    "vendor": dict(shirt="#d86a8a", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="plain", start=2650),
    "t1":     dict(shirt="#f4f0e8", pants="#e8e4dc", hair="#c09060", skin="#e6c4a0", scale=0.97, kind="mom", start=3120),
    "t2":     dict(shirt="#2f3440", pants="#2a2c34", hair="#2b211a", skin="#aa7a58", scale=1.02, kind="dad", start=2876),
    "t3":     dict(shirt="#a3593d", pants="#4f4436", hair="#1f1a16", skin="#96684a", scale=1.0, kind="plain", start=2310),
    "t4":     dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=0.99, kind="plain", start=4105),
    "t5":     dict(shirt="#b8964a", pants="#5d5040", hair="#4a3426", skin="#e6c4a0", scale=0.97, kind="farmer", start=1777),
    "t6":     dict(shirt="#7d4448", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain", start=3360),
    "kid1":   dict(shirt="#4a8ad8", pants="#3e4652", hair="#2b211a", skin="#c49670", scale=0.74, kind="kid", start=4930),
    "kid2":   dict(shirt="#d84a6a", pants="#5a4b3a", hair="#c09060", skin="#eccdb2", scale=0.72, kind="kid", start=4875),
    "kid3":   dict(shirt="#6ab04a", pants="#4d4234", hair="#1f1a16", skin="#96684a", scale=0.76, kind="kid", start=4960),
    "kid4":   dict(shirt="#9a6ad0", pants="#3f3a36", hair="#7a4a2a", skin="#e8c4a0", scale=0.73, kind="kid", start=4901),
}
HATS = {"mayor", "baker"}

KX, KY = 0.0, 600.0          # kitchen (birthday, toaster)
BX = 20.0                    # bathroom/shower  (BX, 600)
CLX = 40.0                   # closet           (CLX, 600)
BRX = 60.0                   # bedroom/blanket  (BRX, 600)
DZ = 0.67                    # dock / jetty plank height

SHORE = {"t1": (-28.0, -40.6, -80, "idle", 0), "t2": (-25.4, -39.6, -95, "idle", 0), "t4": (-9.4, -40.8, -110, "idle", 0),
         "t5": (-30.6, -38.8, -70, "idle", 0), "t6": (-12.2, -38.6, -100, "idle", 0), "man": (-23.2, -41.2, -85, "idle", 0),
         "baker": (-32.6, -41.6, -75, "idle", 0), "mayor": (-6.8, -39.8, -115, "idle", 0),
         "granny": (-27.0, -37.6, -90, "idle", 0), "vendor": (-15.5, -40.0, -90, "idle", 0)}
PIP_BOAT = (-17.4, -50.0, 90, "idle", 0)   # overridden every frame by apply() (rides the boat)

SETS = {
    "town": {"t1": (-10, -1.5, 0, "walk", 0), "t2": (15, 1.6, 180, "walk", 0), "t3": (25, -3, 90, "idle", 0),
             "t4": (-30, 6, 0, "idle", 0), "t5": (4, 1.8, 180, "walk", 0), "t6": (-4, -2.2, 0, "walk", 0),
             "finn": (8, -2.4, 90, "idle", 0), "kid1": (-16, 2.5, 0, "run", 0), "granny": (34, 6.2, -90, "idle", 0)},
    "street": {"finn": (2, -2.6, 90, "idle", 0), "old": (6.5, -2.2, 180, "idle", 0), "t4": (-6, -2.6, 0, "idle", 0),
               "t6": (-1, 1.8, 180, "walk", 0), "t2": (12, 1.5, 180, "walk", 0), "kid3": (-9, 2.4, 0, "walk", 0)},
    "street_mom": {"mom": (-5, -2.4, 90, "idle", 0), "pip": (-4.0, -2.7, 90, "idle", 0), "t3": (-2.2, -1.6, -150, "talk", 0),
                   "t5": (4, 1.6, 180, "walk", 0)},
    "plaza": {"mayor": (66.6, 0, 180, "idle", 0.6), "finn": (59.6, 0.9, 0, "idle", 0), "t1": (59, -3.2, 0, "idle", 0),
              "t3": (58.4, -1.2, 0, "idle", 0), "t5": (58.2, 3.4, 0, "idle", 0), "t6": (58.6, 2.4, 10, "idle", 0),
              "granny": (57.2, -2.3, 0, "idle", 0), "baker": (56.9, 1.4, 0, "idle", 0), "t2": (56.2, -0.2, 0, "idle", 0),
              "t4": (55.8, -3.8, 5, "idle", 0)},
    "wedding": {"mayor": (66.6, 0, 180, "idle", 0.6), "t1": (62.8, 0.7, 180, "idle", 0), "t2": (62.8, -0.7, 180, "idle", 0),
                "t3": (58.4, -1.2, 0, "clap", 0), "t4": (57.6, -3.2, 10, "clap", 0), "t5": (58.2, 3.4, -5, "clap", 0),
                "t6": (57.2, 1.9, 0, "clap", 0), "granny": (59.0, -2.8, 15, "clap", 0), "baker": (56.4, 0.2, 0, "clap", 0)},
    "bakery": {"baker": (-20, 8.5, -90, "idle", 0), "t3": (-20, 5.7, 90, "idle", 0), "t5": (-13, 1.8, 180, "walk", 0)},
    "school": {"t4": (-42, 8.6, -90, "sign", 0), "kid1": (-43.6, 5.6, 80, "sign", 0), "kid2": (-41.6, 5.3, 95, "sign", 0),
               "kid3": (-40.0, 5.8, 110, "sign", 0)},
    "recess": {"kid1": (-43.5, 6.8, -20, "whisper", 0), "kid2": (-42.4, 6.2, 160, "sign", 0),
               "kid3": (-38.6, 6.0, 190, "sign", 0), "kid4": (-37.4, 6.3, -10, "sign", 0),
               "finn": (-50.0, 6.95, -90, "sit", -0.06)},
    "board_walk": {"finn": (-44.0, 6.8, -30, "hold", 0), "kid1": (-41.0, 6.0, 170, "laugh", 0),
                   "kid2": (-40.6, 7.4, 190, "laugh", 0)},
    "trade": {"kid1": (-40.0, 6.4, 180, "talk", 0), "kid2": (-41.4, 6.4, 0, "give", 0)},
    "debate": {"mayor": (66.6, 0, 180, "sign", 0.6), "t1": (59, -3.2, 0, "sign", 0), "t3": (58.4, -1.2, 0, "sign", 0),
               "t5": (58.2, 3.4, 0, "sign", 0), "t6": (58.6, 2.4, 10, "sign", 0), "granny": (57.2, -2.3, 0, "sign", 0),
               "baker": (56.9, 1.4, 0, "sign", 0), "t2": (56.2, -0.2, 0, "sign", 0)},
    "corner": {"t1": (-1, -2.0, 0, "walk", 0), "t6": (10, 2.0, 180, "walk", 0)},
    "yard": {"finn": (1.0, -7.4, 180, "talk", 0)},
    "park": {"finn": (27.8, -30.6, 130, "talk", 0)},
    "kitchen": {"finn": (0.6, KY - 1.1, 140, "idle", 0), "mom": (-1.8, KY + 0.9, -40, "idle", 0)},
    "toaster": {"finn": (2.0, KY + 3.0, 60, "talk", 0)},
    "shower": {"finn": (BX, KY + 0.9, -90, "sing", 0)},
    "closet": {"finn": (CLX, KY + 0.3, -90, "sing", 0)},
    "blanket": {"finn": (BRX + 2.4, KY + 1.5, -90, "sing", 0.36)},
    "lake_walk": {"mom": (-20.7, -19, -90, "walk", 0), "finn": (-19.3, -18.4, -90, "walk", 0),
                  "pip": (-20.0, -17.6, -90, "walk", 0)},
    "lake": {"finn": (-19.4, -46.5, -80, "idle", DZ), "mom": (-20.6, -46.0, -100, "idle", DZ), "pip": PIP_BOAT,
             "t1": SHORE["t1"], "t5": SHORE["t5"], "t6": SHORE["t6"], "vendor": SHORE["vendor"]},
    "icecream": {"mom": (-15.6, -43.0, 90, "idle", 0), "vendor": (-15.5, -40.0, -90, "idle", 0),
                 "finn": (-18.0, -43.6, 60, "idle", 0), "pip": PIP_BOAT},
    "dock_run": {"mom": (-20.0, -44.2, -90, "run", DZ), "finn": (-17.4, -43.4, -90, "idle", 0), "pip": PIP_BOAT},
    "dock": dict({"mom": (-20.5, -55.6, -90, "idle", DZ), "finn": (-19.3, -54.6, -95, "idle", DZ), "pip": PIP_BOAT}, **SHORE),
    "shore": dict({"pip": PIP_BOAT, "mom": (-20.5, -55.6, -90, "idle", DZ), "finn": (-19.3, -54.6, -95, "idle", DZ)}, **SHORE),
    "dock_sing": dict({"mom": (-20.5, -55.6, -90, "sing", DZ), "finn": (-19.5, -54.9, -95, "sing", DZ), "pip": PIP_BOAT},
                      **{k: (v[0], v[1], v[2], "sing", v[4]) for k, v in SHORE.items()}),
    "jetty": {"mom": (-25.6, -74.7, 10, "hug", DZ), "finn": (-25.6, -73.6, -20, "laugh", DZ), "pip": PIP_BOAT},
    "granny": {"granny": (12, -8.0, 90, "sing", 0), "t5": (12.2, -5.0, -90, "idle", 0)},
    "finale": {"mayor": (66.6, 0, 180, "sing", 0.6), "finn": (61.0, 0.4, 0, "sing", 0), "mom": (60.2, -1.1, 0, "sing", 0),
               "pip": (60.6, 1.5, 0, "sing", 0), "t1": (58, -3.2, 0, "sing", 0), "t3": (57.4, -1.2, 0, "sing", 0),
               "t5": (57.2, 3.4, 0, "sing", 0), "t6": (57.6, 2.4, 10, "sing", 0), "granny": (56.2, -2.3, 0, "sing", 0),
               "baker": (55.9, 1.0, 0, "sing", 0), "t2": (55.2, -0.4, 0, "sing", 0), "t4": (54.8, -3.8, 5, "sing", 0),
               "kid1": (59.2, -1.9, 0, "sing", 0), "kid2": (59.0, 2.6, 0, "sing", 0), "vendor": (54.5, 2.6, 0, "sing", 0),
               "man": (55.4, 4.4, -10, "sing", 0)},
}
BOAT_SETS = {"lake", "icecream", "dock_run", "dock", "shore", "dock_sing", "jetty"}
INTERIOR_SETS = {"kitchen", "toaster", "shower", "closet", "blanket"}
SET_MOOD = {s: "interior" for s in INTERIOR_SETS}
ROOMS = {"kitchen": (KX - 4.9, KX + 4.9, KY - 4.9, KY + 4.9, 3.1), "toaster": (KX - 4.9, KX + 4.9, KY - 4.9, KY + 4.9, 3.1)}
LIGHTS = {"kitchen_lamp": {"kitchen", "toaster"}, "bedroom_lamp": {"blanket"}, "tent_light": {"blanket"},
          "bath_lamp": {"shower"}, "closet_lamp": {"closet"}}

PROPS = {
    "bakery_sign": (-20, 9.9, 4.3, -90), "stall_bread": (-20, 7.3, 1.05, -90),
    "sign_a": (5.0, -5.9, 2.45, 90), "sign_b": (-25.0, -36.0, 2.45, 0),
    "park_tree": (26.0, -28.5, 3.0, -50),
    "cake": (KX, KY + 2.0, 1.15, -90), "toaster": (KX + 3.0, KY + 4.45, 1.3, -90),
    "dog_head": ("dog_headpivot", 0.12, 0.0, (0.05, 0)),
    "duck_tgt": ("duck1", 0.0, 0.0, (0.25, 90)),
    "rope": ("rowboat_rope", 0.0, 0.0, (0.1, 60)),
    "falls": (-20.0, -76.0, 0.6, 90),
    "jetty_end": (-24.6, -74.2, 0.9, 90),
}

# ---------------------------------------------------------------- boat path (global time, follows the narration)
BOAT_KEYS = [("s21", 0.0, 0.0), ("s21", 1.0, 0.42), ("s22", 1.0, 0.5), ("s24", 1.0, 0.58), ("s27", 1.0, 0.66),
             ("s30", 1.0, 0.75), ("s33", 1.0, 0.78), ("s35", 1.0, 0.84), ("s36", 0.88, 1.0)]
P_A, P_B, P_CTRL, P_C = (-17.4, -50.0), (-15.6, -67.5), (-16.2, -74.6), (-22.5, -74.2)
_TL = {}


def _timeline(stage):
    if "keys" not in _TL:
        import json
        tl = json.loads((stage.B / "timeline.json").read_text())
        by = {s["id"]: s for s in tl["sentences"]}
        _TL["keys"] = [(by[sid]["start"] + fr * (by[sid]["end"] - by[sid]["start"]), p) for sid, fr, p in BOAT_KEYS]
    return _TL["keys"]


def boat_progress(stage, sh, t, gt):
    b = sh.get("boat")
    if b is not None:
        if isinstance(b, (list, tuple)):
            return b[0] + (b[1] - b[0]) * min(1.0, t / max(0.01, sh["dur"]))
        return float(b)
    keys = _timeline(stage)
    if gt <= keys[0][0]:
        return keys[0][1]
    for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
        if gt <= t1:
            u = (gt - t0) / max(1e-3, t1 - t0)
            return p0 + (p1 - p0) * u
    return keys[-1][1]


def boat_path(p):
    """progress 0 (tied at the dock) .. 0.75 (thirty feet from the edge) .. 1 (bumps the falls jetty)."""
    if p <= 0.75:
        u = p / 0.75
        e = u * u * (1.6 - 0.6 * u)                  # starts slow, then faster
        x = P_A[0] + (P_B[0] - P_A[0]) * e + 0.8 * math.sin(math.pi * e)
        y = P_A[1] + (P_B[1] - P_A[1]) * e
        return x, y, 28.0 * e
    u = (p - 0.75) / 0.25
    a, c, b = P_B, P_CTRL, P_C
    x = (1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u * u * b[0]
    y = (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u * u * b[1]
    return x, y, 28.0 + 62.0 * u


# ---------------------------------------------------------------- build
def build(kit):
    T, B = kit.town, kit.blocks
    T.ground(roads=[(0, 0, 152, 8), (-20, -25, 5, 34), (30, -22, 3.5, 22)], plazas=[(66, 0, 26, 26), (30, -36, 16, 12)],
             keep_clear=[(-50, 10, -82, -40), (20, 40, -44, -28)])
    T.houses(north=[-60, -30, -10, 0, 10, 20, 30, 40, 50], south=[-50, -40, -30, -10, 0, 10, 20, 40, 50])
    T.bakery(-20, 14)
    T.school(-42, 14)
    T.town_hall(82, 0, podium=(66.6, 0))
    T.utilities(xs=(-60, -45, -30, -15, 0, 15, 30, 45, 60), y=-6.2, lamps_x=(-52, -28, -5, 15, 40, 55),
                barrels_at=[(-25.5, 8.6), (-26.3, 9.3), (16, -8.5), (5.6, -8.6), (72, -7), (72.8, -7.7), (35.5, 7.5),
                            (-13.2, -38.2), (-12.6, -37.4)])
    B.fence("yard_s1", (-56, -9.2), (-23, -9.2))
    B.fence("yard_s2", (-17, -9.2), (25, -9.2))
    B.fence("yard_s3", (35, -9.2), (56, -9.2))
    B.fence("yard_n2", (35, 9.5), (56, 9.5))
    B.fence("lake_fence_l", (-23, -10), (-23, -36))
    B.fence("lake_fence_r", (-17, -10), (-17, -36))
    for i, (x, y, f) in enumerate(((5.0, -5.9, 90), (-24.8, -36.0, 0), (52.0, 5.9, -90), (-34.0, -5.9, 90))):
        T.sign(f"sign_{'abcd'[i]}", x, y, f, "TALK ONLY IN\nEMERGENCIES", w=3.4, h=1.25, post=2.45, board="#a3302a",
               size=0.3)
    T.trees([(-60, -30), (-45, 28), (-8, -30), (12, 30), (42, -26), (55, 26), (-28, 32), (60, -22), (-55, 22),
             (12, -30), (45, 40), (15, 46), (-38, -30), (85, 20), (85, -20), (26, -28.5), (22, -40), (38, -42),
             (34, -29), (-48, -48), (8, -50), (-50, -64), (12, -66), (0, -40)], style="B")
    # park: fountain + benches
    B.cyl("fountain", 2.0, 0.6, (30, -36, 0), "#9a968c", seg=16)
    B.cyl("fountain_water", 1.8, 0.05, (30, -36, 0.55), "#4a7a9a", seg=16)
    B.cyl("fountain_col", 0.3, 1.6, (30, -36, 0.5), "#9a968c", seg=8)
    B.cyl("fountain_top", 0.8, 0.2, (30, -36, 1.9), "#9a968c", seg=12)
    for i, (bx, by, rz_) in enumerate(((25, -39.5, 0), (35, -39.5, 0), (-50, 7.25, 0))):
        B.multibox(f"bench{i}", [(1.9, 0.5, 0.08, 0, 0, 0.5, "#7a5c40"), (1.9, 0.08, 0.5, 0, 0.25, 0.8, "#7a5c40"),
                                 (0.1, 0.45, 0.5, -0.85, 0, 0.25, "#3e3b38"), (0.1, 0.45, 0.5, 0.85, 0, 0.25, "#3e3b38")],
                   loc=(bx, by, 0), rot_z=rz_)
    # lake + dock + rowboat + waterfall + ducks, and the little jetty right beside the falls
    T.lake(-20, -60)
    jd = [(8.6, 2.0, 0.18, -28.7, -74.2, 0.55, "#7a5c40")]
    jd += [(0.22, 0.22, 1.2, x, y, 0.2, "#5e4430") for x in (-32.6, -29.6, -26.6, -24.6) for y in (-75.1, -73.3)]
    jd += [(0.1, 2.0, 0.05, -33 + k * 0.7, -74.2, 0.65, "#6a4e36") for k in range(12)]
    B.multibox("falls_jetty", jd)
    B.multibox("reeds", [(0.08, 0.08, 0.9 + (k % 3) * 0.2, -40 + k * 0.7, -52 + (k % 4) * 0.5, 0.45, "#6b7044")
                         for k in range(10)] + [(1.2, 1.0, 0.5, 3.0 + k * 1.6, -55 - k, 0.2, "#7c7a74") for k in range(4)])
    B.multibox("dropped_board", [(0.7, 0.5, 0.03, 0, 0, 0, "#f4f4f0"), (0.74, 0.54, 0.02, 0, 0, -0.012, "#4a6a8a")],
               loc=(-18.95, -54.0, -200), rot_z=0.5)
    tx = B.text("dropped_board_txt", "SAVING WORDS", (0, 0, 0.02), 0, 0.075, "#2a3a6a", extrude=0.002)
    import bpy
    tx.parent = bpy.data.objects["dropped_board"]
    tx.rotation_euler = (0, 0, math.pi)
    # kitchen with birthday cake + toaster
    T.kitchen(KX, KY, soup=False)
    B.cyl("cake", 0.38, 0.28, (KX, KY + 2.0, 0.96), "#f0e0d0", seg=16)
    B.cyl("cake_top", 0.39, 0.05, (KX, KY + 2.0, 1.22), "#e07a9a", seg=16)
    for i in range(5):
        a = i * 2 * math.pi / 5
        B.cyl(f"candle{i}", 0.025, 0.16, (KX + 0.22 * math.cos(a), KY + 2.0 + 0.22 * math.sin(a), 1.26), "#6aa6dc", seg=5)
        fl = B.multibox(f"flame{i}", [(0.04, 0.04, 0.07, 0, 0, 0, "#ffd070")],
                        loc=(KX + 0.22 * math.cos(a), KY + 2.0 + 0.22 * math.sin(a), 1.47))
        T.emissive(fl, 6.0)
    B.multibox("toaster", [(0.52, 0.32, 0.34, 0, 0, 0.17, "#b8bcc0"), (0.4, 0.05, 0.02, 0, -0.06, 0.345, "#24201c"),
                           (0.4, 0.05, 0.02, 0, 0.06, 0.345, "#24201c"), (0.06, 0.04, 0.1, 0.27, 0, 0.2, "#24201c"),
                           (0.56, 0.36, 0.04, 0, 0, 0.0, "#3e3b38")], loc=(KX + 3.0, KY + 4.45, 1.08))
    # bathroom / shower
    T.room("bath", BX, KY, W=5, D=5, floor="#e8e0cc", wall="#8fa0a8")
    B.multibox("bath_props", [(2.2, 0.06, 2.4, BX, KY + 2.45, 1.2, "#e8e0cc"), (0.06, 0.06, 0.5, BX, KY + 2.2, 2.3, "#8a8078"),
                              (0.4, 0.3, 0.1, BX, KY + 1.95, 2.05, "#8a8078"), (2.4, 2.2, 0.1, BX, KY + 1.3, 0.05, "#8fa0a8"),
                              (0.06, 2.0, 2.2, BX - 1.2, KY + 1.3, 1.3, "#6aa6dc"), (2.4, 0.05, 0.05, BX, KY + 0.25, 2.45, "#8a8078")])
    drops = B.multibox("shower_water", [(0.025, 0.025, 1.6, BX + dx, KY + 1.92 + dy, 1.15, "#cfe6f0")
                                        for dx, dy in ((-0.15, 0), (-0.05, 0.06), (0.06, -0.04), (0.16, 0.03), (0.0, 0.1))])
    T.emissive(drops, 1.5)
    T.point_light("bath_lamp", (BX, KY - 0.5, 2.8), 60, (1.0, 0.92, 0.82))
    # closet with hanging clothes
    T.room("closet", CLX, KY, W=3.2, D=3.0, floor="#6a4a30", wall="#a88f72")
    cl = [(3.0, 0.06, 0.06, CLX, KY + 1.1, 2.3, "#3e3b38")]
    cols = ["#a3593d", "#4f6a8a", "#b8964a", "#6aa04a", "#d86a8a", "#5f8580", "#e8e0cc"]
    cl += [(0.36, 0.5, 1.1, CLX - 1.3 + k * 0.42, KY + 1.1, 1.65, cols[k]) for k in range(7)]
    cl += [(0.5, 0.3, 0.2, CLX - 0.9 + k * 0.7, KY + 1.2, 0.1, "#2e2722") for k in range(3)]
    B.multibox("closet_props", cl)
    T.point_light("closet_lamp", (CLX, KY - 0.6, 2.6), 22, (1.0, 0.8, 0.55))
    # bedroom + blanket fort over the bed
    T.bedroom(BRX, KY)
    tent = [(2.2, 1.9, 0.08, BRX + 2.4, KY + 2.0, 2.95, "#7a8fb0"), (0.08, 1.9, 2.1, BRX + 1.3, KY + 2.0, 1.9, "#7a8fb0"),
            (0.08, 1.9, 2.1, BRX + 3.5, KY + 2.0, 1.9, "#7a8fb0"), (2.2, 0.08, 2.1, BRX + 2.4, KY + 2.95, 1.9, "#6a7fa0"),
            (2.3, 0.4, 0.06, BRX + 2.4, KY + 1.05, 2.92, "#e8e0cc")]
    B.multibox("blanket_fort", tent)
    T.point_light("tent_light", (BRX + 2.4, KY + 0.3, 1.9), 18, (1.0, 0.85, 0.6))
    # dog (blocky, animated in apply)
    dog = B.empty("dog", (0, 0, -200))
    B.multibox("dog_body", [(0.9, 0.42, 0.42, 0, 0, 0.5, "#b07a42"), (0.5, 0.36, 0.1, 0, 0, 0.3, "#e8d8b8")]
               + [(0.13, 0.13, 0.34, sx, sy, 0.17, "#b07a42") for sx in (-0.32, 0.32) for sy in (-0.14, 0.14)], parent=dog)
    hp = B.empty("dog_headpivot", (0.45, 0, 0.66), parent=dog)
    B.multibox("dog_headbox", [(0.38, 0.36, 0.34, 0.1, 0, 0.08, "#b07a42"), (0.22, 0.24, 0.16, 0.34, 0, 0.0, "#e8d8b8"),
                               (0.06, 0.1, 0.07, 0.46, 0, 0.05, "#1e1a18"), (0.04, 0.06, 0.06, 0.29, 0.1, 0.16, "#1e1a18"),
                               (0.04, 0.06, 0.06, 0.29, -0.1, 0.16, "#1e1a18"), (0.12, 0.08, 0.22, 0.02, 0.18, 0.2, "#6a4428"),
                               (0.12, 0.08, 0.22, 0.02, -0.18, 0.2, "#6a4428"), (0.1, 0.12, 0.03, 0.4, 0, -0.08, "#d86a6a")],
               parent=hp)
    tp = B.empty("dog_tailpivot", (-0.45, 0, 0.62), parent=dog)
    tl = B.multibox("dog_tail", [(0.08, 0.08, 0.36, 0, 0, 0.18, "#b07a42")], parent=tp)
    tp.rotation_euler = (0, -0.6, 0)
    # candy bag (kid trade extra)
    B.multibox("candy_bag", [(0.22, 0.14, 0.26, 0, 0, 0, "#d84a8a"), (0.08, 0.08, 0.08, 0, 0, 0.16, "#f0d860")],
               loc=(0, 0, -200))


# ---------------------------------------------------------------- per-frame hooks
DOG_AT = {"yard": (-0.8, -7.6, 0)}
_DUCKS = {}


def apply(stage, sh, t, gt):
    import bpy
    from mathutils import Vector
    ob = stage.ob
    s = sh["set"]
    acts = sh.get("acts", {})
    # ---- rowboat drifts toward the waterfall (driven by the narration clock), Pip rides in it
    p = boat_progress(stage, sh, t, gt)
    bx, by, brot = boat_path(p)
    boat = ob["rowboat"]
    bz = 0.12 + 0.03 * math.sin(2.2 * gt)
    boat.location = (bx, by, bz)
    boat.rotation_euler = (0.03 * math.sin(1.7 * gt), 0.04 * math.sin(1.3 * gt), math.radians(brot))
    oar = ob["rowboat_oar"]
    pip_act = acts.get("pip", SETS.get(s, {}).get("pip", (0, 0, 0, "idle"))[3])
    if s in BOAT_SETS:
        r = ob["pip_root"]
        a = math.radians(brot)
        ox, oy = 0.0, -0.35
        r.location = (bx + ox * math.cos(a) - oy * math.sin(a), by + ox * math.sin(a) + oy * math.cos(a),
                      bz + (0.25 if pip_act in ("paddle", "sit") else 0.5))
        r.rotation_euler.z = a
        if pip_act == "paddle":
            w = math.sin(4 * t)
            oar.location = (-0.62, -0.15 + 0.25 * w, 0.75)
            oar.rotation_euler = (1.05 + 0.35 * w, 0.0, 0.25)
        else:
            oar.location = (-0.55, 0.0, 0.7)
            oar.rotation_euler = (0.35, 0, 0.5)
    # ---- ducks paddle in slow circles
    for i in range(5):
        d = ob.get(f"duck{i}")
        if d is None:
            continue
        if i not in _DUCKS:
            _DUCKS[i] = d.location.copy()
        b0 = _DUCKS[i]
        ph = 0.25 * gt + i * 1.3
        d.location = (b0.x + 0.9 * math.cos(ph), b0.y + 0.9 * math.sin(ph), b0.z + 0.02 * math.sin(3 * gt + i))
        d.rotation_euler.z = ph + math.pi / 2 + math.pi / 2
    # ---- dog
    dog = ob["dog"]
    if s in DOG_AT:
        x, y, f = DOG_AT[s]
        dog.location = (x, y, 0.04 * abs(math.sin(5 * gt)))
        dog.rotation_euler.z = math.radians(f)
        ob["dog_tailpivot"].rotation_euler = (0.7 * math.sin(14 * gt), -0.6, 0)
        ob["dog_headpivot"].rotation_euler = (0.25 * math.sin(1.3 * gt), 0, 0.1 * math.sin(0.9 * gt))
    else:
        dog.location = (0, 0, -200)
    # ---- dropped whiteboard on the dock
    db = ob["dropped_board"]
    db.location = (-18.95, -54.0, DZ + 0.02) if sh.get("board") == "down" and s in ("dock", "dock_sing") else (-18.95, -54.0, -200)
    # ---- candy bag in kid2's hand
    bag = ob["candy_bag"]
    if s == "trade":
        bpy.context.view_layer.update()
        bag.location = stage.hand_pos("kid2") + Vector((0, 0.08, -0.05))
    else:
        bag.location = (0, 0, -200)


def cam_override(stage, sh, t, actors, T, f, u):
    from mathutils import Vector
    from render import lerp, rot2
    cam, tgt = sh["cam"], sh["tgt"]
    if tgt.startswith("sign_") and cam == "prop":
        pos = T + rot2(f, lerp(-14, 10, u)) * lerp(7.4, 6.4, u) + Vector((0, 0, -0.5))
        return pos, T + Vector((0, 0, -0.15)), 30
    if tgt == "mayor" and cam == "low" and sh["set"] in ("plaza", "wedding", "debate", "finale"):
        pos = T + rot2(f, lerp(-38, -28, u)) * lerp(3.6, 3.0, u) + Vector((0, 0, -0.75))
        return pos, T + Vector((0, 0, 0.1)), 26
    if tgt == "dog_head" and cam == "ots":
        side = Vector((-f.y, f.x, 0))
        pos = T + f * lerp(1.9, 1.5, u) + side * 0.9 + Vector((0, 0, 0.55))
        return pos, T + Vector((0, 0, 0.05)), 30
    if tgt.endswith("_held_whiteboard"):
        o = stage.ob[tgt]
        n = (o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        c = o.matrix_world @ Vector((0, 0.12, 0))
        return c + n * lerp(1.25, 1.0, u) + Vector((0, 0, 0.05)), c, 35
    if tgt == "rowboat" and cam == "push":
        pos = T + rot2(f, lerp(170, 150, u)) * lerp(14, 8, u) + Vector((0, 0, 2.6))
        return pos, T + Vector((0, 0, 0.4)), 30
    return None
