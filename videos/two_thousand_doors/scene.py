"""In This Town, You Get 2,000 Doors - set dressing, cast, blocking (Style B).
Town + far-away interiors: kitchen (0,600), bedroom (0,-600), school hallway (598..642, 0), art room (600,600).
Hinged doors / round windows / fire / smoke / mug / buckets / Theo's jump are animated in apply()."""
import math

SENT_IDS = [f"s{i:02d}" for i in range(1, 35)]
EXTRA_AFTER = {"e01": "s10", "e02": "s05", "e03": "s07", "e04": "s13", "e05": "s08"}


def sidx(sid):
    if sid in SENT_IDS:
        return SENT_IDS.index(sid)
    return SENT_IDS.index(EXTRA_AFTER.get(sid, "s01")) + 0.5


def I(sid):
    return SENT_IDS.index(sid)


CAST = {
    "theo":  dict(shirt="#e0782e", pants="#3f5a8a", hair="#6a3e22", skin="#e8c4a0", scale=0.78, kind="kid", start=1640),
    "dad":   dict(shirt="#4f7a9a", pants="#4a4038", hair="#5a3a22", skin="#e0b890", scale=1.04, kind="dad", start=1204),
    "lily":  dict(shirt="#e86a9a", pants="#7a4a8a", hair="#c8903a", skin="#f0d0b0", scale=0.6, kind="kid", start=1862),
    "tchr1": dict(shirt="#6a9a5a", pants="#4a4a5a", hair="#3a2a20", skin="#c89a70", scale=1.0, kind="mom", start=640),
    "tchr2": dict(shirt="#8a6aa8", pants="#3e3a44", hair="#9a9a96", skin="#e8c8a8", scale=1.02, kind="plain", start=455),
    "mayor": dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor", start=1987),
    "baker": dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker", start=412,
                  held=["loaf"]),
    "mail":  dict(shirt="#4f6a8a", pants="#3e4652", hair="#1f1a16", skin="#96684a", scale=1.0, kind="mail", start=1499,
                  held=["env"], label="THEO"),
    "granny": dict(shirt="#a8607a", pants="#6a5a7a", hair="#e0dcd4", skin="#f0d0b8", scale=0.94, kind="granny", start=512),
    "k1":    dict(shirt="#3aa0c8", pants="#4a4a52", hair="#2b211a", skin="#aa7a58", scale=0.74, kind="kid", start=1720),
    "k2":    dict(shirt="#e8c040", pants="#5a4a7a", hair="#c09060", skin="#f0d0b0", scale=0.76, kind="kid", start=1585),
    "k3":    dict(shirt="#58b058", pants="#3e4652", hair="#1f1a16", skin="#7a5038", scale=0.72, kind="kid", start=1810),
    "k4":    dict(shirt="#d04848", pants="#4a4038", hair="#7a4e2a", skin="#deb890", scale=0.75, kind="kid", start=1666),
    "k5":    dict(shirt="#9a6ad0", pants="#3f5a8a", hair="#3a2a20", skin="#c89a70", scale=0.73, kind="kid", start=1903),
    "k6":    dict(shirt="#40b0a0", pants="#5a4a3a", hair="#b87a3a", skin="#f0d0b0", scale=0.7, kind="kid", start=1751),
    "k7":    dict(shirt="#f09a4a", pants="#3e3a44", hair="#2b211a", skin="#96684a", scale=0.74, kind="kid", start=1698),
    "t1":    dict(shirt="#a3593d", pants="#4f4436", hair="#2b211a", skin="#aa7a58", scale=0.98, kind="plain", start=812),
    "t2":    dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="mom", start=1033),
    "t3":    dict(shirt="#c8a040", pants="#3e4652", hair="#1f1a16", skin="#96684a", scale=1.0, kind="dad", start=357),
    "t4":    dict(shirt="#b8607a", pants="#5d5040", hair="#4a3426", skin="#e6c4a0", scale=0.97, kind="mom", start=1480),
    "t5":    dict(shirt="#869468", pants="#4d4234", hair="#c09060", skin="#cca078", scale=1.0, kind="farmer", start=921),
    "t6":    dict(shirt="#4a6ab0", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain", start=0),
}
HATS = {"mayor", "baker", "mail", "t5"}
DEFAULT_FACE = {"t6": "tired"}

KX, KY = 0.0, 600.0        # kitchen
BX, BY = 0.0, -600.0       # Theo's bedroom
HX0, HX1, HY0, HY1, HH = 598.0, 642.0, -2.2, 2.2, 3.4   # school hallway
AX, AY = 600.0, 600.0      # art room (x 596..604, y 596.5..603.5)
AH = 5.2

# ------------------------------------------------------------------ sets
KIDS_EXIT = {"k1": (600.4, -0.5, 180, "idle", 0), "k2": (600.6, 0.7, 185, "idle", 0), "k3": (601.7, -0.2, 175, "idle", 0),
             "k4": (601.9, 1.2, 180, "idle", 0), "k5": (603.0, 0.3, 185, "idle", 0), "k6": (603.2, -1.0, 170, "idle", 0),
             "k7": (604.3, 0.9, 180, "idle", 0)}
TEACHERS = {"tchr1": (598.9, -1.5, 25, "whisper", 0), "tchr2": (598.9, 1.6, -25, "whisper", 0)}
CROWD = {"tchr1": (-30.5, 10.4, 175, "idle", 0), "tchr2": (-30.8, 14.8, 188, "idle", 0), "k1": (-29.8, 11.6, 180, "idle", 0),
         "k2": (-29.6, 13.3, 182, "idle", 0), "lily": (-31.2, 12.5, 180, "idle", 0), "dad": (-28.2, 12.3, 180, "idle", 0),
         "mayor": (-27.4, 14.9, 192, "idle", 0), "baker": (-27.8, 9.8, 170, "idle", 0), "mail": (-26.3, 11.3, 180, "idle", 0),
         "granny": (-26.5, 13.6, 185, "idle", 0), "k3": (-28.9, 8.6, 165, "idle", 0), "k4": (-29.0, 16.2, 195, "idle", 0),
         "t1": (-25.4, 8.0, 160, "idle", 0), "t2": (-24.6, 6.4, 155, "idle", 0), "t3": (-26.8, 6.2, 150, "idle", 0),
         "t4": (-28.3, 7.0, 160, "idle", 0), "t5": (-24.9, 9.6, 170, "idle", 0), "t6": (-25.0, 15.0, 190, "idle", 0)}
BUCKET_LINE = {"t1": (-39.4, 8.7, 90, "give", 0), "t2": (-39.1, 7.85, 270, "give", 0), "t3": (-39.4, 7.0, 90, "give", 0),
               "t4": (-39.1, 6.15, 270, "give", 0), "t5": (-39.4, 5.3, 90, "give", 0), "t6": (-39.1, 4.45, 270, "give", 0),
               "dad": (-44.6, 8.7, 90, "give", 0), "tchr2": (-44.3, 7.85, 270, "give", 0), "baker": (-44.6, 7.0, 90, "give", 0)}

