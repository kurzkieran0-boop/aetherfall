"""The Mailman Skips Our House - set dressing, cast, blocking (Style A). Ported from ./mailman onto the kit."""
import math, random, os

CAST = {
    "eli":    dict(shirt="#6f8aa3", pants="#6b5440", hair="#5a3c26", skin="#e2be96", scale=0.78, kind="kid", held=["env"], label="ELI"),
    "eli2":   dict(shirt="#6f8aa3", pants="#6b5440", hair="#5a3c26", skin="#e2be96", scale=0.78, kind="kid", held=["env"], label="MR. DOBBS"),
    "dobbs":  dict(shirt="#4f6a8a", pants="#3e4652", hair="#5a4a3a", skin="#d8a882", scale=1.06, kind="mail", held=["env"], label="ELI"),
    "mom":    dict(shirt="#a3735a", pants="#5c4a40", hair="#6a4428", skin="#e6c4a0", scale=0.98, kind="mom"),
    "dad":    dict(shirt="#7b8048", pants="#5b4634", hair="#3a2a1e", skin="#c49670", scale=1.02, kind="dad"),
    "baker":  dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker", held=["env"], label="BAKER"),
    "pell":   dict(shirt="#8b6f85", pants="#5c4a58", hair="#b9b5ae", skin="#eccdb2", scale=0.96, kind="pell", held=["env"], label="PELL"),
    "mayor":  dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor", held=["env"], label="MAYOR"),
    "harlan": dict(shirt="#8a6a48", pants="#4a5a6a", hair="#d8d4cc", skin="#d4a884", scale=0.98, kind="farmer", held=["env"], label="HARLAN"),
    "t1":     dict(shirt="#a3593d", pants="#4f4436", hair="#2b211a", skin="#aa7a58", scale=0.98, kind="plain"),
    "t2":     dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="plain"),
    "t3":     dict(shirt="#b8964a", pants="#5d5040", hair="#4a3426", skin="#96684a", scale=0.97, kind="plain"),
    "t4":     dict(shirt="#869468", pants="#4d4234", hair="#c09060", skin="#cca078", scale=1.0, kind="plain"),
    "t5":     dict(shirt="#7d4448", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain"),
}
HATS = {"dobbs", "mayor", "baker", "harlan"}

INT_KITCHEN = (0.0, 600.0)
DOBBS_HOUSE = (40.0, 30.0)
ELI_HOUSE = (-55.0, -14.0)

