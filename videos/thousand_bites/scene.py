"""In This Town, You Get 1,000 Bites - set dressing, cast, blocking (Style B, chest bite counters)."""
import math

# ------------------------------------------------------------------ cast (start = counter value at t=0)
CAST = {
    "maya":   dict(shirt="#e8507a", pants="#3a4f80", hair="#4a2a1a", skin="#e8c4a0", scale=0.78, kind="kid",
                   held=["loaf", "thermos"], start=868),
    "rue":    dict(shirt="#8a6aa8", pants="#6a5878", hair="#e4e0d8", skin="#ecccae", scale=0.9, kind="granny",
                   held=["thermos"], start=4),
    "mom":    dict(shirt="#4a9a8a", pants="#5c4a40", hair="#6a4428", skin="#e6c4a0", scale=0.98, kind="mom",
                   held=["thermos"], start=412),
    "doctor": dict(shirt="#7aa0c8", pants="#4a5262", hair="#2b211a", skin="#c49670", scale=1.0, kind="doctor", start=530),
    "baker":  dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker",
                   held=["crumb", "loaf"], start=377),
    "mayor":  dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor", start=601),
    "baby":   dict(shirt="#f0d060", pants="#f0d060", hair="#8a5a3a", skin="#f0d0b0", scale=0.5, kind="baby", start=1000),
    "t1":     dict(shirt="#d0563a", pants="#4f4436", hair="#2b211a", skin="#aa7a58", scale=0.98, kind="plain",
                   held=["thermos"], start=702),
    "t2":     dict(shirt="#3f8fc0", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="plain",
                   held=["crumb", "thermos"], start=455),
    "t3":     dict(shirt="#5aa05a", pants="#3e4652", hair="#1f1a16", skin="#96684a", scale=1.0, kind="plain",
                   held=["thermos"], start=318),
    "t4":     dict(shirt="#8a8a90", pants="#4d4234", hair="#d0ccc4", skin="#cca078", scale=1.0, kind="plain",
                   held=["loaf"], start=0),
    "t5":     dict(shirt="#e0b030", pants="#3f3a36", hair="#c09060", skin="#e6c4a0", scale=1.0, kind="plain",
                   held=["loaf", "thermos"], start=644),
    "t6":     dict(shirt="#9a5ab0", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain",
                   held=["thermos"], start=520),
    "t7":     dict(shirt="#30b0a0", pants="#3a4a6a", hair="#2a1a12", skin="#c49670", scale=0.76, kind="kid",
                   held=["thermos"], start=731),
    "t8":     dict(shirt="#e07830", pants="#4a3a5a", hair="#c8a060", skin="#f0d0b0", scale=0.74, kind="kid",
                   held=["thermos"], start=389),
}
HATS = {"mayor", "baker"}
DEFAULT_FACE = {"t4": "tired"}

KX, KY = 0.0, 600.0       # kitchen (Maya's home)
BX, BY = 0.0, -600.0      # Maya's bedroom (night)
RX, RY = 600.0, 0.0       # restaurant
CX, CY = 600.0, 60.0      # school cafeteria
KNEEL = 0.75              # how far a kneeling actor sinks (x scale): legs go below the street

# ------------------------------------------------------------------ sets
STREET = {"t1": (-6, -2.6, 85, "idle", 0), "t3": (-2.5, -3.0, 95, "idle", 0), "t6": (3, -2.8, 80, "idle", 0),
          "t5": (8, 1.5, 180, "walk", 0), "t2": (14, -0.8, 180, "walk", 0), "mayor": (-12, 2.2, -10, "walk", 0)}
PARADE = {"rue": (1.0, 0.3, 0, "walk", 0), "maya": (0.4, -1.1, 0, "walk", 0), "t3": (11.0, -1.4, 0, "idle", 0),
          "t1": (2, 4.8, -90, "clap", 0), "t2": (5, 5.0, -90, "wave", 0), "t6": (8, 4.8, -95, "clap", 0),
          "mom": (-2.2, 4.9, -80, "wave", 0), "mayor": (-5.2, 5.2, -80, "wave", 0), "doctor": (11, 5.0, -100, "idle", 0),
          "t5": (0, -5.0, 90, "clap", 0), "t8": (3, -5.2, 90, "wave", 0), "t7": (6, -5.0, 85, "clap", 0),
          "baker": (-3, -5.0, 95, "idle", 0)}
RING = {"t1": (8.6, 2.4, -120, "idle", 0), "t2": (9.6, 0.6, 175, "idle", 0), "t6": (9.2, -1.9, 140, "idle", 0),
        "mom": (3.0, -2.5, 45, "idle", 0), "baker": (3.0, 2.2, -35, "idle", 0), "mayor": (6.4, 3.1, -95, "idle", 0),
        "t3": (10.6, -0.6, 175, "idle", 0), "t5": (2.3, 0.4, -5, "idle", 0), "t7": (7.6, -2.9, 105, "idle", 0),
        "t8": (5.2, -3.1, 85, "idle", 0), "doctor": (5.2, 1.35, -90, "idle", 0)}
