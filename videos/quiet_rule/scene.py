"""The Quiet Rule - set dressing, cast, blocking (Style A)."""
import math

CAST = {
    "eli":   dict(shirt="#6f8aa3", pants="#6b5440", hair="#5a3c26", skin="#e2be96", scale=0.78, kind="kid"),
    "baker": dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker"),
    "mayor": dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor"),
    "dad":   dict(shirt="#7b8048", pants="#5b4634", hair="#3a2a1e", skin="#c49670", scale=1.02, kind="dad"),
    "pell":  dict(shirt="#8b6f85", pants="#5c4a58", hair="#b9b5ae", skin="#eccdb2", scale=0.96, kind="pell"),
    "t1":    dict(shirt="#a3593d", pants="#4f4436", hair="#2b211a", skin="#aa7a58", scale=0.98, kind="plain"),
    "t2":    dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="plain"),
    "t3":    dict(shirt="#4f6a8a", pants="#3e4652", hair="#1f1a16", skin="#96684a", scale=1.0, kind="mail"),
    "t4":    dict(shirt="#b8964a", pants="#5d5040", hair="#4a3426", skin="#e6c4a0", scale=0.97, kind="plain"),
    "t5":    dict(shirt="#869468", pants="#4d4234", hair="#c09060", skin="#cca078", scale=1.0, kind="plain"),
    "t6":    dict(shirt="#7d4448", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain"),
}
HATS = {"mayor", "baker", "t3"}
KX, KY = 0.0, 600.0      # kitchen interior
HX, HY = 0.0, -600.0     # town hall office with the safe

SETS = {
    "town": {"t3": (-10, -1.5, 0, "walk", 0), "t5": (15, 1.6, 180, "walk", 0), "t6": (25, -3, 90, "idle", 0),
             "t1": (-30, 6, 0, "idle", 0), "eli": (-3, -2, 90, "idle", 0), "t2": (31, 20, -90, "walk", 0)},
    "street": {"eli": (2, -2.6, 90, "idle", 0), "t5": (8, 1.5, 180, "walk", 0), "t6": (-7, -2.6, 0, "talk", 0),
               "t1": (-5.4, -2.6, 180, "idle", 0), "t2": (16, -0.8, 180, "walk", 0), "t4": (-12, 6.2, -90, "idle", 0)},
    "teacher": {"t4": (-30, -6.6, 90, "talk", 0), "eli": (-30, -4.5, -90, "idle", 0), "t5": (-24, 1.5, 180, "walk", 0)},
    "bakery": {"baker": (-20, 8.5, -90, "idle", 0), "t1": (-20, 5.7, 90, "idle", 0), "t5": (-13, 1.8, 180, "walk", 0)},
    "bakery_check": {"eli": (-18.6, 5.6, 125, "idle", 0), "baker": (-20, 8.5, -90, "idle", 0)},
    "bakery_walk": {"mayor": (-15, 4.2, 180, "walk_down", 0), "baker": (-20, 8.5, -90, "idle", 0)},
    "pell": {"pell": (11.6, 7, 0, "idle", 0), "t2": (18.4, 7, 180, "idle", 0)},
    "mail": {"t3": (5, -6.8, 90, "idle", 0), "t5": (12, 1.5, 180, "walk", 0)},
    "plaza": {"mayor": (66.6, 0, 180, "idle", 0.6), "eli": (59.6, 0.9, 0, "idle", 0), "t1": (59, -3.2, 0, "idle", 0),
              "t3": (58.4, -1.2, 0, "idle", 0), "t5": (58.2, 3.4, 0, "idle", 0), "t6": (58.6, 2.4, 10, "idle", 0),
              "pell": (57.2, -2.3, 0, "idle", 0), "baker": (56.9, 1.4, 0, "idle", 0), "t2": (56.2, -0.2, 0, "idle", 0),
              "t4": (55.8, -3.8, 5, "idle", 0)},
    "safe": {"mayor": (HX + 1.9, HY + 2.4, -115, "idle", 0)},
    "follow": {"mayor": (4, -1.2, 180, "walk_down", 0), "eli": (11, -1.7, 180, "walk", 0)},
    "gate": {"mayor": (-65.5, 0.3, 180, "look_down", 0), "eli": (-58.5, 3.5, 185, "idle", 0)},
    "gate_check": {"eli": (-66.5, 1.4, 175, "idle", 0)},
    "field": {"mayor": (-86, 0.0, 180, "walk_down", 0), "eli": (-76.5, 2.4, 190, "idle", 0)},
    "field_check": {"eli": (-80, 0.2, 180, "look_down", 0)},
    "corner": {"mayor": (30, 2.2, 90, "idle", 0), "eli": (30, 4.4, -90, "idle", 0)},
    "carrot": {"t6": (36.5, 30, 180, "idle", 0), "t2": (24, 40, 0, "idle", 0)},
    "carrot_run": {"eli": (30, 12, 90, "run", 0)},
    "kitchen": {"dad": (KX, KY + 3.3, -90, "sit", 0), "eli": (KX, KY - 0.8, 90, "idle", 0)},
    "door": {"dad": (KX, KY + 3.3, -90, "sit", 0), "eli": (KX, KY - 1.0, -90, "idle", 0)},
}
DOOR_CROWD = {"mayor": (KX, KY - 6.7, 90, "idle", 0), "pell": (KX - 1.35, KY - 6.5, 90, "idle", 0),
              "baker": (KX + 1.35, KY - 6.5, 90, "idle", 0), "t1": (KX - 2.5, KY - 7.7, 90, "idle", 0),
              "t3": (KX + 2.5, KY - 7.7, 90, "idle", 0), "t5": (KX - 0.7, KY - 8.4, 90, "idle", 0),
              "t6": (KX + 0.75, KY - 8.5, 90, "idle", 0), "t2": (KX - 3.4, KY - 9.2, 80, "idle", 0),
              "t4": (KX + 3.4, KY - 9.2, 100, "idle", 0)}