SETS = {
    "town":      {"dobbs": (-30, -6.4, 180, "walk", 0), "t1": (5, 1.4, 0, "walk", 0), "t2": (-10, 6.4, 0, "idle", 0),
                  "t4": (25, -1.2, 180, "walk", 0)},
    "street":    {"dobbs": (-49, -6.4, 180, "walk", 0), "eli": (-55, -10.0, 90, "idle", 0)},
    "gate":      {"dobbs": (-55, -6.6, 180, "idle", 0), "eli": (-54.2, -11.0, 90, "idle", 0)},
    "cross":     {"dobbs": (-47, 5.0, 180, "walk", 0), "eli": (-55, -9.6, 90, "idle", 0)},
    "runpast":   {"dobbs": (-44, -6.2, 180, "run", 0), "eli": (-55, -9.6, 90, "idle", 0)},
    "capdown":   {"dobbs": (-50, -6.4, 180, "walk_down", 0), "eli": (-55, -9.6, 70, "idle", 0)},
    "bakery":    {"baker": (-20, 9.2, -90, "read", 0), "dobbs": (-17.6, 7.2, 160, "idle", 0), "t4": (-12, 2, 180, "walk", 0)},
    "pell":      {"pell": (10, 8.6, -90, "read", 0), "t2": (16, 1.6, 180, "walk", 0)},
    "mayor_st":  {"mayor": (60, -1.0, 180, "read", 0), "t1": (66, 3, 200, "idle", 0), "t3": (55, -4, 20, "idle", 0)},
    "mailbox":   {"eli": (-52.6, -10.2, 90, "idle", 0)},
    "kitchen":   {"mom": (-1.25, 602.0, 0, "sit", 0), "dad": (1.25, 602.0, 180, "sit", 0), "eli": (0, 603.4, -90, "sit", 0)},
    "corner":    {"eli": (-27, -5.0, 0, "idle", 0), "dobbs": (-9, -5.4, 180, "walk", 0)},
    "corner_run": {"dobbs": (-9, -5.4, 0, "run", 0), "eli": (-27, -5.0, 0, "idle", 0)},
    "follow_bakery": {"dobbs": (-17.4, 6.0, 120, "walk", 0), "eli": (-6, 4.6, 180, "idle", 0)},
    "follow_mill": {"dobbs": (-34.2, 21.4, 200, "idle", 0), "eli": (-29, 14.6, 150, "idle", 0)},
    "follow_hall": {"dobbs": (73, -0.6, 0, "walk", 0), "eli": (62, 3.4, -20, "idle", 0)},
    "road_end":  {"dobbs": (-68, 1.0, 180, "hold", 0), "eli": (-62.2, 3.9, 200, "idle", 0)},
    "night_st":  {"eli": (30, 8.0, 90, "sneak", 0)},
    "dobbs_ext": {"eli": (45.6, 26.5, 120, "sneak", 0)},
    "window":    {"eli": (43.75, 30.0, 180, "peek", 0)},
    "int":       {"eli": (41.6, 30.7, 175, "idle", 0)},
    "int_door":  {"eli": (41.6, 30.7, -125, "idle", 0), "dobbs": (40.0, 27.7, 90, "idle", 0)},
    "int_talk":  {"eli": (41.4, 30.4, -125, "idle", 0), "dobbs": (40.4, 28.8, 55, "idle", 0)},
    "int_final": {"eli": (41.4, 30.4, 60, "read", 0), "eli2": (40.0, 27.35, 90, "hold", 0)},
    "barn":      {"harlan": (-95, 6.2, 90, "read", 0)},
    "barn_fire": {"harlan": (-95, 4.0, 90, "idle", 0)},
}
PROPS = {
    "mailbox": (-52.6, -8.45, 1.15, 90),
    "mailbox_in": (-52.6, -8.45, 1.12, 75),
    "eli_gate": (-55, -8.9, 0.8, 90),
    "eli_house": (-55, -10.5, 2.2, 75),
    "bakery_sign": (-20, 9.9, 4.3, -90),
    "post_office": (40, 10.4, 3.2, -90),
    "mill": (-36, 26, 7.0, -70),
    "hall_sign": (74.7, 0, 6.2, 180),
    "podium": (66.0, 0, 1.6, 180),
    "dobbs_house": (40, 26.6, 2.2, -12),
    "dobbs_window": (43.05, 30.0, 1.55, 0),
    "env_wall": (37.1, 30.6, 1.7, 0),
    "env_wall_back": (39.0, 32.9, 2.0, -90),
    "shelf": (37.35, 29.0, 1.45, 0),
    "hook": (40.0, 32.85, 1.75, -90),
    "door_int": (40.0, 27.05, 1.3, 112),
    "barn": (-100, 14, 3.5, -80),
    "field": (-92, 0, 0.5, 0),
}

NEEDS_ENVWALL = True
INTERIOR_SETS = {"kitchen", "int", "int_door", "int_talk", "int_final"}
NIGHT_SETS = {"night_st", "dobbs_ext", "window", "int", "int_door", "int_talk", "int_final"}
ROOMS = {s: (37.25, 42.75, 27.25, 32.75, 3.05) for s in ("int", "int_door", "int_talk", "int_final")}
SET_MOOD = {"kitchen": "interior"}
LIGHTS = {"kitchen_lamp": {"kitchen"}, "dobbs_lamp": NIGHT_SETS}
FAR_PROPS = {"eli_house", "post_office", "dobbs_house", "mill", "bakery_sign", "hall_sign", "barn"}
STRAIGHT_PROPS = {"eli_house"}
DEFAULT_FACE = {"eli2": "blank"}
CREAM, SEAL = "#efe5c8", "#a3302a"
rnd = random.Random(11)
_K = {}