SETS = {
    # ---- town
    "town": {"t1": (-10, -1.6, 0, "walk", 0), "t2": (15, 1.8, 180, "walk", 0), "t3": (25, -3, 90, "idle", 0),
             "t4": (-30, 2.2, 0, "walk", 0), "t5": (5, 2.6, 180, "walk", 0), "t6": (36, -2, 0, "walk", 0),
             "theo": (1, -2.4, 90, "idle", 0), "k1": (-4, 1.5, 0, "run", 0)},
    "street": {"t2": (4.0, -2.6, 90, "idle", 0), "t5": (9, 1.5, 180, "walk", 0), "t4": (-6, -2.0, 0, "walk", 0),
               "t1": (-2.0, -2.8, 80, "talk", 0), "t3": (14, -1.0, 180, "walk", 0), "k2": (-9, 2.5, 0, "run", 0)},
    "door_demo": {"t1": (-10.0, -10.0, 90, "walk", 0), "t2": (-4.5, -6.2, 140, "idle", 0), "t5": (-16, 1.0, 0, "walk", 0)},
    "locked": {"t6": (20.0, -9.7, 90, "idle", 0), "t4": (14.0, -3.0, 0, "walk", 0)},
    "save": {"t3": (10.4, -9.4, 100, "idle", 0), "t2": (-10.2, -9.2, 80, "idle", 0), "k2": (2, -6.5, 0, "walk", 0),
             "t5": (-3, 2, 180, "walk", 0)},
    "morning": {"t1": (-10.0, -10.3, 90, "walk", 0), "k1": (-10.3, -11.4, 92, "walk", 0), "t2": (10.0, -10.2, 90, "walk", 0),
                "k2": (9.7, -11.3, 88, "walk", 0), "t3": (20.0, -10.3, 90, "walk", 0), "t4": (20.4, -11.5, 90, "walk", 0),
                "theo": (2.0, 10.3, -90, "walk", 0), "dad": (2.4, 11.3, -90, "walk", 0)},
    "dinner": {"t1": (-10.0, -6.8, -90, "walk", 0), "k1": (-10.5, -5.9, -90, "walk", 0), "t2": (10.0, -6.6, -90, "walk", 0),
               "k2": (10.4, -5.7, -90, "walk", 0), "t3": (20.0, -6.9, -90, "walk", 0), "t4": (19.6, -5.8, -90, "walk", 0),
               "theo": (2.0, 7.2, 90, "walk", 0), "dad": (2.5, 6.2, 90, "walk", 0)},
    "bakery": {"baker": (-21.2, 8.5, -90, "idle", 0), "t4": (-20.6, 5.5, 90, "idle", 0), "t5": (-12, 1.8, 180, "walk", 0)},
    "mail": {"mail": (2.75, 9.75, 105, "give:env", 0), "t5": (10, 1.5, 180, "walk", 0)},
    "mail_run": {"mail": (0.5, 6.4, 0, "run", 0), "t2": (12.0, -2.5, 150, "idle", 0), "t1": (-6, -2.2, 30, "idle", 0)},
    "school_ext": {"k1": (-42.5, 5.0, 90, "walk", 0), "k2": (-41.2, 4.2, 90, "walk", 0), "k3": (-43.6, 3.6, 95, "walk", 0),
                   "tchr1": (-40.0, 8.2, -100, "idle", 0)},
    "hall_curt": {"k1": (603.0, -0.9, -90, "walk", 0), "tchr1": (608.5, 0.6, 180, "talk", 0), "k2": (611.0, 0.9, 175, "walk", 0),
                  "k3": (606.4, 1.4, 92, "walk", 0)},
    "theo_door": {"theo": (2.0, 9.9, -90, "walk", 0), "t5": (9, 2.0, 180, "walk", 0)},
    "hall_rush": {"k1": (606.0, -0.5, 180, "run", 0), "k2": (607.0, 0.8, 182, "run", 0), "k3": (608.2, -0.1, 178, "run", 0),
                  "k4": (609.0, 1.2, 180, "run", 0), "k5": (610.2, 0.3, 185, "run", 0), "k6": (611.0, -1.0, 175, "run", 0),
                  "k7": (612.2, 0.9, 180, "run", 0), "tchr1": (604.0, -1.5, 180, "walk", 0)},
    "theo_intro": {"theo": (2.0, 7.4, -90, "idle", 0), "t5": (9, 2.0, 180, "walk", 0), "t4": (-7, -2.0, 0, "walk", 0)},
    # ---- kitchen
    "k_fridge": {"theo": (KX - 3.35, KY + 3.0, -70, "hold", 0)},
    "k_closet": {"theo": (KX - 0.2, KY + 3.5, -105, "hold", 0)},
    "k_oven": {"theo": (KX + 0.2, KY + 3.25, -75, "idle", 0)},
    "k_run": {"theo": (KX - 3.0, KY + 1.0, 0, "run", 0)},
    "k_bday": {"dad": (KX + 1.25, KY + 0.3, 180, "hold", 0), "theo": (KX - 1.0, KY + 0.3, 0, "idle", 0)},
    "k_talk": {"dad": (KX + 1.0, KY + 0.4, 180, "talk", 0), "theo": (KX - 1.0, KY + 0.3, 0, "idle", 0)},
    # ---- bedroom
    "bedroom": {"theo": (BX + 2.15, BY + 1.6, 180, "sit", 0.35)},
    "bed_stand": {"theo": (BX + 0.4, BY + 0.2, -60, "idle", 0)},
    "bed_night": {"theo": (BX - 2.6, BY + 3.15, 90, "sneak", 0.82)},
    "bed_door": {"theo": (BX - 2.2, BY - 1.2, 80, "sneak", 0)},
    "teased": {"k1": (0.3, 6.0, 80, "point", 0), "k2": (3.8, 6.3, 100, "laugh", 0), "k4": (1.9, 5.2, 90, "laugh", 0),
               "theo": (-1.0, 9.2, -60, "idle", 0)},
    "theo_out": {"theo": (0.5, 18.25, 90, "sneak", 1.0)},
    "night_st": {"theo": (-6, 3.0, 0, "sneak", 0)},
    # ---- school exterior + hallway
    "school_alarm": {"k1": (-44, 5.5, -90, "run", 0), "k2": (-40, 6.2, -80, "run", 0), "tchr2": (-42, 7.6, -90, "yell", 0)},
    "hall_alarm": {"k1": (605.0, -0.8, 0, "idle", 0), "k2": (606.2, 0.8, 200, "idle", 0), "k3": (608.0, -0.2, 160, "idle", 0),
                   "tchr1": (610.0, 0.8, 180, "yell", 0), "theo": (603.5, 0.5, -20, "idle", 0)},
    "hall_exit": dict(KIDS_EXIT, **TEACHERS, theo=(607.4, -1.3, 180, "idle", 0), lily=(612.0, 1.3, 200, "cry", 0)),
    "hall_lily": {"lily": (612.0, 1.3, 200, "cry", 0), "k7": (604.3, 0.9, 180, "idle", 0), "theo": (607.4, -1.3, 180, "idle", 0)},
    "hall_run": dict(KIDS_EXIT, **TEACHERS, theo=(609.0, -1.85, 180, "run", 0)),
    "hall_pull": dict({k: v for k, v in KIDS_EXIT.items() if k in ("k2", "k4", "k5", "k7")}, theo=(599.0, 0.45, 180, "hold", 0)),
    "hall_open": {"k1": (600.6, 0.2, 180, "run", 0), "k2": (601.8, 0.9, 182, "run", 0), "k3": (603.0, 0.1, 178, "run", 0),
                  "k4": (604.2, 0.8, 180, "run", 0), "k5": (605.4, 0.3, 180, "run", 0), "k6": (606.6, 1.0, 182, "run", 0),
                  "theo": (600.1, -1.45, -10, "hold", 0)},
    "hall_back": {"theo": (600.5, -0.2, 0, "run", 0)},
    "hall_c4": {"theo": (623.1, -1.35, 70, "hold", 0), "k6": (624.1, -1.5, 175, "run", 0), "k7": (624.7, -0.7, 170, "run", 0)},
    "hall_c5": {"theo": (627.2, 1.4, -70, "hold", 0), "k3": (628.0, 1.1, 185, "run", 0), "k1": (628.8, 0.5, 180, "run", 0)},
    "hall_closet": {"theo": (631.2, -1.35, 70, "hold", 0), "k5": (632.0, -1.2, 175, "run", 0)},
    "hall_jan": {"theo": (635.2, 1.4, -70, "hold", 0), "k4": (636.0, 1.0, 185, "run", 0)},
    "hall_dash": {"theo": (626.0, 0.0, 0, "run", 0)},
    # ---- art room
    "art_empty": {},
    "art_lily": {"lily": (601.6, 597.3, -90, "run", 0), "theo": (601.4, 598.6, -90, "give", 0)},
    "art_zero": {"theo": (601.55, 597.6, 90, "idle", 0)},
    "art_trap": {"theo": (601.65, 597.25, -90, "shake", 0)},
    "art_look": {"theo": (600.3, 599.4, 90, "look_up", 0)},
    "art_climb": {"theo": (600.0, 602.55, 90, "peek", 1.3)},
    "art_top": {"theo": (599.35, 602.95, 70, "peek", 2.62)},
    # ---- outside again
    "jump": {"theo": (-35.0, 12.0, 0, "idle", 0)},
    "landed": {"theo": (-33.6, 12.3, 10, "stagger", 0), "k1": (-29.8, 11.6, 180, "idle", 0), "lily": (-31.2, 12.5, 180, "idle", 0)},
    "crowd": dict(CROWD, theo=(-33.4, 12.4, 0, "idle", 0)),
    "bucket": dict(BUCKET_LINE),
    "hall_win": {"mayor": (73.6, -0.6, 180, "idle", 0), "t3": (66.5, 2.4, 0, "idle", 0), "t4": (66.0, -2.6, 10, "idle", 0),
                 "k2": (67.6, 0.4, 0, "idle", 0)},
    "bak_win": {"baker": (-22.6, 8.5, -90, "idle", 0), "t5": (-21.0, 4.8, 95, "idle", 0), "t2": (-18.2, 5.4, 110, "idle", 0)},
    "kids_win": {"k1": (-44.6, 8.95, 90, "peek", 0.55), "k2": (-39.4, 8.95, 90, "peek", 0.55), "k3": (-46.8, 8.95, 90, "sneak", 0.55),
                 "k5": (-42.0, 5.5, 80, "walk", 0), "k6": (-37.2, 8.95, 90, "peek", 0.55)},
    "win_town": {"t1": (-12.1, -9.75, -90, "peek", 0.55), "t2": (7.9, -9.75, -90, "peek", 0.55), "t4": (0, -2, 0, "walk", 0),
                 "t5": (18, 2, 180, "walk", 0)},
    "mail_ladder": {"mail": (14.1, 9.75, 90, "give:env", 1.15), "t5": (10, 2, 0, "walk", 0)},
    "granny_roof": {"granny": (28.9, -14.0, 0, "sit_talk", 3.56), "t2": (31.1, -14.0, 180, "sit", 3.56),
                    "k2": (30.0, -15.1, 90, "sit", 3.56)},
    "theo_end": {"theo": (2.0, 6.8, -90, "laugh", 0), "k1": (0.4, 6.0, -60, "idle", 0), "k2": (3.6, 6.1, -120, "idle", 0)},
    "finale": {"theo": (0.5, 18.25, 90, "wave", 1.0), "t1": (-10, -1.6, 0, "walk", 0), "t2": (15, 1.8, 180, "walk", 0),
               "t4": (-30, 2.2, 0, "walk", 0), "t5": (5, 2.6, 180, "walk", 0), "k1": (-4, 1.5, 0, "run", 0)},
}

INTERIOR_SETS = {s for s in SETS if s.startswith(("k_", "bed", "hall_", "art_"))} - {"hall_win"}
ROOMS = {}
for _s in INTERIOR_SETS:
    if _s.startswith("k_"):
        ROOMS[_s] = (KX - 4.85, KX + 4.85, KY - 4.85, KY + 4.85, 3.0)
    elif _s.startswith("bed"):
        ROOMS[_s] = (BX - 3.85, BX + 3.85, BY - 3.85, BY + 3.85, 3.0)
    elif _s.startswith("hall_"):
        ROOMS[_s] = (HX0 + 0.15, HX1 - 0.15, HY0 + 0.1, HY1 - 0.1, 3.2)
    else:
        ROOMS[_s] = (AX - 3.85, AX + 3.85, AY - 3.4, AY + 3.4, 5.0)
SET_MOOD = {s: "interior" for s in INTERIOR_SETS if s not in ("bed_night", "bed_door")}
HALL_SETS = {s for s in INTERIOR_SETS if s.startswith("hall_")}
ART_SETS = {s for s in INTERIOR_SETS if s.startswith("art_")}
LIGHTS = {"kitchen_lamp": {s for s in INTERIOR_SETS if s.startswith("k_")},
          "bedroom_lamp": {s for s in INTERIOR_SETS if s.startswith("bed")},
          "art_firelight": ART_SETS, "art_lamp": ART_SETS}