SETS["door"].update(DOOR_CROWD)
SETS["kitchen_open"] = dict(SETS["kitchen"], **DOOR_CROWD)
INTERIOR_SETS = {"kitchen", "kitchen_open", "door", "safe"}
SET_MOOD = {"kitchen": "interior", "kitchen_open": "interior", "door": "interior"}
LIGHTS = {"kitchen_lamp": {"kitchen", "kitchen_open", "door"}, "hall_lamp": {"safe"}}
PROPS = {
    "stall_bread": (-20, 7.3, 1.05, -90), "bakery_sign": (-20, 9.9, 4.3, -90), "hall_sign": (74.7, 0, 6.2, 180),
    "safe": (HX, HY + 4.3, 0.9, -62), "safe_in": (HX, HY + 4.1, 1.0, -75), "gate": (-70, 0, 3.2, 0),
    "carrots": (-82, 3.2, 0.3, -60), "eli_house": (30, 59, 2.2, -90), "carrot_sign": (34.2, 5.2, 2.7, -90),
    "bag": (KX + 0.45, KY + 1.9, 0.25, -90), "door": (KX, KY - 5.0, 1.4, 90), "table": (KX, KY + 2.0, 1.0, -90),
}
FAR_PROPS = {"eli_house"}
STRAIGHT_PROPS = {"eli_house"}