def _bind(kit):
    g = globals()
    for n in ("mat", "multibox", "poly", "cyl", "empty", "text", "link", "house", "fence", "srgb"):
        g[n] = getattr(kit.blocks, n)
    g["wall_planes"] = kit.town.wall_planes
    g["img_mat"] = kit.town.img_mat
    g["TEX"] = str(kit.build_dir)
    g["bpy"] = __import__("bpy")


def dobbs_house():
    cx, cy = DOBBS_HOUSE
    W, D, H = 6.0, 6.0, 3.2
    x0, x1, y0, y1 = cx - W / 2, cx + W / 2, cy - D / 2, cy + D / 2
    door = (cx - 0.6, cx + 0.6, 0.0, 2.35)
    win = (cy - 0.65, cy + 0.65, 1.0, 2.05)
    ext = mat("#5f86a8", cull=True)
    env = img_mat("envwall", os.path.join(TEX, "envwall.png"))
    t = 0.12
    # exterior shell (outward normals) and interior skin (inward normals, envelope wallpaper)
    wall_planes("dh_ext_front", "y", y0 - t, x0 - t, x1 + t, H, door, -1, ext)
    wall_planes("dh_ext_back", "y", y1 + t, x0 - t, x1 + t, H, None, 1, ext)
    wall_planes("dh_ext_w", "x", x0 - t, y0 - t, y1 + t, H, None, -1, ext)
    wall_planes("dh_ext_e", "x", x1 + t, y0 - t, y1 + t, H, win, 1, ext)
    wall_planes("dh_in_front", "y", y0, x0, x1, H, door, 1, env, uv_scale=1.3)
    wall_planes("dh_in_back", "y", y1, x0, x1, H, None, -1, env, uv_scale=1.3)
    wall_planes("dh_in_w", "x", x0, y0, y1, H, None, 1, env, uv_scale=1.3)
    wall_planes("dh_in_e", "x", x1, y0, y1, H, win, -1, env, uv_scale=1.3)
    # hole reveals, sill, floor, ceiling, trims
    multibox("dh_frames", [
        (0.12, 0.26, 2.4, door[0] - 0.06, y0 - t / 2, 1.2, "#e8e0cc"), (0.12, 0.26, 2.4, door[1] + 0.06, y0 - t / 2, 1.2, "#e8e0cc"),
        (1.36, 0.26, 0.12, cx, y0 - t / 2, 2.41, "#e8e0cc"),
        (0.4, 1.5, 0.1, x1 + 0.05, cy, 0.95, "#e8e0cc"), (0.26, 1.5, 0.1, x1 + t / 2, cy, 2.1, "#e8e0cc"),
        (0.26, 0.1, 1.15, x1 + t / 2, win[0] - 0.05, 1.52, "#e8e0cc"), (0.26, 0.1, 1.15, x1 + t / 2, win[1] + 0.05, 1.52, "#e8e0cc"),
        (W + 0.5, D + 0.5, 0.2, cx, cy, 0.0, "#6d6252"),
        (W, D, 0.06, cx, cy, 0.11, "#7a5a3e"),
        (W + 0.3, 0.1, 0.25, cx, y0 - 0.2, 0.12, "#4a5a6a")])
    poly("dh_ceiling", [(x0, y0, H), (x1, y0, H), (x1, y1, H), (x0, y1, H)], [(3, 2, 1, 0)], mat("#5a4632", cull=True))
    rh = 1.9
    o = 0.45
    vs = [(x0 - o, y0 - o, H), (x1 + o, y0 - o, H), (x1 + o, y1 + o, H), (x0 - o, y1 + o, H), (cx, y0 - o, H + rh), (cx, y1 + o, H + rh)]
    poly("dh_roof", vs, [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], mat("#4f4a52", cull=True))
    poly("dh_gable", [(x0 - t, y0 - t, H), (x1 + t, y0 - t, H), (cx, y0 - t, H + rh - 0.1),
                      (x0 - t, y1 + t, H), (x1 + t, y1 + t, H), (cx, y1 + t, H + rh - 0.1)],
         [(0, 1, 2), (3, 5, 4)], mat("#5f86a8"))
    # door (hinged, swings inward)
    hinge = empty("dh_door_hinge", (door[0], y0 - 0.02, 0.0))
    multibox("dh_door", [(1.2, 0.08, 2.33, 0.6, 0, 1.17, "#3f5f7e"), (0.1, 0.12, 0.1, 1.05, -0.08, 1.15, "#c8a85a"),
                         (0.9, 0.1, 0.6, 0.6, 0, 1.75, "#355070")], parent=hinge)
    # envelopes sticking out of the walls (3D depth on top of the wallpaper)
    env3 = []
    for i in range(260):
        side = rnd.choice(["w", "w", "back", "back", "front", "e"])
        z = rnd.uniform(0.35, 3.0)
        rz_ = rnd.uniform(-0.3, 0.3)
        if side == "w":
            p = (x0 + 0.03, rnd.uniform(y0 + 0.3, y1 - 0.3)); dims = (0.03, 0.3, 0.2)
        elif side == "e":
            yy = rnd.uniform(y0 + 0.3, y1 - 0.3)
            if win[0] - 0.3 < yy < win[1] + 0.3 and z > 0.7: continue
            p = (x1 - 0.03, yy); dims = (0.03, 0.3, 0.2)
        elif side == "back":
            xx = rnd.uniform(x0 + 0.3, x1 - 0.3)
            if abs(xx - cx) < 0.5 and 1.4 < z < 2.2: continue
            p = (xx, y1 - 0.03); dims = (0.3, 0.03, 0.2)
        else:
            xx = rnd.uniform(x0 + 0.3, x1 - 0.3)
            if door[0] - 0.3 < xx < door[1] + 0.3: continue
            p = (xx, y0 + 0.03); dims = (0.3, 0.03, 0.2)
        if side == "w" and 28.2 < p[1] < 29.8 and 1.0 < z < 2.0:   # keep the name shelf clear
            continue
        env3.append((dims[0], dims[1], dims[2], p[0], p[1], z, CREAM, rz_ if side in ("back", "front") else 0))
        sd = 0.045
        if side in ("w", "e"):
            env3.append((0.05, sd, sd, p[0] + (0.02 if side == "w" else -0.02), p[1], z, SEAL))
        else:
            env3.append((sd, 0.05, sd, p[0], p[1] + (0.02 if side == "front" else -0.02), z, SEAL))
    multibox("dh_envelopes", env3)
    # the shelf of kids' names (west wall)
    sh = [(0.36, 1.9, 0.05, x0 + 0.18, cy - 1.0, z, "#6a4a30") for z in (1.15, 1.62)]
    names = ["CLARA", "THEO", "MAYA", "JONAH", "LUCY", "SAM", "IVY", "BEN"]
    for i, nm in enumerate(names):
        zz = 1.18 if i < 4 else 1.65
        yy = cy - 1.75 + (i % 4) * 0.5
        sh.append((0.05, 0.36, 0.26, x0 + 0.25, yy, zz + 0.13, CREAM, 0))
        sh.append((0.06, 0.06, 0.06, x0 + 0.28, yy, zz + 0.2, SEAL))
        text(f"dh_name_{nm}", nm, (x0 + 0.285, yy, zz + 0.07), math.radians(90), 0.075, "#2c2418", extrude=0.005)
    multibox("dh_shelf", sh)
    text("dh_shelf_label", "KIDS", (x0 + 0.21, cy - 1.0, 1.98), math.radians(90), 0.14, "#e8e0cc", extrude=0.005)
    # the ELI letter alone on its hook (back wall)
    cyl("dh_hook", 0.025, 0.12, (cx, y1 - 0.12, 2.0), "#8f8f8f", seg=6, rot=(math.radians(90), 0, 0))
    multibox("dh_eli_env", [(0.4, 0.03, 0.27, cx, y1 - 0.09, 1.78, CREAM), (0.07, 0.04, 0.07, cx, y1 - 0.11, 1.72, SEAL)])
    text("dh_eli_text", "ELI", (cx, y1 - 0.115, 1.83), 0, 0.09, "#2c2418", extrude=0.005)
    # furniture: table, lamp, stacks, chair, mailbag
    multibox("dh_furniture", [(1.4, 0.9, 0.08, cx - 0.6, cy + 1.2, 0.8, "#6a4a30")] +
             [(0.08, 0.08, 0.76, cx - 0.6 + dx, cy + 1.2 + dy, 0.4, "#5a3e28") for dx in (-0.6, 0.6) for dy in (-0.38, 0.38)] +
             [(0.34, 0.24, 0.05 + 0.03 * i, cx - 0.9 + 0.1 * i, cy + 1.15, 0.86 + 0.02 * i, CREAM, 0.2 * i) for i in range(4)] +
             [(0.6, 0.6, 0.08, cx + 0.4, cy + 1.1, 0.48, "#6a4a30"), (0.6, 0.08, 0.7, cx + 0.4, cy + 1.42, 0.85, "#6a4a30"),
              (0.7, 0.4, 0.6, cx + 2.2, cy - 2.2, 0.42, "#6a4e36"), (0.08, 0.5, 0.6, cx + 2.2, cy - 2.2, 0.9, "#4a3a28")])
    cyl("dh_lamp", 0.16, 0.35, (cx - 1.0, cy + 1.3, 0.84), "#d9c27a", seg=8, r2=0.08)
    lt = bpy.data.lights.new("dobbs_lamp", "POINT")
    lt.energy = 160
    lt.color = (1.0, 0.78, 0.5)
    lt.shadow_soft_size = 0.05
    lo = bpy.data.objects.new("dobbs_lamp", lt)
    lo.location = (cx - 0.4, cy + 0.4, 2.6)
    link(lo)


