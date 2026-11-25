"""Shared layout data for the town, sets (actor blocking) and camera prop targets."""

# Characters: name -> dict(shirt, pants, hair, scale, kind)
CAST = {
    "eli":   dict(shirt="#6f8aa3", pants="#6b5440", hair="#5a3c26", scale=0.78, kind="kid"),
    "baker": dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", scale=1.0, kind="baker"),
    "mayor": dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", scale=1.04, kind="mayor"),
    "dad":   dict(shirt="#7b8048", pants="#5b4634", hair="#3a2a1e", scale=1.02, kind="dad"),
    "pell":  dict(shirt="#8b6f85", pants="#5c4a58", hair="#b9b5ae", scale=0.96, kind="pell"),
    "t1":    dict(shirt="#a3593d", pants="#4f4436", hair="#2b211a", scale=0.98, kind="plain"),
    "t2":    dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", scale=1.0, kind="plain"),
    "t3":    dict(shirt="#4f6a8a", pants="#3e4652", hair="#1f1a16", scale=1.0, kind="mail"),
    "t4":    dict(shirt="#b8964a", pants="#5d5040", hair="#4a3426", scale=0.97, kind="plain"),
    "t5":    dict(shirt="#869468", pants="#4d4234", hair="#c09060", scale=1.0, kind="plain"),
    "t6":    dict(shirt="#7d4448", pants="#3f3a36", hair="#2f2620", scale=1.01, kind="plain"),
}

INT_KITCHEN = (0.0, 600.0)
INT_HALL = (0.0, -600.0)

# Actor blocking per set: name -> (x, y, rot_deg, act, z)
# rot: direction the actor faces (0 = +X, 90 = +Y)
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
    "safe": {"mayor": (1.9, -597.6, 134, "idle", 0)},
    "follow": {"mayor": (4, -1.2, 180, "walk_down", 0), "eli": (11, -1.7, 180, "walk", 0)},
    "gate": {"mayor": (-65.5, 0.3, 180, "look_down", 0), "eli": (-58.5, 3.5, 185, "idle", 0)},
    "gate_check": {"eli": (-66.5, 1.4, 175, "idle", 0)},
    "field": {"mayor": (-86, 0.0, 180, "walk_down", 0), "eli": (-76.5, 2.4, 190, "idle", 0)},
    "field_check": {"eli": (-80, 0.2, 180, "look_down", 0)},
    "corner": {"mayor": (30, 2.2, 90, "idle", 0), "eli": (30, 4.4, -90, "idle", 0)},
    "carrot": {"t6": (36.5, 30, 180, "idle", 0), "t2": (24, 40, 0, "idle", 0)},
    "carrot_run": {"eli": (30, 12, 90, "run", 0)},
    "kitchen": {"dad": (0, 603.3, -90, "sit", 0), "eli": (0, 599.2, 90, "idle", 0)},
    "door": {"dad": (0, 603.3, -90, "sit", 0), "eli": (0, 599.0, -90, "idle", 0)},
}
# town standing outside the kitchen door (added when the door is open)
DOOR_CROWD = {"mayor": (0, 593.3, 90, "idle", 0), "pell": (-1.35, 593.5, 90, "idle", 0),
              "baker": (1.35, 593.5, 90, "idle", 0), "t1": (-2.5, 592.3, 90, "idle", 0),
              "t3": (2.5, 592.3, 90, "idle", 0), "t5": (-0.7, 591.6, 90, "idle", 0),
              "t6": (0.75, 591.5, 90, "idle", 0), "t2": (-3.4, 590.8, 80, "idle", 0),
              "t4": (3.4, 590.8, 100, "idle", 0)}

INTERIOR_SETS = {"kitchen", "door", "safe"}

# Static prop targets: name -> (x, y, z, facing_deg)  (camera sits on the facing side)
PROPS = {
    "stall_bread": (-20, 7.3, 1.05, -90),
    "bakery_sign": (-20, 9.9, 4.3, -90),
    "hall_sign": (74.7, 0, 6.2, 180),
    "safe": (0, -595.7, 0.9, -62),
    "safe_in": (0, -595.9, 1.0, -75),
    "gate": (-70, 0, 3.2, 0),
    "carrots": (-82, 3.2, 0.3, -60),
    "eli_house": (30, 59, 2.2, -90),
    "carrot_sign": (34.2, 5.2, 2.7, -90),
    "bag": (0.45, 601.9, 0.25, -90),
    "door": (0, 595.0, 1.4, 90),
}