SETS = {
    "town": {"t1": (-10, -1.5, 0, "walk", 0), "t2": (12, 1.6, 180, "walk", 0), "t3": (24, -2.5, 90, "idle", 0),
             "t5": (-30, 2, 0, "walk", 0), "t6": (40, -1, 180, "walk", 0), "mom": (-2, 2.5, 0, "walk", 0),
             "maya": (2, -2, 90, "idle", 0), "t7": (-20, 5.4, -90, "idle", 0), "mayor": (64, 0, 180, "idle", 0.6)},
    "street": dict(STREET),
    "born": {"baby": (-10, -8.6, 90, "idle", 0.62), "mom": (-11.5, -7.9, 20, "idle", 0), "t2": (-6, -2.6, 150, "idle", 0)},
    "eat": {"t2": (4, -2.6, 90, "eat:crumb", 0), "t6": (7.5, 1.4, 180, "walk", 0), "t1": (-1.5, -3.0, 70, "idle", 0)},
    "stone": {"t4": (-14, -2.8, 90, "eat:loaf", 0), "t1": (-16.2, -3.2, 50, "idle", 0), "t5": (-9, 1.6, 180, "walk", 0)},
    "share": {"t5": (8, -2.6, 20, "give:loaf", 0), "t6": (9.7, -2.3, 170, "shake", 0), "t3": (12.2, -3.2, 110, "idle", 0),
              "t1": (4.4, 1.8, -20, "hold", 0), "t2": (14.5, 1.4, -90, "eat:crumb", 0)},
    "yard": {"t7": (-30, 29.4, -90, "talk", 0), "t1": (-32.4, 27.4, 30, "idle", 0), "t2": (-27.6, 27.3, 150, "idle", 0),
             "t3": (-33.3, 29.2, -20, "idle", 0), "mom": (-26.8, 29.0, 200, "idle", 0), "t8": (-28.4, 30.6, -100, "idle", 0)},
    "restaurant": {"t1": (RX - 3.7, RY + 0.9, -60, "sit", 0), "t3": (RX - 2.3, RY + 0.9, -120, "sit", 0),
                   "t6": (RX + 2.4, RY + 0.95, -90, "sit", 0), "mayor": (RX + 3.8, RY + 0.6, -150, "sit", 0),
                   "t5": (RX + 0.2, RY + 3.0, -90, "idle", 0)},
    "bakery": {"baker": (-20, 8.7, -90, "idle", 0), "t3": (-21.2, 5.6, 70, "idle", 0), "t1": (-14, 1.8, 180, "walk", 0)},
    "school": {"t7": (-44, 0.5, 90, "walk", 0), "t8": (-40.6, 0.0, 95, "walk", 0), "maya": (-42.2, -1.6, 90, "walk", 0)},
    "cafeteria": {"t7": (CX - 2.4, CY + 1.0, -90, "look_down", 0), "maya": (CX, CY + 1.0, -90, "look_down", 0),
                  "t8": (CX + 2.4, CY + 1.0, -90, "look_down", 0), "t5": (CX + 4.4, CY + 3.6, -100, "idle", 0)},
    "maya_street": {"maya": (0, -2.0, 90, "idle", 0), "t1": (-5, -2.6, 80, "idle", 0), "t6": (4.5, -2.8, 100, "idle", 0),
                    "t2": (10, 1.5, 180, "walk", 0), "t5": (-9, 1.8, 0, "walk", 0)},
    "kitchen": {"maya": (KX, KY + 3.35, -90, "eat:loaf", 0), "mom": (KX + 2.6, KY + 3.6, 200, "laugh", 0)},
    "kitchen_stand": {"maya": (KX - 0.5, KY + 0.4, -70, "idle", 0), "mom": (KX + 0.9, KY + 0.9, 215, "idle", 0)},
    "bedroom": {"maya": (BX + 2.4, BY + 2.85, -90, "idle", 0.33), "rue": (BX + 0.3, BY - 0.6, -45, "hold:thermos", 0)},
    "bedroom_alone": {"maya": (BX + 2.4, BY + 2.85, -90, "drink:thermos", 0.33)},
    "rue_street": {"rue": (-21.4, 5.2, 60, "shake", 0), "baker": (-20, 8.7, -90, "give:loaf", 0),
                   "t3": (-17.4, 5.0, 120, "idle", 0), "t2": (-24.5, 2.0, 0, "walk", 0)},
    "parade": dict(PARADE),
    "collapse": dict(RING, rue=(7.0, 0.0, 0, "lie", 0), maya=(4.0, -2.0, 60, "idle", 0)),
    "kneel": dict(RING, rue=(7.6, 0.1, 0, "lie", 0), maya=(5.0, -0.85, 90, "give:loaf", 0),
                  doctor=(7.4, 1.3, -100, "idle", 0)),
    "situp": dict(RING, rue=(5.6, 0.2, -60, "sit", -0.56), maya=(4.5, -1.0, 40, "give:thermos", 0),
                  doctor=(7.4, 1.3, -100, "idle", 0)),
    "bakery_run": {"maya": (-5.5, 1.2, 149, "run", 0)},
    "bakery_grab": {"maya": (-18.0, 8.9, 120, "hold:loaf", 0)},
    "corners": {"t1": (25.2, 3.8, -80, "drink", 0), "t2": (27.0, 3.6, -100, "drink", 0),
                "mom": (33.2, 3.8, -95, "drink", 0), "t6": (35.0, 3.6, -80, "drink", 0),
                "baker": (34.0, 7.4, -90, "talk", 0), "t3": (7.0, -3.6, 90, "drink", 0), "t5": (8.8, -3.4, 75, "drink", 0),
                "t7": (-30.8, -3.6, 90, "drink", 0), "t8": (-29.2, -3.5, 95, "drink", 0),
                "maya": (-8.8, 3.8, -90, "drink:thermos", 0), "rue": (-7.2, 3.7, -85, "drink", 0),
                "mayor": (60.5, -4.0, 90, "drink", 0), "doctor": (-10.6, 3.4, -70, "drink", 0)},
    "dog_royal": {"t1": (44.0, -5.0, -150, "idle", 0), "t6": (47.6, -5.2, -30, "idle", 0), "mayor": (45.8, -3.0, -90, "nod", 0)},
    "sniff": {"mayor": (-4, -4.4, 90, "idle", 0), "t2": (-4.6, 6.0, -90, "eat:crumb", 0)},
    "trade": {"t7": (-40, 2.6, 0, "give", 0), "t8": (-38.4, 2.6, 180, "hold", 0)},
}
INTERIOR_SETS = {"restaurant", "cafeteria", "kitchen", "kitchen_stand", "bedroom", "bedroom_alone"}
SET_MOOD = {"restaurant": "interior", "cafeteria": "interior", "kitchen": "interior", "kitchen_stand": "interior",
            "bedroom": "night", "bedroom_alone": "night"}
LIGHTS = {"kitchen_lamp": {"kitchen", "kitchen_stand"}, "bedroom_lamp": {"bedroom", "bedroom_alone"},
          "bed_lamp": {"bedroom", "bedroom_alone"}, "rest_lamp": {"restaurant"}, "rest_lamp2": {"restaurant"},
          "caf_lamp": {"cafeteria"}}
SITTERS = {"kitchen": {"maya"}, "bedroom": {"maya"}, "bedroom_alone": {"maya"}, "cafeteria": {"t7", "maya", "t8"}}
KNEELERS = {"kneel": {"maya", "doctor"}, "situp": {"maya", "doctor"}, "collapse": {"doctor"}}
DOG = {"parade": (14.0, -0.4, -90, 1.02), "collapse": (9.0, -3.6, -100, 0), "kneel": (9.0, -3.6, -100, 0),
       "situp": (9.0, -3.6, -100, 0), "corners": (26.1, 1.6, -90, 0), "dog_royal": (45.8, -6.0, -90, 0.55),
       "town": (-8, -2.4, 0, 0)}