for _i in range(5):
    LIGHTS[f"hall_lamp{_i}"] = HALL_SETS

PROPS = {
    "slot": (2.0, 10.2, 1.3, -90), "bak_loaf": (-19.7, 8.35, 0.15, -90), "bak_sign": (-20, 9.8, 3.45, -90),
    "bak_door": (-19.9, 9.2, 1.2, -90),
    "sch_sign": (-42, 9.2, 4.3, -90), "sch_door": (-42, 9.25, 1.3, -90), "sch_rwin": (-35.4, 12.0, 3.6, 0),
    "curtain1": (603.0, -2.0, 1.4, 90), "curtain2": (606.0, 2.0, 1.4, -90), "curtain3": (609.0, -2.0, 1.4, 90),
    "hall_bell": (606.0, 2.05, 2.9, -90),
    "exit_door": (598.2, 0.0, 1.4, 0), "exit_handle": (598.25, 0.55, 1.1, 0),
    "hd_class4": (624.0, -2.0, 1.3, 90), "hd_class5": (628.0, 2.0, 1.3, -90), "hd_closet": (632.0, -2.0, 1.3, 90),
    "hd_janitor": (636.0, 2.0, 1.3, -90),
    "art_door": (601.6, 596.65, 1.2, 90), "art_handle": (602.05, 596.7, 1.05, 90), "awin": (600.0, 603.4, 4.25, -90),
    "shelves": (600.0, 603.0, 1.4, -90), "fire": (597.4, 600.6, 1.0, 0),
    "fridge": (KX - 4.2, KY + 3.9, 1.2, -90), "oven": (KX + 1.2, KY + 4.0, 0.5, -90), "kcloset": (KX - 0.9, KY + 4.85, 1.1, -90),
    "cake": (KX, KY + 2.0, 1.15, -90), "spill": (KX + 0.9, KY + 0.15, 0.05, 180),
    "bwin": (BX - 2.6, BY + 3.9, 2.25, -90), "bed_door": (BX - 3.9, BY - 1.1, 1.2, 0), "bowl": (BX + 1.62, BY + 1.6, 1.0, 180),
    "twin": (0.5, 17.6, 2.25, 90), "south_row": (0, -10.5, 1.5, 90), "dinner_row": (10, -9.0, 0.6, 90),
    "hall_bigwin": (76.3, 0.0, 5.1, 180), "hall_sign": (74.7, 0, 7.0, 180), "bak_bigwin": (-22.7, 9.85, 1.6, -90),
    "tea": (30.0, -14.0, 4.35, 90), "ladder_m": (14.1, 9.9, 1.8, -90),
    "fam_a_door": (-10.0, -10.2, 1.2, 90), "fam_b_door": (10.0, -10.2, 1.2, 90), "fam_c_door": (20.0, -10.2, 1.2, 90),
    "theo_door": (2.0, 10.2, 1.2, -90),
}
STRAIGHT_PROPS = set()
FAR_PROPS = {"hall_bigwin"}

# hinge name -> (axis, base_deg, open_deg)
HINGES = {}
SET_DOORS = {
    "door_demo": {"fam_a_hinge": "opening"}, "morning": {"fam_a_hinge": "open", "fam_b_hinge": "open", "fam_c_hinge": "open",
                                                          "theo_house_hinge": "open"},
    "dinner": {"fam_a_hinge": "open", "fam_b_hinge": "open", "fam_c_hinge": "open", "theo_house_hinge": "open"},
    "mail": {"theo_house_hinge": "closed"}, "theo_door": {"theo_house_hinge": "open"},
    "k_fridge": {"fridge_hinge": "opening"}, "k_closet": {"kcloset_hinge": "opening"}, "k_oven": {"oven_hinge": "twice"},
    "bed_night": {"bwin_hinge": "opening"}, "theo_out": {"twin_hinge": "open"}, "finale": {"twin_hinge": "open"},
    "hall_pull": {"exit_hinge": "opening"}, "hall_open": {"exit_hinge": "open"}, "hall_back": {"exit_hinge": "open"},
    "hall_c4": {"hd_class4_hinge": "opening"}, "hall_c5": {"hd_class4_hinge": "open", "hd_class5_hinge": "opening"},
    "hall_closet": {"hd_class4_hinge": "open", "hd_class5_hinge": "open", "hd_closet_hinge": "opening"},
    "hall_jan": {"hd_class4_hinge": "open", "hd_class5_hinge": "open", "hd_closet_hinge": "open", "hd_janitor_hinge": "opening"},
    "hall_dash": {"hd_class4_hinge": "open", "hd_class5_hinge": "open"},
    "art_lily": {"art_hinge": "open"}, "art_zero": {"art_hinge": "closed"}, "art_trap": {"art_hinge": "rattle"},
    "art_top": {"awin_hinge": "closed"},
}


def default_door(h, idx):
    if h == "bak_hinge":
        return "open"
    if h in ("exit_hinge", "sch_front_hinge"):
        return "open" if idx >= I("s22") else "closed"
    if h.startswith("hd_"):
        return "open" if idx >= I("s23") else "closed"
    if h == "art_end_hinge":
        return "open" if I("s23") <= idx < I("s24") else "closed"
    if h in ("awin_hinge", "swin_hinge"):
        return "open" if idx > I("s28") else "closed"
    return "closed"


# fire/smoke level by sentence
SMOKE = {"s17": 0.55, "s18": 0.65, "s19": 0.75, "s20": 1.0, "s21": 1.0, "s22": 1.0, "s23": 1.0, "s24": 1.0, "s25": 1.0,
         "s26": 1.0, "s27": 1.0, "s28": 1.0, "s29": 0.75, "s30": 0.35}

# custom camera views: name -> (pos_a, pos_b, look, lens); look = xyz | "actor" (head) | "actor@hand" | "actor@chest"
VIEWS = {
    "exit_hand": ((599.5, 1.95, 1.5), (599.35, 1.9, 1.45), "theo@hand", 32),
    "exit_side": ((600.6, -1.9, 1.6), (600.2, -1.8, 1.5), (598.3, 0.3, 1.2), 26),
    "exit_crowd": ((598.6, 1.2, 1.75), (598.6, 0.6, 1.7), (604.0, 0.0, 1.0), 22),
    "exit_out": ((598.5, 1.95, 1.4), (598.5, 1.9, 1.35), (604.0, 0.3, 1.0), 24),
    "c4_v": ((626.5, 1.6, 1.8), (626.2, 1.5, 1.7), (623.8, -1.6, 1.1), 26),
    "crowd_v": ((-34.6, 8.0, 2.2), (-34.4, 8.6, 2.1), (-28.5, 12.5, 1.2), 24),
    "hall_long": ((599.0, 1.6, 2.6), (601.5, 1.4, 2.5), (630.0, 0.0, 1.2), 30),
    "hall_rev": ((640.5, -1.5, 2.3), (638.0, -1.2, 2.2), (604.0, 0.4, 1.0), 30),
    "art_door_in": ((603.2, 598.8, 1.7), (603.0, 598.6, 1.6), (601.6, 596.8, 1.0), 26),
    "art_handle": ((600.3, 597.7, 1.5), (600.4, 597.6, 1.45), "theo@hand", 32),
    "art_up": ((601.8, 598.0, 0.7), (601.7, 598.3, 0.7), (600.0, 603.4, 4.2), 22),
    "art_wide": ((603.4, 597.0, 2.6), (603.2, 597.4, 2.5), (599.0, 601.5, 1.6), 22),
    "art_climb": ((601.8, 600.4, 2.2), (601.6, 600.8, 2.4), "theo", 30),
    "art_win_in": ((601.3, 601.2, 3.9), (601.2, 601.4, 3.95), (599.9, 603.4, 4.25), 30),
    "fire_v": ((600.6, 598.2, 1.8), (600.3, 598.6, 1.7), (597.3, 600.8, 0.9), 28),
    "morning_v": ((-3.0, -1.5, 2.2), (-2.5, -1.8, 2.1), (-10.0, -10.5, 1.2), 26),
    "jump_side": ((-28.5, 7.0, 2.0), (-28.8, 7.6, 1.8), "theo", 30),
    "bed_win": ((BX - 0.9, BY + 3.35, 2.45), (BX - 1.05, BY + 3.4, 2.4), (BX - 2.6, BY + 3.95, 2.2), 28),
    "bed_bowl": ((BX + 0.3, BY + 1.9, 1.35), (BX + 0.5, BY + 1.8, 1.3), (BX + 1.8, BY + 1.6, 1.1), 30),
    "fridge_v": ((KX - 4.4, KY + 0.9, 1.6), (KX - 4.3, KY + 1.2, 1.55), (KX - 3.9, KY + 3.8, 1.1), 28),
    "closet_v": ((KX + 1.2, KY + 1.8, 1.6), (KX + 1.0, KY + 2.1, 1.55), (KX - 0.9, KY + 4.8, 1.0), 28),
    "oven_v": ((KX + 2.6, KY + 2.2, 1.3), (KX + 2.4, KY + 2.4, 1.25), (KX + 1.2, KY + 4.0, 0.5), 30),
    "slot_v": ((3.9, 7.6, 1.7), (3.6, 8.0, 1.6), (2.1, 10.2, 1.3), 30),
    "bak_loaf_v": ((-17.6, 6.2, 1.6), (-17.8, 6.5, 1.5), (-19.8, 8.9, 0.9), 26),
    "kitchen_drop": ((KX + 2.7, KY + 1.8, 1.3), (KX + 2.5, KY + 1.6, 1.2), (KX + 1.1, KY + 0.3, 0.7), 28),
    "roof_high": ((36.0, -6.0, 9.0), (35.0, -6.6, 8.6), (30.0, -14.0, 4.0), 30),
    "ladder_low": ((16.5, 5.5, 0.5), (16.2, 5.8, 0.5), (14.1, 10.0, 2.6), 24),
}