def eli_house():
    x, y = ELI_HOUSE
    house("eli_house", x, y, 90, w=7, d=7, h=3.6, wall="#8b9aa6", roof="#5e4c3e")
    fence("eli_fence_l", (x - 6, -8.8), (x - 0.85, -8.8))
    fence("eli_fence_r", (x + 0.85, -8.8), (x + 6, -8.8))
    gh = empty("eli_gate_hinge", (x - 0.8, -8.8, 0))
    multibox("eli_gate", [(0.12, 0.1, 1.1, 0.08 + i * 0.3, 0, 0.6, "#8a7052") for i in range(6)] +
             [(1.6, 0.08, 0.12, 0.8, 0, 0.45, "#7d6448"), (1.6, 0.08, 0.12, 0.8, 0, 0.95, "#7d6448")], parent=gh)
    mx, my = -52.6, -8.45
    multibox("mailbox", [(0.1, 0.1, 1.0, mx, my - 0.1, 0.5, "#5e4a38"), (0.36, 0.5, 0.06, mx, my - 0.1, 0.97, "#5e4a38"),
                         (0.34, 0.52, 0.04, mx, my - 0.1, 1.0, "#5d6a70"), (0.04, 0.52, 0.3, mx - 0.17, my - 0.1, 1.15, "#5d6a70"),
                         (0.04, 0.52, 0.3, mx + 0.17, my - 0.1, 1.15, "#5d6a70"), (0.36, 0.52, 0.06, mx, my - 0.1, 1.31, "#5d6a70"),
                         (0.34, 0.04, 0.3, mx, my - 0.36, 1.15, "#4d585e"),
                         (0.03, 0.2, 0.05, mx + 0.2, my - 0.05, 1.32, "#a3302a"), (0.03, 0.05, 0.25, mx + 0.2, my + 0.03, 1.2, "#a3302a")])
    # open front lid (hinged at the bottom, folded down toward the street)
    multibox("mailbox_lid", [(0.32, 0.03, 0.28, mx, my + 0.3, 0.92, "#5d6a70")])
    # the very confused spider and its web
    sp = [(0.07, 0.07, 0.05, mx, my, 1.05, "#141210"), (0.05, 0.05, 0.05, mx, my + 0.05, 1.06, "#141210")]
    for i in range(4):
        for s in (-1, 1):
            sp.append((0.09, 0.012, 0.012, mx + s * 0.06, my - 0.02 + i * 0.025, 1.04, "#141210", s * (0.4 - i * 0.25)))
    sp += [(0.003, 0.003, 0.25, mx - 0.1 + 0.07 * i, my + 0.15, 1.15, "#d8d8d0") for i in range(4)]
    multibox("spider", sp)


