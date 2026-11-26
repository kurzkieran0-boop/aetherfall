"""Shared layout: cast, actor blocking per set, camera prop targets for "The Mailman Skips Our House"."""

# name -> look
CAST = {
    "eli":    dict(shirt="#6f8aa3", pants="#6b5440", hair="#5a3c26", skin="#e2be96", scale=0.78, kind="kid"),
    "eli2":   dict(shirt="#6f8aa3", pants="#6b5440", hair="#5a3c26", skin="#e2be96", scale=0.78, kind="kid"),
    "dobbs":  dict(shirt="#4f6a8a", pants="#3e4652", hair="#5a4a3a", skin="#d8a882", scale=1.06, kind="mail"),
    "mom":    dict(shirt="#a3735a", pants="#5c4a40", hair="#6a4428", skin="#e6c4a0", scale=0.98, kind="mom"),
    "dad":    dict(shirt="#7b8048", pants="#5b4634", hair="#3a2a1e", skin="#c49670", scale=1.02, kind="dad"),
    "baker":  dict(shirt="#e9e4d8", pants="#7a6a58", hair="#3b2b20", skin="#d6ac84", scale=1.0, kind="baker"),
    "pell":   dict(shirt="#8b6f85", pants="#5c4a58", hair="#b9b5ae", skin="#eccdb2", scale=0.96, kind="pell"),
    "mayor":  dict(shirt="#5b5e62", pants="#45474b", hair="#9a9a96", skin="#e8c8a8", scale=1.04, kind="mayor"),
    "harlan": dict(shirt="#8a6a48", pants="#4a5a6a", hair="#d8d4cc", skin="#d4a884", scale=0.98, kind="farmer"),
    "t1":     dict(shirt="#a3593d", pants="#4f4436", hair="#2b211a", skin="#aa7a58", scale=0.98, kind="plain"),
    "t2":     dict(shirt="#5f8580", pants="#5a4b3a", hair="#7a4e2a", skin="#deb890", scale=1.0, kind="plain"),
    "t3":     dict(shirt="#b8964a", pants="#5d5040", hair="#4a3426", skin="#96684a", scale=0.97, kind="plain"),
    "t4":     dict(shirt="#869468", pants="#4d4234", hair="#c09060", skin="#cca078", scale=1.0, kind="plain"),
    "t5":     dict(shirt="#7d4448", pants="#3f3a36", hair="#2f2620", skin="#b88864", scale=1.01, kind="plain"),
}
HATS = {"dobbs", "mayor", "baker", "harlan"}

INT_KITCHEN = (0.0, 600.0)
DOBBS_HOUSE = (40.0, 30.0)      # tiny blue house behind the post office (has a real interior)
ELI_HOUSE = (-55.0, -14.0)

# actor blocking: name -> (x, y, facing_deg, act, z)
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
# props held in the right hand (object name per holder)
HELD = {"eli", "eli2", "dobbs", "mayor", "baker", "pell", "harlan"}

INTERIOR_SETS = {"kitchen", "int", "int_door", "int_talk", "int_final"}
NIGHT_SETS = {"night_st", "dobbs_ext", "window", "int", "int_door", "int_talk", "int_final"}

# camera prop targets: name -> (x, y, z, facing_deg)   camera sits on the facing side
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