BUCKETS = 9


# ------------------------------------------------------------------ build helpers
def _hinge(B, name, loc, base, open_deg, boxes, parent=None, axis="z"):
    h = B.empty(name + "_hinge", loc, math.radians(base) if axis == "z" else 0.0, parent=parent)
    if axis != "z":
        h.rotation_euler.z = math.radians(base)
    B.multibox(name + "_door", boxes, parent=h)
    HINGES[name + "_hinge"] = (axis, base, open_deg)
    h["hk"] = [1.0 if axis == "x" else 0.0, float(base), float(open_deg)]   # read back at render time
    return h


def _panel(w, h, thick=0.08, col="#6a4a30", knob=True, extra=()):
    b = [(w, thick, h, w / 2, 0, h / 2, col)]
    if knob:
        b += [(0.09, thick + 0.09, 0.09, w - 0.14, 0, h * 0.46, "#d8b860")]
    return b + list(extra)


def _ring(cx, cz, r0, r1, n=28, square=False):
    vs, fs = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        k = (r1 / max(abs(c), abs(s))) if square else r1
        vs += [(cx + r0 * c, 0, cz + r0 * s), (cx + k * c, 0, cz + k * s)]
    for i in range(n):
        j = (i + 1) % n
        fs.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    return vs, fs