def _windmill_unused(cx, cy):
    hb, ht, H = 2.6, 1.5, 9.0
    vs = [(cx - hb, cy - hb, 0), (cx + hb, cy - hb, 0), (cx + hb, cy + hb, 0), (cx - hb, cy + hb, 0),
          (cx - ht, cy - ht, H), (cx + ht, cy - ht, H), (cx + ht, cy + ht, H), (cx - ht, cy + ht, H)]
    poly("mill_tower", vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], "#b9a07c")
    poly("mill_cap", [(cx - 1.9, cy - 1.9, H), (cx + 1.9, cy - 1.9, H), (cx + 1.9, cy + 1.9, H), (cx - 1.9, cy + 1.9, H),
                      (cx, cy - 1.9, H + 2.0), (cx, cy + 1.9, H + 2.0)],
         [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], "#6a5040")
    multibox("mill_door", [(1.3, 0.2, 2.2, cx, cy - hb - 0.02, 1.1, "#5b4030"), (1.0, 0.2, 0.8, cx, cy - 2.1, 5.2, "#4d5f6e"),
                           (3.2, 0.2, 0.7, cx, cy - hb - 0.05, 2.8, "#4f3a2a")])
    text("mill_sign", "MILL", (cx, cy - hb - 0.17, 2.8), 0, 0.45, "#efe6d0")
    hub = empty("mill_hub", (cx, cy - ht - 0.9, H - 1.2))
    bl = [(0.5, 0.35, 0.5, 0, 0, 0, "#4f3a2a")]
    for k in range(4):
        a = k * math.pi / 2
        dx, dz = math.cos(a), math.sin(a)
        for r in range(6):
            bl.append((0.6 if r else 0.2, 0.08, 0.6 if r else 0.2, dx * (0.8 + r * 0.6), -0.1, dz * (0.8 + r * 0.6), "#d8ccb0" if r else "#4f3a2a"))
        bl.append((0.14 if dz else 4.2, 0.12, 4.2 if dz else 0.14, dx * 2.2, -0.05, dz * 2.2, "#4f3a2a"))
    multibox("mill_blades", bl, parent=hub)
    multibox("mill_sacks", [(0.7, 0.5, 0.6, cx + 2.2 + 0.7 * i, cy - 3.2, 0.3, "#c8b890") for i in range(3)])