def build(kit):
    T, B = kit.town, kit.blocks
    T.ground(roads=[(0, 0, 152, 8), (30, 34, 6, 60)], plazas=[(66, 0, 26, 26)],
             keep_clear=[(26, 34, 3, 64), (-110, -73, -20, 20)])
    north = [x for x in range(-50, 51, 10) if x not in (-40, -20, 30)]
    T.houses(north=north, south=list(range(-50, 51, 10)))
    T.bakery(-20, 14)
    T.school(-42, 14)
    B.fence("pell_fence", (15, 6.0), (15, 10.2))
    B.fence("yard_n", (-56, 9.5), (-48, 9.5))
    B.fence("yard_n2", (35, 9.5), (56, 9.5))
    B.fence("yard_s", (-56, -9.2), (56, -9.2))
    for i, yy in enumerate((22, 32, 42, 52)):
        B.house(f"carrot_w{i}", 22, yy, 0, w=6, d=6.5, h=3.3)
        B.house(f"carrot_e{i}", 38, yy, 180, w=6, d=6.5, h=3.3)
    B.house("eli_house", 30, 62, -90, w=6, d=6, h=3.3, wall="#8b9aa6", roof="#5e4c3e")
    B.fence("eli_fence_l", (25.5, 58.2), (28.4, 58.2))
    B.fence("eli_fence_r", (31.6, 58.2), (34.5, 58.2))
    T.sign("carrot_sign", 34.2, 5.3, -90, "CARROT ST", w=2.6, h=0.6, post=2.75, board="#4f6b4a", size=0.36)
    T.town_hall(82, 0, podium=(66.6, 0))
    B.multibox("gate", [(0.7, 0.7, 6.5, -70, -4.8, 3.25, "#6a4e36"), (0.7, 0.7, 6.5, -70, 4.8, 3.25, "#6a4e36"),
                        (0.6, 11.4, 0.7, -70, 0, 6.2, "#5e4430"), (0.5, 10.4, 0.35, -70, 0, 5.4, "#5e4430")])
    for side, sgn in (("l", -1), ("r", 1)):
        planks = [(0.12, 0.42, 4.2, 0, 0.22 + i * 0.47, 2.2, "#7b5d40") for i in range(9)]
        planks += [(0.16, 4.4, 0.3, 0, 2.2, 1.2, "#5f4630"), (0.16, 4.4, 0.3, 0, 2.2, 3.4, "#5f4630")]
        g = B.multibox(f"gate_door_{side}", planks, loc=(-70, sgn * 4.4, 0))
        g.rotation_euler.z = math.radians(-40) if sgn < 0 else math.radians(220)
    B.text("gate_sign", "TOWN", (-69.6, 0, 6.2), math.radians(90), 0.5, "#e8dcc0")
    B.fence("perim_l", (-70, -5.2), (-70, -40))
    B.fence("perim_r", (-70, 5.2), (-70, 40))
    T.field(-92, 0, rows=23, cols=44)
    T.utilities(xs=(-60, -45, -30, -15, 0, 15, 30, 45, 60), y=-6.2, lamps_x=(-45, -30, -2, 40, 55, 62),
                barrels_at=[(-25.5, 8.6), (-26.3, 9.3), (-63, 4.6), (-62.2, 5.5), (-59.2, 4.6), (72, -7), (72.8, -7.7),
                            (35.5, 7.5), (-4, 8.6), (16, -8.5), (5.6, -8.6)])
    T.trees([(-60, -30), (-45, 28), (-8, -30), (12, 30), (42, -28), (55, 26), (-28, 32), (60, -22), (-55, 22), (18, -30),
             (45, 40), (15, 46), (48, 52), (12, 60), (-35, -28), (85, 20), (85, -20)])
    # kitchen with a tall front door (so the crowd's blank faces show) + the bag under the table
    T.kitchen(KX, KY, soup=False, door=(KX - 0.8, KX + 0.8, 3.0))
    B.cyl("bag", 0.34, 0.5, (KX + 0.45, KY + 1.9, 0.1), "#8f7350", seg=7, r2=0.22)
    B.cyl("bag_neck", 0.12, 0.16, (KX + 0.45, KY + 1.9, 0.6), "#7e6444", seg=6, r2=0.18)
    hinge = B.empty("door_hinge", (KX - 0.8, KY - 5, 0))
    B.multibox("door_panel", [(1.6, 0.1, 2.98, 0.8, 0, 1.49, "#6a4a30"), (0.12, 0.14, 0.12, 1.4, 0.08, 1.2, "#c8a85a")], parent=hinge)
    B.multibox("door_frame", [(0.15, 0.2, 3.1, KX - 0.88, KY - 5, 1.55, "#4f3a28"), (0.15, 0.2, 3.1, KX + 0.88, KY - 5, 1.55, "#4f3a28"),
                              (1.9, 0.2, 0.15, KX, KY - 5, 3.05, "#4f3a28")])
    B.house("k_out1", KX - 9, KY - 18, 90, w=7, d=7, h=3.6)
    B.house("k_out2", KX + 6, KY - 19, 90, w=7, d=7, h=3.8)
    B.multibox("k_street", [(60, 8, 0.04, KX, KY - 10, 0.02, "#a68a66")])
    B.pole("k_pole", KX + 4, KY - 7)
    B.lamp("k_lamp", KX - 4, KY - 7)
    T.office_safe(HX, HY, name="hall")


def apply(stage, sh, t, gt):
    from render import smooth
    hinge = stage.ob["door_hinge"]
    door = sh.get("door")
    if door == "opening":
        hinge.rotation_euler.z = math.radians(-105) * smooth(t / (sh["dur"] * 0.8))
    elif door == "open" or sh["set"] in ("door", "kitchen_open"):
        hinge.rotation_euler.z = math.radians(-105)
    else:
        hinge.rotation_euler.z = 0
    if sh["set"] in ("door", "kitchen_open"):
        for n in DOOR_CROWD:
            if n not in sh.get("faces", {}):
                stage.set_face(n, "blank")


def cam_override(stage, sh, t, actors, T, f, u):
    from mathutils import Vector
    from render import lerp, rot2
    cam, tgt = sh["cam"], sh["tgt"]
    if sh["set"] == "door" and tgt in actors and cam in ("ecu", "cu") and tgt in DOOR_CROWD:
        hat = tgt in HATS
        pos = Vector((T.x + lerp(0.08, -0.04, u) * (1 if T.x >= 0 else -1), KY - 5.1, T.z + (0.2 if hat else 0.04)))
        return pos, T + Vector((0, 0, 0.3 if hat else 0.0)), 30 if hat else 40
    if tgt == "safe" and cam in ("push", "whip", "prop"):
        a, b = (Vector((HX + 3.6, HY - 1.8, 2.3)), Vector((HX + 1.9, HY + 0.7, 1.8))) if cam == "push" else \
               (Vector((HX + 2.2, HY + 0.0, 1.9)), Vector((HX + 1.6, HY + 1.0, 1.9)))
        pos = a.lerp(b, u)
        look = T.copy()
        if cam == "whip":
            from render import smooth
            w = 1 - smooth(min(1.0, t / 0.24))
            dv = T - pos
            look = pos + rot2(dv, 85 * w) + Vector((0, 0, dv.z))
        return pos, look, 32
    if tgt == "safe_in" and cam in ("prop", "ecu"):
        return T + rot2(f, 18) * lerp(2.2, 1.6, u) + Vector((0, 0, 0.5)), T, 40
    return None