HOME_SETS = {"kitchen", "kitchen_stand", "bedroom", "bedroom_alone", "cafeteria"}

PROPS = {
    "cake_y": (-30, 28, 1.2, -90), "grape": (RX - 3, RY, 1.0, -90), "rsoup": (RX - 3, RY, 1.05, -90),
    "plate": (-20, 7.3, 1.36, -90), "price": (-19.2, 6.95, 1.2, -90), "school_sign": (-42, 9.3, 4.3, -90),
    "bell": (CX - 3, CY + 4.85, 2.35, -90), "tray": (CX, CY + 0.35, 0.86, -90),
    "pancakes": (KX - 0.75, KY + 2.15, 1.12, -90), "melon": (KX + 0.75, KY + 2.05, 1.22, -90),
    "sandwich": (KX, KY + 1.55, 1.15, -90), "kcake": (KX, KY + 2.0, 1.25, -90), "pea": (KX, KY + 1.6, 1.0, -90),
    "window": (-21.3, 9.8, 1.3, -90), "float": (16, -0.4, 2.4, -90), "banner": (7.5, 6.2, 5.6, -90),
    "pot_a": (26, 5.9, 1.8, -90), "pot_d": (-8, 5.9, 1.8, -90), "hall_sign": (74.7, 0, 6.2, 180),
    "blend": (-30.3, 28, 1.35, -90), "bsoup": (-20, 7.3, 1.35, -90), "crib": (-10, -8.6, 0.9, 90),
    "dog": ("dog_headpt", 0, 0, (0.0, -90)), "bedthermos": (BX + 1.0, BY + 3.3, 1.0, -90),
    "rest_sign": (RX, RY + 4.9, 2.6, -90),
}
FAR_PROPS = {"school_sign", "hall_sign", "banner"}

# toggle groups: objects named grp_<group>_* are visible only when the group is shown
SHOW_DEFAULT = {"kitchen": ["feast"], "restaurant": ["grape"], "yard": ["ycake"], "kitchen_stand": ["kcake"]}


def sent_no(sh):
    s = sh.get("sentence", "s00")
    try:
        return int("".join(ch for ch in s[1:3] if ch.isdigit()))
    except ValueError:
        return 0


def shown_groups(sh):
    g = set(sh.get("show", SHOW_DEFAULT.get(sh.get("set"), [])))
    n = sent_no(sh) if str(sh.get("sentence", "")).startswith("s") else 0
    if 18 <= n <= 32:
        g.add("parade")
    if n >= 33:
        g.add("stands")
    return g