def barn(cx, cy):
    multibox("barn_body", [(8, 10, 5, cx, cy, 2.5, "#8a4436"), (2.8, 0.2, 3.4, cx, cy - 5.05, 1.7, "#5e2e26"),
                           (0.15, 0.25, 3.4, cx - 1.4, cy - 5.1, 1.7, "#e8e0cc"), (0.15, 0.25, 3.4, cx + 1.4, cy - 5.1, 1.7, "#e8e0cc"),
                           (2.8, 0.25, 0.15, cx, cy - 5.1, 3.4, "#e8e0cc")])
    poly("barn_roof", [(cx - 4.4, cy - 5.3, 5), (cx + 4.4, cy - 5.3, 5), (cx + 4.4, cy + 5.3, 5), (cx - 4.4, cy + 5.3, 5),
                       (cx, cy - 5.3, 8), (cx, cy + 5.3, 8)], [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], "#4a4440")
    fire = []
    for i in range(40):
        x = cx + rnd.uniform(-4, 4)
        y = cy + rnd.uniform(-5, 5)
        z = 5 + (1 - abs(x - cx) / 4.4) * 3 + rnd.uniform(0, 1.5)
        s = rnd.uniform(0.5, 1.4)
        fire.append((s, s, s * 1.6, x, y, z, rnd.choice(["#ff8a2a", "#ffb43a", "#ff6a1a"])))
    for i in range(8):
        fire.append((1.0, 0.3, 1.2, cx + rnd.uniform(-3, 3), cy - 5.1, rnd.uniform(1, 4), "#ff9a2a"))
    f = multibox("barn_fire", fire)
    for m in f.data.materials:
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Color"].default_value = b.inputs["Base Color"].default_value
        b.inputs["Emission Strength"].default_value = 4.0
    f.hide_render = True
    sm = multibox("barn_smoke", [(rnd.uniform(1.5, 3), rnd.uniform(1.5, 3), rnd.uniform(1.5, 2.5), cx + rnd.uniform(-3, 3),
                                  cy + rnd.uniform(-4, 4), 9 + i * 1.2, rnd.choice(["#3a3634", "#4a4644", "#2e2a28"])) for i in range(14)])
    sm.hide_render = True