def _disc(r, n=28, cz=0.0, y=0.0):
    vs = [(0, y, cz)] + [(r * math.cos(2 * math.pi * i / n), y, cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    fs = [(0, (i + 1) % n + 1, i + 1) for i in range(n)]
    return vs, fs


def round_window(kit, name, loc, face_deg, r, plate, sky, sky_emit, glass, glass_emit):
    """Round window on a wall: square plate with a round hole, wooden ring, 'sky' disc, glass pane hinged at the top
    (opens toward the viewer side, i.e. local +y = face_deg)."""
    B, T = kit.blocks, kit.town
    root = B.empty(name, loc, B.rz(face_deg))
    vs, fs = _ring(0, 0, r, r + 0.22, square=True)
    B.poly(name + "_plate", [(x, 0.0, z) for x, _, z in vs], fs, plate, parent=root)
    vs, fs = _ring(0, 0, r - 0.02, r + 0.1)
    B.poly(name + "_ring", [(x, 0.035, z) for x, _, z in vs], fs, "#5e4430", parent=root)
    B.multibox(name + "_sill", [(2 * r + 0.4, 0.22, 0.08, 0, 0.08, -r - 0.12, "#5e4430")], parent=root)
    vs, fs = _disc(r, y=-0.01)
    sk = B.poly(name + "_sky", vs, fs, sky, parent=root)
    if sky_emit:
        T.emissive(sk, sky_emit)
    if name in ("bwin",):
        B.multibox(name + "_stars", [(0.03, 0.01, 0.03, x, -0.005, z, "#fffbe8") for x, z in
                                     ((-0.2, 0.15), (0.12, 0.25), (0.22, -0.05), (-0.05, -0.2), (0.0, 0.08))], parent=root)
    h = B.empty(name + "_hinge", (0, 0.03, r), 0.0, parent=root)
    vs, fs = _disc(r - 0.01, cz=-r, y=0.0)
    gl = B.poly(name + "_glass", vs, fs, glass, parent=h)
    if glass_emit:
        T.emissive(gl, glass_emit)
    B.multibox(name + "_mullion", [(0.05, 0.05, 2 * r - 0.04, 0, 0.02, -r, "#5e4430"),
                                   (2 * r - 0.04, 0.05, 0.05, 0, 0.02, -r, "#5e4430"),
                                   (0.12, 0.08, 0.06, 0, 0.05, -2 * r + 0.08, "#c8a85a")], parent=h)
    HINGES[name + "_hinge"] = ("x", 0.0, 70.0)
    h["hk"] = [1.0, 0.0, 70.0]
    return root


def door_house(kit, name, x, y, face, wall=None, roof=None, h=3.6):
    B = kit.blocks
    d = 7
    root = B.house(name, x, y, face, w=7, d=d, h=h, wall=wall, roof=roof)
    B.multibox(name + "_doorway", [(1.15, 0.03, 2.05, 0, d / 2 + 0.17, 1.03, "#1c1814"),
                                   (0.6, 0.02, 0.4, 0, d / 2 + 0.16, 1.4, "#e8c870")], parent=root)
    _hinge(B, name, (-0.6, d / 2 + 0.21, 0), 0, 100,
           _panel(1.2, 2.06, col="#6a4a30", extra=[(0.36, 0.1, 0.08, 0.6, 0, 1.32, "#2a2420"),
                                                   (0.42, 0.11, 0.03, 0.6, 0, 1.38, "#c8a85a")]), parent=root)
    return root


def ladder(kit, name, base, height, tilt_deg, rz_deg=0.0):
    B = kit.blocks
    bx = [(0.08, 0.1, height, -0.25, 0, height / 2, "#7a5c40"), (0.08, 0.1, height, 0.25, 0, height / 2, "#7a5c40")]
    bx += [(0.5, 0.06, 0.06, 0, 0, 0.3 + i * 0.35, "#8a7052") for i in range(int((height - 0.3) / 0.35) + 1)]
    ob = B.multibox(name, bx, loc=base)
    ob.rotation_euler = (math.radians(tilt_deg), 0, math.radians(rz_deg))
    return ob


def flame(kit, name, loc, s=1.0):
    B, T = kit.blocks, kit.town
    ob = B.multibox(name, [(0.9 * s, 0.8 * s, 0.55 * s, 0, 0, 0.27 * s, "#ff6a1a"),
                           (0.6 * s, 0.55 * s, 0.6 * s, 0.06 * s, 0.03, 0.75 * s, "#ff9a2a"),
                           (0.34 * s, 0.32 * s, 0.5 * s, -0.05 * s, -0.02, 1.2 * s, "#ffd23a"),
                           (0.16 * s, 0.16 * s, 0.3 * s, 0.1 * s, 0.05, 1.55 * s, "#fff09a")], loc=loc)
    T.emissive(ob, 5.0)
    return ob


def smoke(kit, name, loc, size, col="#9a9aa0"):
    B = kit.blocks
    sx, sy, sz = size
    return B.multibox(name, [(sx, sy, sz, 0, 0, 0, col), (sx * 0.7, sy * 0.8, sz * 0.7, sx * 0.3, -sy * 0.15, sz * 0.4, "#b4b4b8"),
                             (sx * 0.6, sy * 0.6, sz * 0.6, -sx * 0.35, sy * 0.2, sz * 0.25, "#85858c")], loc=loc)


# ------------------------------------------------------------------ build
def build(kit):
    T, B = kit.town, kit.blocks
    HINGES.clear()
    T.ground(roads=[(0, 0, 152, 8)], plazas=[(66, 0, 26, 26)],
             keep_clear=[(-50, -22, 2, 20), (-40, -34, 2, 9.6)])
    # houses (>= 12) + custom door houses
    T.houses(north=[-62, -8, 22, 32, 42, 52], south=[-60, -50, -40, -30, -20, 0, 40, 50])
    door_house(kit, "theo_house", 2, 14, -90, wall="#8fa0a8", roof="#7a4a36")
    for nm, xx, wl in (("fam_a", -10, "#c8b08a"), ("fam_b", 10, "#b59a86"), ("fam_c", 20, "#9fa38a")):
        door_house(kit, nm, xx, -14, 90, wall=wl)
    B.house("mail_house", 12, 14, -90, w=7, d=7, h=3.6, wall="#cdbb98", roof="#5d4a3c")
    ladder(kit, "mail_ladder", (14.1, 9.25, 0), 3.6, -19)
    # Theo's round side window (night escape) + barrel under it
    round_window(kit, "twin", (0.5, 17.56, 2.25), 90, 0.42, "#8fa0a8", "#1c1814", 0, "#9cc4dc", 0)
    B.barrel("theo_barrel", 0.5, 18.25)
    # granny's flat-roof house with a tea party
    gx, gy = 30, -14
    gb = [(7, 7, 3.45, gx, gy, 1.72, "#c2a88a"), (7.3, 7.3, 0.3, gx, gy, 0.15, "#6d6252"),
          (1.2, 0.2, 2.1, gx, gy + 3.55, 1.05, "#5b4030"), (1.5, 0.12, 0.2, gx, gy + 3.58, 2.15, "#4a3a2c"),
          (7.4, 7.4, 0.16, gx, gy, 3.48, "#8a6a4a")]
    for sx in (-2.1, 2.1):
        gb += [(1.1, 0.14, 1.0, gx + sx, gy + 3.56, 1.9, "#4d5f6e"), (1.3, 0.1, 0.12, gx + sx, gy + 3.58, 1.34, "#e8e0cc")]
    for i in range(9):
        p = -3.6 + i * 0.9
        gb += [(0.08, 0.08, 0.8, gx + p, gy + 3.6, 3.96, "#e8e0cc"), (0.08, 0.08, 0.8, gx + p, gy - 3.6, 3.96, "#e8e0cc"),
               (0.08, 0.08, 0.8, gx - 3.6, gy + p, 3.96, "#e8e0cc"), (0.08, 0.08, 0.8, gx + 3.6, gy + p, 3.96, "#e8e0cc")]
    gb += [(7.3, 0.1, 0.08, gx, gy + 3.6, 4.36, "#e8e0cc"), (7.3, 0.1, 0.08, gx, gy - 3.6, 4.36, "#e8e0cc"),
           (0.1, 7.3, 0.08, gx - 3.6, gy, 4.36, "#e8e0cc"), (0.1, 7.3, 0.08, gx + 3.6, gy, 4.36, "#e8e0cc")]
    gb += [(1.3, 1.3, 0.08, gx, gy, 4.32, "#f0ece4"), (0.1, 0.1, 0.72, gx, gy, 3.92, "#6a4a30")]
    for cx_, cy_ in ((gx - 1.1, gy), (gx + 1.1, gy), (gx, gy - 1.1)):
        gb += [(0.55, 0.55, 0.08, cx_, cy_, 4.02, "#6a4a30"), (0.08, 0.08, 0.46, cx_, cy_, 3.79, "#6a4a30")]
    gb += [(0.5, 0.5, 0.3, gx + 2.6, gy + 2.6, 3.71, "#a3593d"), (0.6, 0.6, 0.4, gx + 2.6, gy + 2.6, 4.06, "#5d8a3a"),
           (0.5, 0.5, 0.3, gx - 2.6, gy + 2.6, 3.71, "#a3593d"), (0.6, 0.6, 0.4, gx - 2.6, gy + 2.6, 4.06, "#d870a0")]
    B.multibox("granny_house", gb)
    B.cyl("teapot", 0.18, 0.24, (gx + 0.1, gy + 0.1, 4.36), "#e870a0", seg=10, r2=0.13)
    B.multibox("teacups", [(0.1, 0.1, 0.08, gx - 0.35, gy + 0.05, 4.4, "#ffffff"), (0.1, 0.1, 0.08, gx + 0.4, gy - 0.2, 4.4, "#ffffff"),
                           (0.1, 0.1, 0.08, gx - 0.05, gy - 0.4, 4.4, "#ffffff"), (0.28, 0.28, 0.04, gx - 0.1, gy + 0.35, 4.37, "#e8c040")])
    B.multibox("bunting", [(0.25, 0.04, 0.25, gx - 3.4 + i * 0.45, gy + 3.62, 4.6, ["#e85a5a", "#e8c040", "#3aa0c8", "#58b058"][i % 4], 0)
                           for i in range(16)])
    ladder(kit, "granny_ladder", (gx + 2.6, gy + 4.4, 0), 4.2, 13)
    # landmarks
    T.bakery(-20, 14)
    T.school(-42, 14)
    T.town_hall(82, 0, podium=(66.6, 0))
    # bakery door propped open with a loaf
    B.multibox("bak_doorway", [(1.15, 0.03, 2.05, -20, 9.63, 1.03, "#1c1814"), (0.9, 0.02, 0.6, -20.0, 9.615, 1.1, "#e8c870")])
    _hinge(B, "bak", (-19.42, 9.58, 0), 180, 75, _panel(1.16, 2.04, col="#6a4a30",
                                                        extra=[(0.7, 0.1, 0.5, 0.58, 0, 1.45, "#9cc4dc")]))
    B.multibox("bak_loaf", [(0.5, 0.26, 0.24, -19.68, 8.42, 0.12, "#b07a3a", 0.9), (0.36, 0.2, 0.08, -19.68, 8.42, 0.27, "#c8945a", 0.9),
                            (0.08, 0.27, 0.04, -19.6, 8.3, 0.25, "#8a5a2a", 0.9), (0.08, 0.27, 0.04, -19.78, 8.55, 0.25, "#8a5a2a", 0.9)])
    B.multibox("bak_crumbs", [(0.06, 0.06, 0.03, -19.4 + 0.13 * i, 8.1 + 0.07 * (i % 3), 0.02, "#c8945a") for i in range(6)])
    # school: hinged heavy front door + round window on the east wall + glow window + smoke
    B.multibox("sch_doorway", [(1.75, 0.03, 2.35, -42, 9.33, 1.17, "#1c1814")])
    _hinge(B, "sch_front", (-41.12, 9.28, 0), 180, 95, _panel(1.76, 2.36, thick=0.1, col="#5e4028",
                                                               extra=[(1.6, 0.12, 0.1, 0.88, 0, 0.7, "#3a3a3e"),
                                                                      (1.6, 0.12, 0.1, 0.88, 0, 1.9, "#3a3a3e")]))
    round_window(kit, "swin", (-35.45, 12.0, 3.6), 0, 0.5, "#b59a86", "#2a2420", 0, "#9cc4dc", 0)
    gl = B.multibox("sch_glow", [(1.3, 0.03, 1.0, -37.2, 9.35, 3.7, "#ff9a40")])
    T.emissive(gl, 3.0)
    for i, (p, s) in enumerate([((-37.2, 9.0, 4.6), (1.2, 1.0, 0.9)), ((-36.8, 8.6, 5.6), (1.6, 1.4, 1.1)),
                                ((-36.0, 9.2, 6.8), (2.0, 1.6, 1.3)), ((-35.0, 12.0, 4.4), (1.0, 1.0, 0.8)),
                                ((-34.6, 12.4, 5.4), (1.4, 1.3, 1.0)), ((-38.5, 12.0, 8.2), (2.4, 2.0, 1.5)),
                                ((-37.5, 13.0, 9.6), (3.0, 2.4, 1.8)), ((-36.0, 11.0, 7.5), (1.8, 1.5, 1.2))]):
        smoke(kit, f"sch_smoke{i}", p, s)
    # crates under the school windows (kids climb in, scene 32)
    B.multibox("crates", [(0.8, 0.8, 0.55, xx, 8.95, 0.27, "#8a7052") for xx in (-44.6, -39.4, -46.8, -37.2)])
    B.cyl("water_barrel", 0.5, 1.0, (-39.25, 3.4, 0), "#7a5636", seg=10)
    B.cyl("water_barrel_w", 0.44, 0.02, (-39.25, 3.4, 1.0), "#4a7a9a", seg=10)
    B.cyl("water_barrel2", 0.5, 1.0, (-44.45, 6.0, 0), "#7a5636", seg=10)
    # town hall giant window (hidden until the mayor cuts it) + bakery window
    hw = [(0.08, 5.6, 2.9, 0, 0, 0, "#2a2a30"), (0.16, 5.9, 0.18, 0, 0, 1.5, "#f0ece0"), (0.16, 5.9, 0.18, 0, 0, -1.5, "#f0ece0"),
          (0.16, 0.18, 3.1, 0, 2.9, 0, "#f0ece0"), (0.16, 0.18, 3.1, 0, -2.9, 0, "#f0ece0"), (0.14, 0.12, 2.9, 0, 0, 0, "#f0ece0"),
          (0.14, 5.6, 0.12, 0, 0, 0, "#f0ece0"), (0.5, 6.0, 0.12, -0.2, 0, -1.6, "#e2dccb"),
          (0.06, 0.8, 0.5, -0.05, 1.4, -0.9, "#e8c040"), (0.06, 0.6, 0.6, -0.05, -1.5, -0.8, "#58b058")]
    B.multibox("hall_bigwin", hw, loc=(76.36, 0, 5.1))
    bw = [(2.1, 0.06, 1.8, 0, 0, 0, "#2a2a30"), (2.3, 0.12, 0.14, 0, -0.03, 0.95, "#f0ece0"), (2.3, 0.12, 0.14, 0, -0.03, -0.95, "#f0ece0"),
          (0.14, 0.12, 2.0, 1.1, -0.03, 0, "#f0ece0"), (0.14, 0.12, 2.0, -1.1, -0.03, 0, "#f0ece0"), (0.1, 0.1, 1.8, 0, -0.03, 0, "#f0ece0"),
          (0.5, 0.25, 0.2, -0.5, -0.12, -0.85, "#c08a4a"), (0.5, 0.25, 0.2, 0.4, -0.12, -0.85, "#c08a4a")]
    B.multibox("bak_bigwin", bw, loc=(-22.75, 9.95, 1.6))
    # street furniture
    B.fence("yard_n", (-56, 9.6), (-50, 9.6))
    B.fence("yard_n2", (26, 9.6), (56, 9.6))
    B.fence("yard_s", (-64, -9.4), (-14, -9.4))
    B.fence("yard_s2", (35, -9.4), (56, -9.4))
    B.fence("yard_s3", (-6, -9.4), (6, -9.4))
    T.utilities(xs=(-60, -45, -30, -15, 0, 15, 30, 45, 60), y=-6.2, lamps_x=(-52, -27, -6, 7.5, 26, 46, 62),
                barrels_at=[(-25.5, 8.6), (-26.3, 9.3), (-63, 4.6), (-62.2, 5.5), (72, -7), (72.8, -7.7), (35.5, 7.5),
                            (-4, 8.6), (16, -8.5), (5.6, -8.6)])
    T.trees([(-60, -30), (-45, 28), (-8, -30), (12, 30), (42, -28), (55, 26), (-28, 32), (60, -22), (-55, 22), (18, -30),
             (45, 40), (15, 46), (-35, -28), (85, 20), (85, -20), (-70, 10), (-72, -12)], style="B")
    T.sign("door_sign", 66, -9, 90, "DOORS ARE\nPRECIOUS", w=3.0, h=1.1, size=0.3, board="#a3302a")
    # ---------------------------------------------------------------- kitchen (0, 600)
    T.kitchen(KX, KY, soup=False)
    fl = B.multibox("fridge_light", [(1.0, 0.02, 1.9, KX - 4.2, KY + 3.935, 1.05, "#fff6e0")])
    T.emissive(fl, 1.6)
    B.multibox("fridge_food", [(1.0, 0.05, 0.04, KX - 4.2, KY + 3.9, z, "#c8c8c0") for z in (0.6, 1.1, 1.6)] +
               [(0.2, 0.12, 0.25, KX - 4.5, KY + 3.85, 0.75, "#e85a5a"), (0.15, 0.12, 0.3, KX - 4.0, KY + 3.85, 1.27, "#58b058"),
                (0.3, 0.12, 0.15, KX - 3.9, KY + 3.85, 0.7, "#e8c040"), (0.12, 0.12, 0.35, KX - 4.4, KY + 3.85, 1.3, "#f0f0f0")])
    _hinge(B, "fridge", (KX - 4.75, KY + 3.88, 0.02), 0, -100,
           _panel(1.1, 2.06, thick=0.07, col="#e8e4da", knob=False,
                  extra=[(0.06, 0.1, 0.8, 0.98, -0.06, 1.25, "#8a8a8a"), (0.16, 0.02, 0.16, 0.4, -0.04, 1.6, "#e85a5a"),
                         (0.14, 0.02, 0.12, 0.65, -0.04, 1.45, "#3aa0c8")]))
    og = B.multibox("oven_glow", [(0.72, 0.02, 0.52, KX + 1.2, KY + 4.035, 0.5, "#ff8a3a")])
    T.emissive(og, 2.5)
    B.multibox("oven_body", [(0.9, 0.02, 0.8, KX + 1.2, KY + 4.045, 0.5, "#2a2624"), (0.4, 0.3, 0.02, KX + 1.0, KY + 4.4, 1.09, "#2a2624"),
                             (0.4, 0.3, 0.02, KX + 1.5, KY + 4.4, 1.09, "#2a2624")])
    _hinge(B, "oven", (KX + 1.2, KY + 4.0, 0.17), 0, 85,
           [(0.84, 0.06, 0.66, 0, 0, 0.33, "#3e3b38"), (0.5, 0.02, 0.3, 0, -0.035, 0.36, "#5a3a2a"),
            (0.6, 0.07, 0.05, 0, -0.07, 0.6, "#c8c8c0")], axis="x")
    B.multibox("kcloset_in", [(1.0, 0.04, 2.1, KX - 0.9, KY + 4.97, 1.05, "#1c1814"), (0.08, 0.06, 1.6, KX - 1.1, KY + 4.92, 0.8, "#c8a878"),
                              (0.3, 0.08, 0.3, KX - 1.1, KY + 4.92, 0.15, "#e8c040"), (0.25, 0.1, 0.4, KX - 0.6, KY + 4.9, 0.2, "#3aa0c8"),
                              (0.8, 0.1, 0.04, KX - 0.9, KY + 4.92, 1.5, "#8a7052")])
    _hinge(B, "kcloset", (KX - 1.4, KY + 4.9, 0), 0, -100, _panel(1.0, 2.1))
    B.cyl("cake", 0.32, 0.26, (KX, KY + 2.0, 0.96), "#f0b8c8", seg=14)
    B.cyl("cake_top", 0.33, 0.05, (KX, KY + 2.0, 1.2), "#ffffff", seg=14)
    B.multibox("candles", [(0.03, 0.03, 0.14, KX + dx, KY + 2.0 + dy, 1.31, "#3aa0c8") for dx, dy in ((-0.12, 0), (0, 0.1), (0.12, 0), (0, -0.1))])
    cf = B.multibox("candle_flames", [(0.04, 0.04, 0.06, KX + dx, KY + 2.0 + dy, 1.42, "#ffe07a") for dx, dy in ((-0.12, 0), (0, 0.1), (0.12, 0), (0, -0.1))])
    T.emissive(cf, 4.0)
    mug = B.cyl("mug", 0.075, 0.15, (0, 0, -100), "#f2efe6", seg=10)
    B.cyl("mug_coffee", 0.065, 0.01, (0, 0, 0.145), "#5a3a22", seg=10, parent=mug)
    B.multibox("mug_handle", [(0.03, 0.06, 0.09, 0.09, 0, 0.08, "#f2efe6")], parent=mug)
    B.cyl("spill", 0.38, 0.012, (KX + 0.9, KY + 0.15, -100), "#4a2e1a", seg=14)
    B.multibox("bday_banner", [(0.35, 0.04, 0.35, KX - 2.4 + i * 0.55, KY + 4.93, 2.6, ["#e85a5a", "#e8c040", "#3aa0c8", "#58b058"][i % 4])
                               for i in range(8)])
    # ---------------------------------------------------------------- Theo's bedroom (0, -600)
    T.bedroom(BX, BY)
    round_window(kit, "bwin", (BX - 2.6, BY + 3.95, 2.25), -90, 0.42, "#a8b4c0", "#26345a", 0.8, "#6a88b0", 0.15)
    B.multibox("bed_door_frame", [(0.12, 0.12, 2.25, BX - 3.95, BY - 1.66, 1.12, "#5e4430"), (0.12, 0.12, 2.25, BX - 3.95, BY - 0.54, 1.12, "#5e4430"),
                                  (0.12, 1.24, 0.12, BX - 3.95, BY - 1.1, 2.2, "#5e4430")])
    _hinge(B, "bed", (BX - 3.92, BY - 1.6, 0), 90, -95, _panel(1.0, 2.1, thick=0.07))
    B.cyl("bowl", 0.17, 0.1, (BX + 1.6, BY + 1.6, 0.92), "#3aa0c8", seg=12, r2=0.21)
    B.multibox("cereal", [(0.05, 0.05, 0.03, BX + 1.6 + dx, BY + 1.6 + dy, 1.02, "#e8c040") for dx, dy in
                          ((-0.08, 0), (0.05, 0.06), (0.06, -0.07), (-0.02, -0.04), (0.0, 0.09))])
    B.multibox("bed_posters", [(0.04, 1.0, 1.3, BX + 3.96, BY - 1.5, 1.9, "#6a4a30"), (0.03, 0.8, 1.1, BX + 3.93, BY - 1.5, 1.9, "#e8c040"),
                               (0.03, 0.35, 0.35, BX + 3.91, BY - 1.5, 1.95, "#d8b860"),
                               (0.04, 0.9, 0.06, BX + 3.94, BY + 1.0, 1.6, "#5e4430")] +
               [(0.08, 0.08, 0.08, BX + 3.88, BY + 0.7 + 0.2 * i, 1.68, "#d8b860") for i in range(4)])
    B.multibox("desk_lamp", [(0.15, 0.15, 0.04, BX - 2.1, BY + 3.4, 0.84, "#3e3b38"), (0.04, 0.04, 0.4, BX - 2.1, BY + 3.4, 1.05, "#3e3b38")])
    # ---------------------------------------------------------------- school hallway (598..642, -2.2..2.2)
    wm = B.mat("#cdbb98", cull=True)
    T.wall_planes("hall_wall_f", "y", HY0, HX0, HX1, HH, None, 1, wm)
    T.wall_planes("hall_wall_b", "y", HY1, HX0, HX1, HH, None, -1, wm)
    T.wall_planes("hall_wall_l", "x", HX0, HY0, HY1, HH, (-0.8, 0.8, 0.0, 2.6), 1, wm)
    T.wall_planes("hall_wall_r", "x", HX1, HY0, HY1, HH, (-0.6, 0.6, 0.0, 2.3), -1, wm)
    tiles = []
    for i in range(22):
        for j in range(2):
            tiles.append((2.0, 2.2, 0.1, HX0 + 1 + 2 * i, -1.1 + 2.2 * j, 0.05, "#d8d0bc" if (i + j) % 2 == 0 else "#8a9a9a"))
    B.multibox("hall_floor", tiles)
    band = [(44, 0.04, 1.0, 620, HY0 + 0.02, 0.5, "#5f8a78"), (44, 0.04, 1.0, 620, HY1 - 0.02, 0.5, "#5f8a78"),
            (44, 0.05, 0.08, 620, HY0 + 0.03, 1.02, "#3e5a50"), (44, 0.05, 0.08, 620, HY1 - 0.03, 1.02, "#3e5a50")]
    band += [(0.3, 4.4, 0.22, HX0 + 2 + 4 * i, 0, HH - 0.05, "#e8e0cc") for i in range(11)]
    B.multibox("hall_trim", band)
    lp = B.multibox("hall_lightpanels", [(0.6, 1.2, 0.05, HX0 + 4 + 4 * i, 0, HH - 0.18, "#fff7e6") for i in range(10)])
    T.emissive(lp, 2.0)
    for i in range(5):
        T.point_light(f"hall_lamp{i}", (HX0 + 3 + 9 * i, 0, 3.0), 160, (1.0, 0.92, 0.8))
    # curtained classroom doorways (new wing)
    ccols = ["#b0303a", "#3a5a9a", "#3f8a4a", "#d8a838", "#7a4a9a"]
    for k, (cxp, wall) in enumerate([(603, -1), (606, 1), (609, -1), (612, 1), (615, -1)]):
        yw = HY0 if wall < 0 else HY1
        sgn = 1 if wall < 0 else -1       # into the corridor
        B.multibox(f"curt_frame{k}", [(0.15, 0.2, 2.6, cxp - 0.95, yw + sgn * 0.08, 1.3, "#6a4a30"),
                                      (0.15, 0.2, 2.6, cxp + 0.95, yw + sgn * 0.08, 1.3, "#6a4a30"),
                                      (2.05, 0.2, 0.15, cxp, yw + sgn * 0.08, 2.62, "#6a4a30")])
        folds = [(0.31, 0.16 if i % 2 else 0.26, 2.45, -0.78 + i * 0.312, 0, -1.25, ccols[k]) for i in range(6)]
        folds += [(1.95, 0.3, 0.22, 0, 0, -0.08, ccols[(k + 2) % 5]), (2.1, 0.08, 0.08, 0, 0, 0.06, "#3a3a3e")]
        B.multibox(f"curtain{k}", folds, loc=(cxp, yw + sgn * 0.22, 2.55))
    # lockers + notice board
    B.multibox("lockers", [(0.6, 0.45, 1.9, 617.5 + 0.62 * i, HY1 - 0.24, 0.95, "#4a7ab0" if i % 2 else "#3f6a9a") for i in range(8)] +
               [(0.06, 0.05, 0.25, 617.7 + 0.62 * i, HY1 - 0.48, 1.0, "#c8c8c0") for i in range(8)] +
               [(2.0, 0.05, 1.2, 618.5, HY0 + 0.03, 1.8, "#8a6a4a"), (0.4, 0.03, 0.5, 618.0, HY0 + 0.06, 1.85, "#f0ece4"),
                (0.4, 0.03, 0.4, 618.8, HY0 + 0.06, 1.7, "#e8c040"), (0.35, 0.03, 0.4, 619.2, HY0 + 0.06, 2.05, "#e870a0")])
    # alarm bell
    bell = B.cyl("hall_bell", 0.22, 0.2, (606.0, HY1 - 0.12, 2.85), "#c8302a", seg=12, r2=0.06, rot=(math.radians(-90), 0, 0))
    B.multibox("hall_bell_base", [(0.3, 0.05, 0.3, 606.0, HY1 - 0.03, 2.85, "#3a3a3e")])
    # exit door (heavy, pulls inward) + bright outside behind it
    B.multibox("exit_frame", [(0.2, 0.15, 2.75, HX0 + 0.05, -0.9, 1.37, "#4f3a28"), (0.2, 0.15, 2.75, HX0 + 0.05, 0.9, 1.37, "#4f3a28"),
                              (0.2, 1.95, 0.16, HX0 + 0.05, 0, 2.68, "#4f3a28")])
    es = B.multibox("exit_sign", [(0.06, 0.9, 0.32, HX0 + 0.04, 0, 3.0, "#2fae5a")])
    T.emissive(es, 2.0)
    B.text("exit_sign_txt", "EXIT", (HX0 + 0.09, 0, 3.0), -math.pi / 2, 0.22, "#ffffff")
    out = B.multibox("exit_outside", [(0.1, 3.4, 3.4, HX0 - 1.6, 0, 1.7, "#fff1d0")])
    T.emissive(out, 2.2)
    B.multibox("exit_grass", [(1.6, 3.4, 0.05, HX0 - 0.8, 0, 0.03, "#7fa04e")])
    _hinge(B, "exit", (HX0 + 0.1, -0.8, 0), 90, -95,
           [(1.6, 0.12, 2.6, 0.8, 0, 1.3, "#5e4028"), (1.5, 0.14, 0.12, 0.8, 0, 0.6, "#3a3a3e"),
            (1.5, 0.14, 0.12, 0.8, 0, 2.0, "#3a3a3e"), (0.12, 0.26, 0.42, 1.42, 0.07, 1.12, "#c8a85a"),
            (0.4, 0.14, 0.4, 0.4, 0, 1.6, "#4d5f6e")])
    # old wing: real doors (classroom, closet, janitor) + art room door at the far end
    for nm, cxp, wall, label in (("hd_class4", 624, -1, "CLASS 4"), ("hd_class5", 628, 1, "CLASS 5"),
                                 ("hd_closet", 632, -1, "CLOSET"), ("hd_janitor", 636, 1, "JANITOR")):
        yw = HY0 if wall < 0 else HY1
        sgn = 1 if wall < 0 else -1
        B.multibox(nm + "_frame", [(1.1, 0.03, 2.2, cxp, yw + sgn * 0.02, 1.1, "#1c1814"),
                                   (0.14, 0.16, 2.35, cxp - 0.62, yw + sgn * 0.08, 1.17, "#4f3a28"),
                                   (0.14, 0.16, 2.35, cxp + 0.62, yw + sgn * 0.08, 1.17, "#4f3a28"),
                                   (1.38, 0.16, 0.14, cxp, yw + sgn * 0.08, 2.3, "#4f3a28"),
                                   (1.2, 0.05, 0.35, cxp, yw + sgn * 0.03, 2.65, "#f0ece4")])
        B.text(nm + "_label", label, (cxp, yw + sgn * 0.07, 2.65), math.pi if wall < 0 else 0.0, 0.17, "#2a2a30")
        _hinge(B, nm, (cxp - 0.55, yw + sgn * 0.1, 0), 0, 95 * sgn,
               _panel(1.1, 2.18, col="#7a5534" if "class" in nm else "#5e6a72",
                      extra=[(0.4, 0.1, 0.5, 0.55, 0, 1.6, "#9cc4dc")] if "class" in nm else []))
    B.multibox("art_end_frame", [(0.16, 0.14, 2.45, HX1 - 0.06, -0.68, 1.22, "#4f3a28"), (0.16, 0.14, 2.45, HX1 - 0.06, 0.68, 1.22, "#4f3a28"),
                                 (0.16, 1.5, 0.14, HX1 - 0.06, 0, 2.4, "#4f3a28"), (0.05, 1.4, 0.35, HX1 - 0.03, 0, 2.75, "#f0ece4")])
    B.text("art_end_label", "ART ROOM", (HX1 - 0.07, 0, 2.75), math.pi / 2, 0.17, "#2a2a30")
    B.multibox("art_end_beyond", [(0.1, 2.0, 2.6, HX1 + 0.8, 0, 1.3, "#3a3030")])
    _hinge(B, "art_end", (HX1 - 0.1, -0.6, 0), 90, 95, _panel(1.2, 2.28))
    for i, (p, s) in enumerate([((639.0, 0.5, 3.0), (2.8, 2.6, 0.8)), ((634.0, -0.6, 3.05), (3.2, 2.8, 0.7)),
                                ((628.5, 0.8, 3.1), (2.6, 2.4, 0.6)), ((623.0, -0.4, 3.12), (2.8, 2.6, 0.55)),
                                ((617.0, 0.6, 3.15), (2.4, 2.4, 0.5)), ((611.0, -0.5, 3.18), (2.2, 2.2, 0.45)),
                                ((605.0, 0.4, 3.2), (2.0, 2.0, 0.4)), ((640.5, -1.0, 2.2), (1.4, 1.4, 1.4)),
                                ((636.5, 1.2, 2.5), (1.6, 1.4, 1.0))]):
        smoke(kit, f"hall_smoke{i}", p, s)
    # ---------------------------------------------------------------- art room (600, 600)
    am = B.mat("#cdbb98", cull=True)
    ax0, ax1, ay0, ay1 = AX - 4, AX + 4, AY - 3.5, AY + 3.5
    T.wall_planes("art_wall_f", "y", ay0, ax0, ax1, AH, (601.0, 602.2, 0.0, 2.3), 1, am)
    T.wall_planes("art_wall_b", "y", ay1, ax0, ax1, AH, None, -1, am)
    T.wall_planes("art_wall_l", "x", ax0, ay0, ay1, AH, None, 1, am)
    T.wall_planes("art_wall_r", "x", ax1, ay0, ay1, AH, None, -1, am)
    B.multibox("art_floor", [(8, 7, 0.1, AX, AY, 0.05, "#9a9488")] +
               [(0.5, 0.4, 0.01, AX + dx, AY + dy, 0.105, c) for dx, dy, c in
                ((1.2, -0.5, "#e85a5a"), (-0.6, 1.1, "#3aa0c8"), (2.0, 1.6, "#e8c040"), (0.3, -1.8, "#58b058"))])
    B.multibox("art_band", [(8, 0.04, 0.9, AX, ay0 + 0.02, 0.45, "#5f8a78"), (8, 0.04, 0.9, AX, ay1 - 0.02, 0.45, "#5f8a78"),
                            (0.04, 7, 0.9, ax0 + 0.02, AY, 0.45, "#5f8a78"), (0.04, 7, 0.9, ax1 - 0.02, AY, 0.45, "#5f8a78")])
    sh = [(0.1, 0.55, 2.6, 598.3, 603.2, 1.3, "#6a4a30"), (0.1, 0.55, 2.6, 601.7, 603.2, 1.3, "#6a4a30"),
          (0.1, 0.55, 2.6, 600.0, 603.2, 1.3, "#6a4a30")]
    sh += [(3.5, 0.55, 0.07, 600.0, 603.2, z, "#7a5534") for z in (0.05, 0.68, 1.31, 1.94, 2.6)]
    pc = ["#e85a5a", "#3aa0c8", "#e8c040", "#58b058", "#9a6ad0", "#f09a4a", "#ffffff", "#e870a0"]
    k = 0
    for z in (0.09, 0.72, 1.35, 1.98):
        for i in range(8):
            xx = 598.55 + i * 0.4 + (0.2 if i >= 4 else 0) - (0.1 if i >= 4 else 0)
            if abs(xx - 600.0) < 0.15:
                continue
            sh.append((0.2, 0.2, 0.26 if (i + k) % 2 else 0.2, xx, 603.1, z + 0.13, pc[(i + k) % 8]))
        k += 3
    B.multibox("art_shelves", sh)
    round_window(kit, "awin", (AX, ay1 - 0.03, 4.25), -90, 0.5, "#cdbb98", "#cfe8ff", 1.6, "#a8d0ec", 0.25)
    B.multibox("art_table", [(2.4, 1.3, 0.08, 600.2, 599.4, 0.78, "#8a6a4a")] +
               [(0.08, 0.08, 0.76, 600.2 + sx, 599.4 + sy, 0.38, "#5e4028") for sx in (-1.1, 1.1) for sy in (-0.55, 0.55)] +
               [(0.18, 0.18, 0.16, 599.5 + 0.35 * i, 599.3 + 0.2 * (i % 2), 0.9, pc[i]) for i in range(5)] +
               [(0.7, 0.5, 0.02, 600.6, 599.6, 0.83, "#f0ece4")])
    B.multibox("art_easels", [(0.08, 0.08, 1.8, 602.6, 600.6, 0.9, "#7a5534"), (0.9, 0.06, 0.7, 602.6, 600.55, 1.4, "#f0ece4"),
                              (0.5, 0.03, 0.35, 602.5, 600.5, 1.45, "#3aa0c8"), (0.25, 0.03, 0.25, 602.8, 600.5, 1.3, "#e8c040"),
                              (0.08, 0.08, 1.8, 602.9, 602.2, 0.9, "#7a5534"), (0.9, 0.06, 0.7, 602.9, 602.15, 1.4, "#f0ece4"),
                              (0.4, 0.03, 0.4, 602.85, 602.1, 1.45, "#e870a0")])
    B.multibox("art_drawings", [(0.04, 0.6, 0.5, ax1 - 0.03, 598.0 + 0.9 * i, 2.4 + 0.2 * (i % 2), pc[(i * 3) % 8]) for i in range(5)])
    B.multibox("art_burnt", [(1.6, 1.0, 0.7, 597.2, 600.8, 0.35, "#3a3030"), (0.5, 0.5, 0.9, 596.8, 602.3, 0.45, "#3a3030"),
                             (0.6, 0.7, 0.5, 597.0, 599.0, 0.25, "#3a3030")])
    for i, (p, s) in enumerate([((597.2, 600.8, 0.7), 1.0), ((596.8, 602.3, 0.9), 0.75), ((597.0, 599.0, 0.5), 0.8),
                                ((597.8, 601.6, 0.0), 0.6)]):
        flame(kit, f"art_fire{i}", p, s)
    T.point_light("art_firelight", (597.8, 600.6, 1.6), 450, (1.0, 0.55, 0.25))
    T.point_light("art_lamp", (601.5, 599.0, 4.6), 260, (1.0, 0.92, 0.82))
    for i, (p, s) in enumerate([((597.5, 600.5, 3.4), (2.0, 2.2, 1.0)), ((597.2, 602.0, 4.3), (2.2, 2.0, 1.1)),
                                ((598.6, 598.5, 4.1), (2.0, 2.0, 0.9)), ((602.6, 598.2, 4.6), (2.0, 2.2, 0.8)),
                                ((602.8, 601.5, 4.4), (1.8, 1.8, 0.9)), ((597.0, 598.0, 2.6), (1.4, 1.4, 1.0)),
                                ((599.8, 597.6, 4.7), (2.2, 1.8, 0.7))]):
        smoke(kit, f"art_smoke{i}", p, s)
    B.multibox("art_beyond", [(2.6, 0.1, 3.2, 601.6, 595.7, 1.6, "#cdbb98"), (2.6, 0.12, 1.0, 601.6, 595.76, 0.5, "#5f8a78")])
    B.multibox("art_frame", [(0.14, 0.16, 2.42, 600.93, 596.55, 1.21, "#4f3a28"), (0.14, 0.16, 2.42, 602.27, 596.55, 1.21, "#4f3a28"),
                             (1.48, 0.16, 0.14, 601.6, 596.55, 2.37, "#4f3a28")])
    _hinge(B, "art", (601.0, 596.6, 0), 0, 95, _panel(1.2, 2.28, col="#7a5534", extra=[(0.09, 0.2, 0.09, 1.06, 0, 1.05, "#d8b860")]))
    # ceilings (no shadow casting, so daylight still fills the rooms) hide the outdoor horizon over interior walls
    for nm, (x0, x1, y0, y1, z) in {"kit_ceil": (KX - 5, KX + 5, KY - 5, KY + 5, 3.2), "bed_ceil": (BX - 4, BX + 4, BY - 4, BY + 4, 3.2),
                                    "hall_ceil": (HX0, HX1, HY0, HY1, HH), "art_ceil": (ax0, ax1, ay0, ay1, AH)}.items():
        c = B.poly(nm, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], [(3, 2, 1, 0)], B.mat("#e8e0cc", cull=True))
        c.visible_shadow = False
    # buckets for the bucket line
    for i in range(BUCKETS):
        bk = B.cyl(f"bucket{i}", 0.17, 0.3, (0, 0, -100), "#5f86c8", seg=10, r2=0.2)
        B.cyl(f"bucket{i}_w", 0.18, 0.02, (0, 0, 0.29), "#4a7a9a", seg=10, parent=bk)


# ------------------------------------------------------------------ per-frame hook
def _ang(state, t, dur, full):
    from render import smooth
    if state in (None, "closed"):
        return 0.0
    if state == "open":
        return full
    if state == "opening":
        return full * smooth((t - 0.1) / max(0.3, min(0.9, dur * 0.6)))
    if state == "closing":
        return full * (1 - smooth((t - 0.15) / 0.45))
    if state == "rattle":
        return full * 0.015 * math.sin(38 * t)
    if state == "twice":
        u = t / max(dur, 0.1)
        if u < 0.3:
            return full * smooth(u / 0.3)
        if u < 0.55:
            return full * (1 - smooth((u - 0.3) / 0.25))
        return full * smooth((u - 0.55) / 0.3)
    if isinstance(state, (int, float)):
        return full * state
    return 0.0


def apply(stage, sh, t, gt):
    from mathutils import Vector
    from render import smooth
    ob = stage.ob
    s, dur = sh["set"], sh["dur"]
    sid = sh["sentence"]
    idx = sidx(sid)
    # ---- doors + windows
    doors = sh.get("doors", {})
    if not HINGES:
        for o in ob:
            if "hk" in o:
                hk = list(o["hk"])
                HINGES[o.name] = ("x" if hk[0] > 0.5 else "z", float(hk[1]), float(hk[2]))
    for h, (axis, base, full) in HINGES.items():
        if h not in ob:
            continue
        st = doors.get(h, SET_DOORS.get(s, {}).get(h, default_door(h, idx)))
        a = math.radians(_ang(st, t, dur, full))
        if axis == "z":
            ob[h].rotation_euler.z = math.radians(base) + a
        else:
            ob[h].rotation_euler.x = a
    # ---- big windows (mayor + baker)
    for nm, key, after in (("hall_bigwin", "bigwin", I("s31")), ("bak_bigwin", "bakwin", I("s31"))):
        mode = sh.get(key)
        o = ob[nm]
        if mode == "cut":
            k = max(0.02, smooth((t - 0.15) / max(0.4, dur * 0.7)))
            o.hide_render = False
            o.scale = (1, k, k) if nm == "hall_bigwin" else (k, 1, k)
        elif mode == "on" or idx > after:
            o.hide_render = False
            o.scale = (1, 1, 1)
        else:
            o.hide_render = True
    # ---- fire + smoke
    lvl = SMOKE.get(sid if sid in SENT_IDS else "", 0.0)
    lvl = sh.get("smoke", lvl)
    for o in ob:
        n = o.name
        if n.startswith(("art_fire", "art_smoke", "hall_smoke", "sch_smoke")) and o.type == "MESH":
            on = lvl > 0
            o.hide_render = not on
            if not on:
                continue
            k = int("".join(c for c in n if c.isdigit()) or 0)
            if "base" not in o:
                o["base"] = tuple(o.location)
            bx, by, bz = o["base"]
            if n.startswith("art_fire"):
                o.scale = (1 + 0.06 * math.sin(9 * gt + k), 1 + 0.06 * math.cos(8 * gt + 2 * k),
                           1 + 0.22 * math.sin(13 * gt + 1.7 * k) + 0.1 * math.sin(29 * gt + k))
            else:
                g = (0.55 + 0.45 * lvl) * (1 + 0.08 * math.sin(1.3 * gt + k))
                o.scale = (g, g, g)
                drift = 0.25 * math.sin(0.6 * gt + k)
                rise = (0.5 * ((0.35 * gt + 0.13 * k) % 1.0)) if n.startswith("sch_smoke") else 0.08 * math.sin(0.9 * gt + k)
                o.location = (bx + drift, by + 0.15 * math.cos(0.7 * gt + k), bz + rise)
    if "art_firelight" in ob:
        ob["art_firelight"].data.energy = 450 * (1 + 0.25 * math.sin(17 * gt) + 0.12 * math.sin(31 * gt + 1))
    ob["sch_glow"].hide_render = lvl <= 0 or idx > I("s30")
    # ---- curtains sway (wind in scene 17), alarm bell shake
    amp = 0.16 if sid == "s17" else 0.035
    for k in range(5):
        c = ob[f"curtain{k}"]
        c.rotation_euler.x = amp * math.sin(1.7 * gt + k * 1.3) * (1 if k % 2 == 0 else -1)
    ob["hall_bell"].rotation_euler.y = (0.25 * math.sin(60 * t)) if sh.get("bell") else 0.0
    # ---- Dad's coffee mug
    mug, spill = ob["mug"], ob["spill"]
    mstate = sh.get("mug", {"k_bday": "hold", "k_talk": "floor"}.get(s))
    spill.location.z = -100
    if mstate in ("hold", "drop") and ob["dad_root"].location.z > -50:
        hp = stage.hand_pos("dad")
        p = hp + Vector((0, 0, -0.02))
        if mstate == "drop":
            u = max(0.0, t - dur * 0.35)
            p.z = max(0.07, p.z - 4.9 * u * u)
            mug.rotation_euler = (min(1.6, 2.5 * u), 0, 0.4)
            if p.z <= 0.08:
                spill.location.z = 0.01
                spill.scale = (min(1.0, 0.2 + 3 * (u - 0.45)),) * 3
        else:
            mug.rotation_euler = (0, 0, 0.4)
        mug.location = p
    elif mstate == "floor":
        mug.location = (KX + 0.75, KY + 0.05, 0.08)
        mug.rotation_euler = (1.57, 0, 0.9)
        spill.location.z = 0.01
        spill.scale = (1, 1, 1)
    else:
        mug.location = (0, 0, -100)
    # ---- buckets for the bucket line
    line = [n for n in BUCKET_LINE if s == "bucket" and ob[n + "_root"].location.z > -50]
    for i in range(BUCKETS):
        b = ob[f"bucket{i}"]
        if i < len(line):
            hp = stage.hand_pos(line[i])
            b.location = hp + Vector((0, 0, -0.32 + 0.05 * math.sin(5 * gt + i)))
        else:
            b.location = (0, 0, -100)
    # ---- Theo jumps out of the school's round window (scene 28)
    if sh.get("jump") and "theo_root" in ob:
        r = ob["theo_root"]
        u = max(0.0, t - 0.15)
        x0, y0 = -35.15, 12.0
        r.location = (x0 + min(2.2, 2.6 * u), y0, max(0.0, 3.0 + 1.2 * u - 4.9 * u * u))
        r.rotation_euler.x = -0.25 * min(1.0, u * 2)


def cam_override(stage, sh, t, actors, T, f, u):
    v = sh.get("view")
    if not v or v not in VIEWS:
        return None
    from mathutils import Vector
    a, b, look, lens = VIEWS[v]
    pos = Vector(a).lerp(Vector(b), u)
    if isinstance(look, str):
        nm, _, part = look.partition("@")
        if part == "hand":
            L = stage.hand_pos(nm)
        elif part == "chest":
            L = stage.ob[nm + "_torso"].matrix_world @ Vector((0, 0.3, 1.43))
        else:
            L = stage.head_pos(nm)
    else:
        L = Vector(look)
    return pos, L, lens