# ------------------------------------------------------------------ build
def build(kit):
    T, B = kit.town, kit.blocks
    mb, cyl, text, empty = B.multibox, B.cyl, B.text, B.empty

    def G(group, name):
        return f"grp_{group}_{name}"

    T.ground(roads=[(0, 0, 152, 8), (30, 34, 6, 60)], plazas=[(66, 0, 26, 26)],
             keep_clear=[(26, 34, 3, 64), (-36, -24, 22, 34)])
    T.houses(north=[-64, -6, 8, 18, 40, 48], south=[-60, -50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50])
    T.bakery(-20, 14)
    T.school(-42, 14)
    T.town_hall(82, 0, podium=(66.6, 0))
    for i, yy in enumerate((24, 34, 46)):
        B.house(f"cross_w{i}", 22, yy, 0, w=6, d=6.5, h=3.4)
        B.house(f"cross_e{i}", 38, yy, 180, w=6, d=6.5, h=3.4)
    T.sign("main_sign", 25.6, 5.4, -90, "MAIN ST", w=2.6, h=0.6, post=2.75, board="#4f6b4a", size=0.36)
    B.fence("yard_n", (-56, 9.6), (-49, 9.6))
    B.fence("yard_n2", (12.5, 9.6), (14.0, 9.6))
    B.fence("yard_s", (-56, -9.4), (-14, -9.4))
    B.fence("yard_s2", (-6, -9.4), (56, -9.4))
    T.utilities(xs=(-60, -45, -30, -15, 0, 15, 30, 45, 60), y=-6.2, lamps_x=(-52, -34, -12, 22, 44, 58),
                barrels_at=[(-25.5, 8.6), (-26.3, 9.3), (35.5, 7.5), (-4, 8.6), (16, -8.5), (5.6, -8.6), (72, -7)])
    T.trees([(-60, -30), (-45, 28), (-8, -30), (12, 30), (42, -28), (55, 26), (-55, 22), (18, -30), (45, 40),
             (15, 46), (48, 52), (-35, -28), (85, 20), (85, -20), (-12, 30), (-40, 34), (-22, 36), (2, 24)], style="B")

    # --- baby crib (front yard, south side)
    mb("crib", [(1.4, 0.9, 0.1, -10, -8.6, 0.55, "#e8e0cc")] +
       [(0.08, 0.08, 0.9, -10 + sx * 0.66, -8.6 + sy * 0.41, 0.45, "#e8e0cc") for sx in (-1, 1) for sy in (-1, 1)] +
       [(0.05, 0.05, 0.35, -10 + i * 0.16 - 0.64, -8.6 + sy * 0.41, 0.78, "#e8e0cc") for i in range(9) for sy in (-1, 1)] +
       [(1.4, 0.06, 0.06, -10, -8.6 + sy * 0.41, 0.96, "#e8e0cc") for sy in (-1, 1)] +
       [(1.3, 0.8, 0.08, -10, -8.6, 0.63, "#9ac0e0")])

    # --- bakery: fancy plate with a single crumb + price tag; "soup day" pot + sign
    mb("plate_pedestal", [(0.6, 0.6, 0.4, -20, 7.3, 1.17, "#e8e0cc"), (0.7, 0.7, 0.05, -20, 7.3, 1.38, "#c9b16a")])
    cyl("plate_dish", 0.27, 0.03, (-20, 7.3, 1.405), "#f6f2ea", seg=16)
    cyl("plate_rim", 0.29, 0.012, (-20, 7.3, 1.40), "#c9b16a", seg=16)
    mb("plate_crumb", [(0.035, 0.03, 0.025, -20, 7.3, 1.448, "#c08a4a", 0.4)])
    mb("price_tag", [(0.42, 0.04, 0.26, -19.25, 6.92, 1.18, "#f6f2ea", 0)])
    text("price_text", "$12", (-19.25, 6.895, 1.18), 0, 0.15, "#2c2418", extrude=0.01)
    cyl(G("bsoup", "pot"), 0.4, 0.5, (-20.9, 7.3, 0.97), "#3e3b38", seg=12)
    cyl(G("bsoup", "soup"), 0.36, 0.03, (-20.9, 7.3, 1.46), "#c8502a", seg=12)
    mb(G("bsoup", "board"), [(3.4, 0.12, 0.6, -20, 9.85, 3.0, "#a3302a")])
    text(G("bsoup", "text"), "NOW SELLING: SOUP", (-20, 9.77, 3.0), 0, 0.3, "#efe6d0")

    # --- birthday yard (behind the north houses)
    B.fence("by_f1", (-35, 24), (-25, 24))
    B.fence("by_f2", (-35, 24), (-35, 33))
    B.fence("by_f3", (-25, 24), (-25, 33))
    mb("by_table", [(2.2, 1.2, 0.1, -30, 28, 0.86, "#f2eee4")] +
       [(0.1, 0.1, 0.82, -30 + sx * 1.0, 28 + sy * 0.5, 0.41, "#6a4a30") for sx in (-1, 1) for sy in (-1, 1)])
    cyl(G("ycake", "cake"), 0.32, 0.26, (-30, 28, 0.91), "#f0c8d0", seg=14)
    cyl(G("ycake", "icing"), 0.33, 0.04, (-30, 28, 1.15), "#ffffff", seg=14)
    cyl(G("ycake", "candle"), 0.025, 0.18, (-30, 28, 1.19), "#5f86c8", seg=6)
    fl = cyl(G("ycake", "flame"), 0.03, 0.07, (-30, 28, 1.38), "#ffd060", seg=6, r2=0.005)
    T.emissive(fl, 8.0)
    cyl(G("blend", "glass"), 0.16, 0.42, (-30.3, 28, 0.91), "#f0b8c8", seg=12)
    cyl(G("blend", "top"), 0.17, 0.04, (-30.3, 28, 1.33), "#ffffff", seg=12)
    cyl(G("blend", "straw"), 0.02, 0.3, (-30.25, 28.05, 1.3), "#d84a4a", seg=5)
    cyl(G("blend", "candle"), 0.02, 0.14, (-30.36, 27.96, 1.33), "#5f86c8", seg=6)
    for i in range(6):   # little bunting over the yard
        mb(f"by_flag{i}", [(0.3, 0.03, 0.35, -34 + i * 1.6, 24.05, 1.75, ["#d84a4a", "#f0c040", "#4a8ad8"][i % 3])])
    B.wire("by_wire", (-35, 24.05, 2.0), (-25, 24.05, 2.0), sag=0.3)

    # --- parade dressing on Main Street (poles across the street + bunting + banner + float + drum)
    for i, x in enumerate((0, 15)):
        B.pole(G("parade", f"npole{i}"), x, 6.2)
    flags = []
    for (a, b) in (((0, -6.2), (0, 6.2)), ((15, -6.2), (15, 6.2)), ((0, -6.2), (15, 6.2)), ((0, 6.2), (15, -6.2)),
                   ((-15, -6.2), (0, 6.2)), ((15, 6.2), (30, -6.2))):
        name = G("parade", f"bunt_{a[0]}_{a[1]}_{b[0]}")
        B.wire(name, (a[0], a[1], 7.1), (b[0], b[1], 7.1), sag=1.2)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = int(L / 0.8)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for k in range(1, n):
            u = k / n
            x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
            z = 7.1 - 1.2 * 4 * u * (1 - u) - 0.2
            flags.append((0.34, 0.03, 0.36, x, y, z, ["#d84a4a", "#f0c040", "#4a8ad8", "#5ab05a", "#f6f2ea"][k % 5], ang))
    mb(G("parade", "flags"), flags)
    mb(G("parade", "banner"), [(13.6, 0.08, 1.3, 7.5, 6.2, 5.6, "#a3302a"), (13.8, 0.1, 0.1, 7.5, 6.2, 6.28, "#f0c040"),
                               (13.8, 0.1, 0.1, 7.5, 6.2, 4.92, "#f0c040")])
    text(G("parade", "banner_t1"), "BIG PARADE DAY", (7.5, 6.14, 5.6), 0, 0.7, "#f6f2ea")
    text(G("parade", "banner_t2"), "BIG PARADE DAY", (7.5, 6.26, 5.6), math.pi, 0.7, "#f6f2ea")
    fx, fy = 16.0, -0.4
    mb(G("parade", "float"), [(6.0, 2.8, 0.7, fx, fy, 0.75, "#4a8ad8"), (6.2, 3.0, 0.12, fx, fy, 1.12, "#f0c040"),
                              (5.8, 2.9, 0.5, fx, fy, 0.35, "#f6f2ea"),
                              (2.6, 1.4, 1.1, fx + 1.2, fy + 0.3, 1.7, "#c08a4a"), (2.4, 1.2, 0.35, fx + 1.2, fy + 0.3, 2.35, "#d8a868"),
                              (0.9, 0.9, 0.2, fx - 2.0, fy, 1.27, "#a3302a")] +
       [(0.9, 0.25, 0.9, fx + sx * 2.1, fy + sy * 1.45, 0.45, "#3e3b38") for sx in (-1, 1) for sy in (-1, 1)])
    mb(G("parade", "float_sign"), [(3.4, 0.1, 0.7, fx + 1.0, fy - 1.47, 1.05, "#f6f2ea")])
    text(G("parade", "float_txt"), "LOOK, DON'T EAT", (fx + 1.0, fy - 1.53, 1.05), 0, 0.3, "#a3302a")
    drum = empty(G("parade", "drum"), (11.0, -0.8, 1.15))
    cyl(G("parade", "drum_body"), 0.45, 0.5, (0, 0, -0.25), "#d84a4a", seg=14, parent=drum, rot=(math.radians(90), 0, 0))
    cyl(G("parade", "drum_rim1"), 0.47, 0.06, (0, -0.22, 0), "#f6f2ea", seg=14, parent=drum, rot=(math.radians(90), 0, 0))
    cyl(G("parade", "drum_rim2"), 0.47, 0.06, (0, 0.28, 0), "#f6f2ea", seg=14, parent=drum, rot=(math.radians(90), 0, 0))

    # --- soup stands on every corner (sunset, after the soup discovery)
    def stand(name, x, y, face, flavor, col):
        root = empty(G("stands", name), (x, y, 0), B.rz(face))
        bx = [(2.6, 1.0, 1.0, 0, 0, 0.5, "#8a6a4a"), (2.8, 1.1, 0.08, 0, 0, 1.04, "#9a7a58")]
        bx += [(0.1, 0.1, 2.4, sx * 1.3, sy * 0.5, 1.2, "#6a4a30") for sx in (-1, 1) for sy in (-1, 1)]
        bx += [(0.38, 1.4, 0.08, -1.33 + i * 0.38, 0.05, 2.45, "#d84a4a" if i % 2 == 0 else "#f6f2ea") for i in range(8)]
        mb(G("stands", name + "_body"), bx, parent=root)
        cyl(G("stands", name + "_pot"), 0.4, 0.5, (0, -0.1, 1.08), "#3e3b38", seg=12, parent=root)
        s = cyl(G("stands", name + "_soup"), 0.36, 0.03, (0, -0.1, 1.57), col, seg=12, parent=root)
        T.emissive(s, 0.5)
        cyl(G("stands", name + "_ladle"), 0.03, 0.9, (0.18, -0.1, 1.3), "#c8c8c0", seg=6, parent=root, rot=(0.0, 0.45, 0))
        for k, dx in enumerate((-0.9, 0.9)):
            cyl(G("stands", f"{name}_mug{k}"), 0.1, 0.16, (dx, 0.2, 1.08), "#f6f2ea", seg=8, parent=root)
        mb(G("stands", name + "_sign"), [(1.9, 0.08, 0.5, 0, 0.55, 0.62, "#4f3a2a")], parent=root)
        text(G("stands", name + "_txt"), flavor, (0, 0.6, 0.62), math.pi, 0.26, "#efe6d0", parent=root)

    stand("sa", 26, 6.0, -90, "PUMPKIN", "#e08a2a")
    stand("sb", 34, 6.0, -90, "CHICKEN", "#e8c860")
    stand("sc", 7.5, -5.8, 90, "POTATO", "#e8dcb0")
    stand("sd", -8, 6.0, -90, "TOMATO", "#c8402a")
    stand("se", -30, -5.8, 90, "PUMPKIN", "#e08a2a")
    stand("sf", 60, -6.6, 90, "SOUP", "#c8502a")

    # --- royal dog (blocky, with a crown and a red cape) + its cushion throne
    dog = empty("dog", (0, 0, -300))
    fur, dark = "#d8a050", "#8a5a2a"
    mb("dog_body", [(0.44, 0.95, 0.44, 0, 0, 0.6, fur), (0.13, 0.13, 0.42, -0.14, 0.32, 0.21, fur),
                    (0.13, 0.13, 0.42, 0.14, 0.32, 0.21, fur), (0.13, 0.13, 0.42, -0.14, -0.32, 0.21, fur),
                    (0.13, 0.13, 0.42, 0.14, -0.32, 0.21, fur), (0.46, 0.62, 0.05, 0, -0.05, 0.84, "#a3302a"),
                    (0.05, 0.6, 0.3, -0.24, -0.05, 0.7, "#a3302a"), (0.05, 0.6, 0.3, 0.24, -0.05, 0.7, "#a3302a")], parent=dog)
    head = empty("dog_head", (0, 0.56, 0.9), parent=dog)
    mb("dog_headbox", [(0.42, 0.4, 0.4, 0, 0, 0, fur), (0.26, 0.24, 0.2, 0, 0.3, -0.07, "#e8c890"),
                       (0.1, 0.06, 0.07, 0, 0.42, -0.01, "#1e1a18"), (0.07, 0.03, 0.08, -0.1, 0.205, 0.07, "#1e1a18"),
                       (0.07, 0.03, 0.08, 0.1, 0.205, 0.07, "#1e1a18"), (0.11, 0.1, 0.24, -0.2, -0.04, 0.12, dark),
                       (0.11, 0.1, 0.24, 0.2, -0.04, 0.12, dark), (0.12, 0.05, 0.03, 0, 0.36, -0.15, "#d86070")], parent=head)
    crown = [(0.34, 0.34, 0.09, 0, 0, 0.25, "#e0b030")]
    crown += [(0.07, 0.07, 0.11, sx * 0.135, sy * 0.135, 0.34, "#e0b030") for sx in (-1, 1) for sy in (-1, 1)]
    mb("dog_crown", crown, parent=head)
    jw = mb("dog_jewel", [(0.06, 0.03, 0.06, 0, 0.175, 0.25, "#d83040")], parent=head)
    T.emissive(jw, 2.0)
    empty("dog_headpt", (0, 0.12, 0.05), parent=head)
    tail = empty("dog_tail", (0, -0.47, 0.75), parent=dog)
    mb("dog_tailbox", [(0.09, 0.09, 0.4, 0, -0.05, 0.16, fur)], parent=tail)
    mb("dog_throne", [(1.4, 1.6, 0.5, 45.8, -6.0, 0.25, "#a3302a"), (1.5, 1.7, 0.06, 45.8, -6.0, 0.52, "#e0b030"),
                      (1.4, 0.3, 1.2, 45.8, -6.75, 0.85, "#a3302a")])
    cyl("dog_ham", 0.22, 0.4, (45.8, -5.5, 0.55), "#c86a5a", seg=10, rot=(math.radians(90), 0, 0.3))
    mb("dog_cushion_float", [(1.0, 1.0, 0.12, 14.0, -0.4, 1.12, "#a3302a")])

    # --- props that follow actors (positioned in apply)
    mb("maya_backpack", [(0.62, 0.28, 0.66, 0, 0, 0, "#6a4aa8"), (0.5, 0.06, 0.3, 0, -0.16, -0.12, "#8a6ac8"),
                         (0.08, 0.06, 0.62, -0.2, 0.16, 0.06, "#3a2a6a"), (0.08, 0.06, 0.62, 0.2, 0.16, 0.06, "#3a2a6a")],
       loc=(0, 0, -300))
    mb("stone_teeth", [(0.022, 0.012, 0.03, -0.036 + i * 0.024, 0, 0, "#9a9488") for i in range(4)], loc=(0, 0, -300))
    cyl("party_hat", 0.17, 0.42, (0, 0, -300), "#d84a4a", seg=10, r2=0.01)
    mb("maya_quilt", [(1.15, 1.25, 0.28, BX + 2.4, BY + 2.2, 1.02, "#c85a6a"), (0.4, 0.4, 0.29, BX + 2.15, BY + 2.0, 1.02, "#f0c040"),
                      (0.4, 0.4, 0.29, BX + 2.65, BY + 2.45, 1.02, "#4a8ad8")])

    # --- kitchen (Maya's home): feast, birthday cake, dinner pea
    T.kitchen(KX, KY, soup=False)
    k = KY + 2
    for i in range(5):
        cyl(G("feast", f"pancake{i}"), 0.25, 0.05, (KX - 0.75, k + 0.15, 0.97 + i * 0.05), "#d8a050", seg=12)
    cyl(G("feast", "syrup"), 0.2, 0.02, (KX - 0.75, k + 0.15, 1.22), "#8a4a1a", seg=12)
    cyl(G("feast", "pkplate"), 0.32, 0.02, (KX - 0.75, k + 0.15, 0.96), "#f6f2ea", seg=12)
    mb(G("feast", "melon"), [(0.62, 0.5, 0.42, KX + 0.75, k + 0.05, 1.17, "#3f7a3a"), (0.5, 0.52, 0.36, KX + 0.75, k + 0.05, 1.17, "#5a9a4a"),
                             (0.08, 0.53, 0.37, KX + 0.62, k + 0.05, 1.17, "#2f5a2a"), (0.08, 0.53, 0.37, KX + 0.88, k + 0.05, 1.17, "#2f5a2a")])
    cyl(G("feast", "pickles"), 0.13, 0.32, (KX + 1.2, k + 0.5, 0.96), "#b8d0b0", seg=10)
    cyl(G("feast", "pickle_lid"), 0.14, 0.05, (KX + 1.2, k + 0.5, 1.28), "#c9b16a", seg=10)
    mb(G("feast", "sandwich"), [(0.6, 0.5, 0.06, KX, k - 0.45, 0.99, "#d8a868"), (0.62, 0.52, 0.04, KX, k - 0.45, 1.04, "#5a9a4a"),
                                (0.58, 0.48, 0.05, KX, k - 0.45, 1.08, "#d86050"), (0.6, 0.5, 0.06, KX, k - 0.45, 1.13, "#d8a868"),
                                (0.4, 0.34, 0.05, KX, k - 0.45, 1.18, "#e8c860"), (0.42, 0.36, 0.05, KX, k - 0.45, 1.225, "#d8a868"),
                                (0.6, 0.5, 0.06, KX, k - 0.45, 1.28, "#d8a868")])
    cyl(G("kcake", "cake"), 0.3, 0.24, (KX, k, 0.96), "#f0c8d0", seg=14)
    cyl(G("kcake", "icing"), 0.31, 0.04, (KX, k, 1.18), "#ffffff", seg=14)
    cyl(G("kcake", "candle"), 0.025, 0.16, (KX, k, 1.22), "#e8507a", seg=6)
    f2 = cyl(G("kcake", "flame"), 0.03, 0.07, (KX, k, 1.39), "#ffd060", seg=6, r2=0.005)
    T.emissive(f2, 8.0)
    cyl(G("pea", "plate"), 0.26, 0.02, (KX, k - 0.4, 0.96), "#f6f2ea", seg=14)
    cyl(G("pea", "pea"), 0.018, 0.02, (KX + 0.02, k - 0.4, 0.98), "#5ab05a", seg=8)

    # --- Maya's bedroom (night): bed from the kit + thermos on the nightstand + a warm bedside lamp
    T.bedroom(BX, BY, wall="#8fa0c0")
    mb("bed_nightstand", [(0.6, 0.5, 0.7, BX + 1.0, BY + 3.3, 0.35, "#6a4a30")])
    cyl("bedthermos", 0.07, 0.3, (BX + 1.0, BY + 3.3, 0.7), "#a3302a", seg=10)
    cyl("bedthermos_cap", 0.075, 0.06, (BX + 1.0, BY + 3.3, 1.0), "#d8d8d0", seg=10)
    cyl("bedlamp_base", 0.08, 0.3, (BX + 0.8, BY + 3.45, 0.7), "#3e3b38", seg=8)
    sh_ = cyl("bedlamp_shade", 0.18, 0.2, (BX + 0.8, BY + 3.45, 1.0), "#f3dc9a", seg=10, r2=0.12)
    T.emissive(sh_, 3.0)
    T.point_light("bed_lamp", (BX + 1.2, BY + 1.2, 2.0), 70, (1.0, 0.78, 0.5))
    mb("bed_poster", [(1.2, 0.03, 0.8, BX - 1.8, BY + 3.97, 1.9, "#f0c040")])
    text("bed_poster_t", "SOUP", (BX - 1.8, BY + 3.94, 1.9), 0, 0.3, "#a3302a")

    # --- restaurant (one grape per table -> soup the next morning)
    T.room("rest", RX, RY, W=12, D=10, H=3.4, floor="#8a6a4a", wall="#c2a88a")
    for i, tx in enumerate((RX - 3, RX + 3)):
        mb(f"rest_table{i}", [(1.7, 1.7, 0.08, tx, RY, 0.88, "#f2eee4"), (1.75, 1.75, 0.3, tx, RY, 0.73, "#f2eee4"),
                              (0.15, 0.15, 0.85, tx, RY, 0.42, "#5e4028")])
        for cx_, cy_ in ((-0.75, 0.9), (0.75, 0.9), (1.0, -0.2), (-1.0, -0.2)):
            mb(f"rest_chair{i}_{cx_}_{cy_}", [(0.55, 0.55, 0.08, tx + cx_, RY + cy_, 0.5, "#6a4a30")] +
               [(0.06, 0.06, 0.5, tx + cx_ + sx * 0.22, RY + cy_ + sy * 0.22, 0.25, "#5e4028") for sx in (-1, 1) for sy in (-1, 1)])
        cyl(f"rest_plate{i}", 0.3, 0.02, (tx, RY, 0.93), "#f6f2ea", seg=16)
        cyl(f"rest_rim{i}", 0.31, 0.012, (tx, RY, 0.925), "#c9b16a", seg=16)
        mb(G("grape", f"g{i}"), [(0.05, 0.05, 0.055, tx, RY, 0.97, "#6a3a8a", 0.3)])
        cyl(G("rsoup", f"bowl{i}"), 0.22, 0.12, (tx, RY, 0.94), "#e2d8c0", seg=12, r2=0.26)
        cyl(G("rsoup", f"soup{i}"), 0.24, 0.02, (tx, RY, 1.05), "#c8502a", seg=12)
        for sx in (-0.45, 0.45):
            cyl(f"rest_candle{i}_{sx}", 0.03, 0.22, (tx + sx, RY + 0.4, 0.93), "#f6f2ea", seg=6)
            c = cyl(f"rest_flame{i}_{sx}", 0.025, 0.06, (tx + sx, RY + 0.4, 1.16), "#ffd060", seg=6, r2=0.004)
            T.emissive(c, 6.0)
    mb("rest_signboard", [(4.6, 0.08, 0.9, RX, RY + 4.95, 2.6, "#4f3a2a")])
    text("rest_signtext", "CHEZ GRAPE", (RX, RY + 4.88, 2.6), 0, 0.5, "#e0b030")
    mb("rest_menu", [(1.2, 0.06, 1.5, RX + 4.5, RY + 4.95, 1.7, "#2a2a2c")])
    text("rest_menu_t", "MENU\n1 GRAPE", (RX + 4.5, RY + 4.9, 1.75), 0, 0.2, "#f6f2ea")
    T.point_light("rest_lamp", (RX - 3, RY + 0.5, 2.8), 60, (1.0, 0.82, 0.6))
    T.point_light("rest_lamp2", (RX + 3, RY + 0.5, 2.8), 60, (1.0, 0.82, 0.6))

    # --- school cafeteria: long table, bench, trays, the lunch bell
    T.room("caf", CX, CY, W=12, D=10, H=3.4, floor="#7c7a74", wall="#cdbb98")
    mb("caf_table", [(8.0, 1.4, 0.08, CX, CY, 0.8, "#9a7a58")] +
       [(0.12, 1.2, 0.76, CX + sx, CY, 0.38, "#5e4028") for sx in (-3.6, 0, 3.6)])
    mb("caf_bench", [(8.0, 0.45, 0.08, CX, CY + 1.0, 0.48, "#7a5c40")] +
       [(0.12, 0.4, 0.46, CX + sx, CY + 1.0, 0.23, "#5e4028") for sx in (-3.6, 0, 3.6)])
    for i, tx in enumerate((CX - 2.4, CX, CX + 2.4)):
        mb(f"caf_tray{i}", [(0.75, 0.5, 0.03, tx, CY + 0.35, 0.855, "#b8bcc0"), (0.25, 0.2, 0.031, tx - 0.18, CY + 0.35, 0.87, "#8a8e92")])
    mb("caf_lentil", [(0.025, 0.025, 0.014, CX - 0.18, CY + 0.35, 0.89, "#8a6a3a")])
    mb("caf_food", [(0.12, 0.1, 0.03, CX - 2.55, CY + 0.35, 0.89, "#c8a060"), (0.1, 0.1, 0.03, CX + 2.25, CY + 0.35, 0.89, "#6a9a4a")])
    cyl("caf_bell", 0.22, 0.25, (CX - 3, CY + 4.82, 2.25), "#c9b16a", seg=12, r2=0.1, rot=(math.radians(90), 0, 0))
    mb("caf_bellmount", [(0.5, 0.08, 0.5, CX - 3, CY + 4.95, 2.37, "#4f3a2a")])
    mb("caf_board", [(4.0, 0.06, 1.2, CX + 1.5, CY + 4.95, 2.0, "#2f4a3a")])
    text("caf_board_t", "LUNCH: 1 BITE", (CX + 1.5, CY + 4.9, 2.0), 0, 0.34, "#f6f2ea")
    mb("caf_counter", [(3.2, 0.9, 1.0, CX + 4.2, CY + 4.3, 0.5, "#b8bcc0")])
    T.point_light("caf_lamp", (CX, CY + 1, 3.0), 160, (1.0, 0.92, 0.8))