def build(kit):
    _bind(kit)
    T, B = kit.town, kit.blocks
    T.ground(roads=[(0, 0, 160, 8), (40, 18, 4, 16), (-36, 12, 3, 18)], plazas=[(66, 0, 26, 26)],
             keep_clear=[(36, 46, 8, 36), (-110, -73, -22, 6)])
    T.houses(north=[-60, -30, -10, 0, 10, 20, 30, 50, 60], south=[-65, -45, -35, -25, -15, -5, 5, 15, 25, 35, 45, 55])
    T.bakery(-20, 14)
    T.school(-46, 14)
    T.post_office(40, 14)
    T.windmill(-36, 26)
    eli_house()
    dobbs_house()
    barn(-100, 14)
    T.town_hall(82, 0, podium=(66.6, 0))
    T.field(-92, -4, rows=17, cols=44)
    B.fence("field_f1", (-74, -22), (-110, -22))
    B.fence("field_f2", (-74, 5), (-88, 5))
    B.fence("perim", (-72, -4.5), (-72, -21))
    T.utilities(xs=(-70, -59, -45, -30, -15, 0, 15, 30, 48, 62), y=-6.2, lamps_x=(-28, -2, 22, 34, 55, 62),
                barrels_at=[(-25.5, 8.6), (-26.3, 9.3), (-62.2, 4.6), (-62.9, 5.4), (-61.4, 5.4), (72, -7), (35.5, 9.5),
                            (-4, 8.6), (16, -8.5), (5.6, -8.6), (-40, 19.5), (46, 26.5)])
    T.trees([(-60, -30), (-45, 28), (-8, -30), (12, 30), (42, -28), (55, 26), (-28, 32), (60, -22), (-55, 22), (18, -30),
             (48, 42), (15, 46), (48, 52), (12, 60), (-35, -28), (85, 20), (85, -20)])
    T.kitchen(INT_KITCHEN[0], INT_KITCHEN[1], soup=True)


def apply(stage, sh, t, gt):
    from render import smooth
    hinge = stage.ob["dh_door_hinge"]
    if sh.get("door") == "opening":
        hinge.rotation_euler.z = math.radians(-100) * smooth(t / (sh["dur"] * 0.85))
    elif sh.get("door") == "open":
        hinge.rotation_euler.z = math.radians(-100)
    else:
        hinge.rotation_euler.z = 0
    stage.ob["mill_hub"].rotation_euler.y = 0.55 * gt
    fire = bool(sh.get("fire"))
    stage.ob["barn_fire"].hide_render = not fire
    stage.ob["barn_smoke"].hide_render = not fire
    if fire:
        stage.ob["barn_fire"].scale.z = 1 + 0.12 * math.sin(23 * t)
        stage.ob["barn_smoke"].location.z = 0.6 * t