# ------------------------------------------------------------------ per-frame hooks
def _groups(stage):
    g = getattr(stage, "_tb_groups", None)
    if g is None:
        g = {}
        for ob in stage.ob:
            if ob.name.startswith("grp_"):
                g.setdefault(ob.name.split("_")[1], []).append(ob)
        stage._tb_groups = g
    return g


def _hide_tree(ob, hide):
    ob.hide_render = hide
    for c in ob.children_recursive:
        c.hide_render = hide


def apply(stage, sh, t, gt):
    from mathutils import Vector, Matrix
    actors = stage.actors_for(sh)
    acts = sh.get("acts", {})
    show = shown_groups(sh)
    for gname, obs in _groups(stage).items():
        for ob in obs:
            ob.hide_render = gname not in show
    S = stage.CAST
    for n, spec in actors.items():
        act = acts.get(n, spec[3]).partition(":")[0]
        s = S[n]["scale"]
        root = stage.ob[n + "_root"]
        if act == "lie":        # kit's lie lands face-down: roll face-up so face + counter read from above
            root.rotation_euler.x = 1.5
            root.location.z = spec[4] + 0.36 * s
        if n in SITTERS.get(sh["set"], ()) and act not in ("sit", "walk", "run"):
            root.location.z = spec[4] + 0.56 - 0.9 * s
            stage.ob[n + "_legL"].rotation_euler.x = stage.ob[n + "_legR"].rotation_euler.x = 1.57
        if n in KNEELERS.get(sh["set"], ()) and act not in ("walk", "run"):
            root.location.z = spec[4] - KNEEL * s
            if act in ("give", "hold"):
                stage.ob[n + "_armR"].rotation_euler.x = 1.05
    # flashback: the counter "that never moved" shows the bedroom-era 300
    if sh.get("flash") and "maya" in actors:
        stage.set_counter("maya", 300, gt)
    # backpack on Maya when she's out of the house
    bp = stage.ob["maya_backpack"]
    if "maya" in actors and sh["set"] not in HOME_SETS:
        bp.matrix_world = stage.ob["maya_torso"].matrix_world @ Matrix.Translation((0, -0.37, 1.32))
    else:
        bp.matrix_world = Matrix.Translation((0, 0, -300))
    # stone teeth
    teeth = stage.ob["stone_teeth"]
    who = [n for n in sh.get("teeth", []) if n in actors]
    if who:
        n = who[0]
        fc = sh.get("faces", {}).get(n, "neutral")
        z, w = (0.19, 1.7) if fc == "laughing" else (0.222, 1.0)
        teeth.matrix_world = stage.ob[n + "_head"].matrix_world @ Matrix.Translation((0, 0.318, z)) @ \
            Matrix.Diagonal((w, 1, 1, 1))
    else:
        teeth.matrix_world = Matrix.Translation((0, 0, -300))
    # party hat on the birthday kid
    hat = stage.ob["party_hat"]
    if sh["set"] == "yard" and "t7" in actors:
        hat.matrix_world = stage.ob["t7_head"].matrix_world @ Matrix.Translation((0.05, 0, 0.66))
    else:
        hat.matrix_world = Matrix.Translation((0, 0, -300))
    # drum follows the drummer
    if "drum" in show or "parade" in show:
        d = stage.ob.get("grp_parade_drum")
        if d is not None and "t3" in actors and sh["set"] == "parade":
            r = stage.ob["t3_root"]
            f = r.matrix_world.to_3x3() @ Vector((0, 1, 0))
            d.location = r.location + f.normalized() * 0.55 + Vector((0, 0, 1.15))
            d.rotation_euler.z = r.rotation_euler.z
        elif d is not None:
            d.location = (0, 0, -300)
    # the royal dog
    dog = stage.ob["dog"]
    if sh["set"] in DOG:
        x, y, face, z = DOG[sh["set"]]
        dog.location = (x, y, z)
        dog.rotation_euler.z = math.radians(face - 90)
        stage.ob["dog_tail"].rotation_euler.y = 0.6 * math.sin(14 * t)
        stage.ob["dog_head"].rotation_euler.x = 0.12 * math.sin(3 * t) if sh["set"] != "dog_royal" else -0.25 + 0.15 * abs(math.sin(5 * t))
    else:
        dog.location = (0, 0, -300)
    stage.ob["dog_cushion_float"].hide_render = "parade" not in show
    # soup ladles stir
    for nm in ("grp_stands_sa_ladle", "grp_stands_sd_ladle"):
        if nm in stage.ob:
            stage.ob[nm].rotation_euler.z = 0.9 * t


def cam_override(stage, sh, t, actors, T, f, u):
    """Rue lying on Main Street: look down at her face / counter from above (face-up, head away from her feet)."""
    from mathutils import Vector
    from render import lerp, fdir
    cam, tgt = sh["cam"], sh["tgt"]
    lying = "rue" in actors and sh.get("acts", {}).get("rue", actors["rue"][3]).startswith("lie")
    if lying and tgt in ("rue", "rue_chest") and cam in ("ecu", "cu", "mcu", "counter", "dutch", "push", "high", "orbit"):
        H = stage.head_pos("rue")
        C = stage.ob["rue_torso"].matrix_world @ Vector((0, 0.3, 1.43))
        feet = fdir(stage.facing("rue"))           # from head toward her feet
        side = Vector((-feet.y, feet.x, 0))
        if cam == "counter" or tgt == "rue_chest":
            look = C
            pos = C + feet * 0.45 + side * 0.15 + Vector((0, 0, lerp(1.55, 1.25, u)))
            return pos, look, 40
        if cam == "mcu":
            look = (H + C) / 2
            pos = look + feet * 0.9 + side * 0.25 + Vector((0, 0, lerp(2.0, 1.7, u)))
            return pos, look, 40
        if cam == "high":
            look = (H + C) / 2
            pos = look + feet * 2.2 + side * lerp(-1.0, 1.0, u) + Vector((0, 0, 4.0))
            return pos, look, 30
        if cam == "orbit":
            look = (H + C) / 2
            a = lerp(-40, 40, u)
            from render import rot2
            pos = look + rot2(feet, a) * 1.8 + Vector((0, 0, 2.4))
            return pos, look, 35
        d = {"ecu": lerp(1.7, 1.4, u), "cu": lerp(2.3, 1.9, u), "dutch": 1.8, "push": lerp(3.6, 2.0, u)}[cam]
        pos = H + feet * d * 0.45 + side * d * 0.12 + Vector((0, 0, d))
        r = (pos, H, 40)
        if cam == "dutch":
            r = (pos, H, 40, 12)
        return r
    # Maya kneeling beside Rue: keep cameras off the line through Rue's head (swing 35 deg to Maya's left, a bit higher)
    if sh["set"] in KNEELERS and tgt == "maya" and "maya" in KNEELERS[sh["set"]] and \
            cam in ("counter", "mcu", "ecu", "cu", "dutch", "push", "hands"):
        from render import rot2
        fm = fdir(stage.facing("maya"))
        H = stage.head_pos("maya")
        C = stage.ob["maya_torso"].matrix_world @ Vector((0, 0.3, 1.43))
        k = stage.CAST["maya"]["scale"]
        if cam == "counter":
            return C + rot2(fm, 35) * lerp(1.75, 1.45, u) + Vector((0, 0, 0.32)), C, 40
        if cam == "mcu":
            look = H - Vector((0, 0, 0.42 * k))
            return look + rot2(fm, 32) * lerp(2.5, 2.1, u) + Vector((0, 0, 0.3)), look, 40
        if cam == "hands":
            Hd = (stage.hand_pos("maya") + stage.ob["maya_armL"].matrix_world @ Vector((0, 0, -0.75))) / 2
            return Hd + rot2(fm, 55) * lerp(1.6, 1.3, u) + Vector((0, 0, 0.55)), Hd + Vector((0, 0, 0.05)), 35
        if cam == "push":
            return H + rot2(fm, 32) * lerp(4.2, 2.2, u) + Vector((0, 0, 0.45)), H - Vector((0, 0, 0.2)), 35
        d = {"ecu": lerp(1.55, 1.25, u), "cu": lerp(2.0, 1.6, u), "dutch": lerp(1.8, 1.5, u)}[cam]
        r = (H + rot2(fm, 30) * d + Vector((0, 0, 0.12)), H + Vector((0, 0, 0.04)), 40)
        return r + ((12,) if cam == "dutch" else ())
    # parade bunting hangs at 5.5-7.1 m over Main Street: keep high cameras under it
    if cam == "high" and "parade" in shown_groups(sh) and -17 < T.x < 32 and abs(T.y) < 7:
        from render import rot2
        k = stage.CAST[tgt]["scale"] if tgt in actors else 1.0
        pos = T + rot2(f, 15 + 12 * u) * 3.4 * k
        pos.z = min(T.z + 3.4, 4.8)
        return pos, T - Vector((0, 0, 0.5)), 26
    return None
