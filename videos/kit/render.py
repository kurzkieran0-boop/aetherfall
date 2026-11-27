"""Shot renderer (bpy, Eevee, headless). Resume-safe; every frame render goes through the shared render semaphore.

blender -b -P kit/render.py -- <slug> [--only shot_001,shot_002] [--still OUT_DIR] [--res WxH]
(or python kit/render.py ... with the bpy module).  KIT_PREVIEW=1 -> 540x960, 1 sample, frames_preview/.

Reads videos/<slug>/{scene.py, shots.json}. Scene module provides CAST, SETS, PROPS and optional
HATS, ROOMS {set: (x0, x1, y0, y1, zmax)}, LIGHTS {light_obj: [sets]}, SET_MOOD {set: mood}, apply(stage, sh, t, gt).
"""
import bpy, json, math, os, sys, time
from pathlib import Path
from mathutils import Vector, Quaternion, Euler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import video, bdir, vdir, render_slot, args, preview, frames_dir, FACE_EXPR, DIGITS
import progress, kit_gpu

RFPS = int(os.environ.get("KIT_RENDER_FPS") or (15 if os.environ.get("KIT_PREVIEW") == "1" else 30))


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c] + [1]


MOODS_A = {
    "day":      (52, 220, 3.6, "#fff2dc", "#e6dcc4", "#c9d3d6", "#8fa9bf", 1.0),
    "golden":   (28, 250, 3.2, "#ffd9a8", "#efcf9e", "#c9c3b4", "#8e9fb2", 1.1),
    "dusk":     (15, 235, 2.4, "#ffb68a", "#e3a27c", "#a08f94", "#4f5a76", 1.25),
    "night":    (40, 150, 1.7, "#a8bcf0", "#55658f", "#3a4670", "#1c2442", 3.2),
    "interior": (68, 230, 1.5, "#ffe2bc", "#d9a685", "#8f8592", "#4a5370", 0.7),
}
MOODS_B = {   # brighter, warmer, softer sky
    "day":      (50, 215, 4.6, "#fff0d6", "#eef2f0", "#b8d8ee", "#6aa6dc", 1.35),
    "golden":   (24, 250, 4.0, "#ffcf96", "#ffe2b8", "#d8d8d0", "#7aa4cc", 1.3),
    "dusk":     (14, 240, 3.0, "#ffa878", "#f0a882", "#b098a8", "#506890", 1.4),
    "night":    (40, 150, 1.8, "#a8bcf0", "#5a6a96", "#3c4a78", "#1c2648", 3.4),
    "interior": (68, 230, 2.0, "#ffe6c4", "#f0c8a0", "#a8a0a8", "#5a6888", 0.9),
}


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def rot2(v, deg):
    a = math.radians(deg)
    return Vector((v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a), 0))


def fdir(deg):
    return Vector((math.cos(math.radians(deg)), math.sin(math.radians(deg)), 0))


def counter_at(keys, t):
    """keys: [(time, value, mode)] sorted; mode 'step' (jump at time) or 'ramp' (tick down from previous key)."""
    if not keys:
        return None
    v = keys[0][1]
    prev_t, prev_v = keys[0][0], keys[0][1]
    for kt, kv, mode in keys:
        if t >= kt:
            v, prev_t, prev_v = kv, kt, kv
            continue
        if mode == "ramp" and kt > prev_t:
            u = (t - prev_t) / (kt - prev_t)
            return int(round(prev_v + (kv - prev_v) * u))
        return v
    return v


def png_ok(p):
    """A frame is usable only if it is a complete PNG (a reboot / full disk can leave zero-filled or cut-off files)."""
    try:
        sz = p.stat().st_size
        if sz < 64:
            return False
        with open(p, "rb") as f:
            head = f.read(8)
            f.seek(-8, 2)
            tail = f.read(8)
        return head == b"\x89PNG\r\n\x1a\n" and tail == b"IEND\xaeB`\x82"
    except OSError:
        return False


class Stage:
    def __init__(self, slug, res=None):
        self.slug = slug
        self.cfg, self.story, self.scene = video(slug)
        self.B = bdir(slug)
        bpy.ops.wm.open_mainfile(filepath=str(self.B / "town.blend"))
        self.sc = bpy.context.scene
        self.sc.render.image_settings.color_mode = "RGB"      # no alpha channel: ~25% smaller frames on disk
        self.device = kit_gpu.setup()
        w, h = (res or os.environ.get("KIT_RES") or ("540x960" if preview() else "1080x1920")).split("x")
        self.sc.render.resolution_x, self.sc.render.resolution_y = int(w), int(h)
        samples = 1 if preview() else int(os.environ.get("KIT_SAMPLES", getattr(self.cfg, "SAMPLES", 8)))
        from blocks import set_eevee
        set_eevee(self.sc, samples)
        self.sc.render.use_persistent_data = True
        self.cam = bpy.data.objects["cam"]
        self.sun = bpy.data.objects["sun"]
        self.ramp = self.sc.world.node_tree.nodes["SKYRAMP"]
        self.bg = self.sc.world.node_tree.nodes["SKYBG"]
        self.ob = bpy.data.objects
        self.CAST = self.scene.CAST
        self.HATS = getattr(self.scene, "HATS", set())
        faces = self.B / "faces"
        self.imgs = {(n, e): bpy.data.images.load(str(faces / f"{n}_{e}.png"), check_existing=True)
                     for n in self.CAST for e in FACE_EXPR}
        self.face_node = {n: self.ob[n + "_face"].active_material.node_tree.nodes["FACE"] for n in self.CAST}
        self.cur = {}
        self.counter = bool(getattr(self.cfg, "COUNTER", None))
        if self.counter:
            self.dig = {(s, c): bpy.data.images.load(str(DIGITS / f"{s}_{c}.png"), check_existing=True)
                        for s in ("teal", "red", "dim") for c in list("0123456789") + ["blank"]}
            self.dig_nodes = {n: [self.ob[f"{n}_digit{i}"].active_material.node_tree.nodes["DIG"] for i in range(4)]
                              for n in self.CAST if f"{n}_digit0" in self.ob}
        sj = json.loads((vdir(slug) / "shots.json").read_text())
        self.ckeys = sj.get("counters", {})
        self.moods = MOODS_B if self.cfg.STYLE == "B" else MOODS_A

    # ------------------------------------------------------------------ lighting
    def mood(self, m):
        el, az, st, sc, hz, mid, top, bgs = self.moods[m]
        self.sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(az)), "XYZ")
        self.sun.data.energy = st
        self.sun.data.color = lin(sc)[:3]
        els = sorted(self.ramp.color_ramp.elements, key=lambda e: e.position)
        els[0].color, els[1].color, els[2].color = lin(hz), lin(mid), lin(top)
        self.bg.inputs["Strength"].default_value = bgs

    def lights_for(self, sh):
        light = getattr(self.scene, "SET_MOOD", {}).get(sh["set"], sh.get("light", "day"))
        if sh.get("light_force"):
            light = sh["light_force"]
        self.mood(light)
        for lname, sets in getattr(self.scene, "LIGHTS", {}).items():
            if lname in self.ob:
                self.ob[lname].hide_render = sh["set"] not in sets

    # ------------------------------------------------------------------ actors
    def set_face(self, n, e):
        if self.cur.get(n) != e:
            self.face_node[n].image = self.imgs[(n, e)]
            self.cur[n] = e

    def set_counter(self, n, value, gt):
        if n not in self.dig_nodes or value is None:
            return
        value = max(0, int(value))
        red = value < 300
        blink_off = red and value > 0 and (gt * 2.4) % 1.0 > 0.62
        style = "dim" if blink_off else ("red" if red else "teal")
        s = str(value).rjust(4)[-4:]
        for i, ch in enumerate(s):
            key = (style, "blank" if ch == " " else ch)
            node = self.dig_nodes[n][i]
            if self.cur.get((n, i)) != key:
                node.image = self.dig[key]
                self.cur[(n, i)] = key

    def show_held(self, n, kind):
        for ob in self.ob:
            if ob.name.startswith(f"{n}_held_"):
                vis = kind is not None and (ob.name == f"{n}_held_{kind}" or ob.name.startswith(f"{n}_held_{kind}_text"))
                ob.hide_render = not vis

    def pose(self, n, spec, act, t, face, seed, sh):
        x, y, rot, _, z = spec
        s = self.CAST[n]["scale"]
        root = self.ob[n + "_root"]
        legL, legR = self.ob[n + "_legL"], self.ob[n + "_legR"]
        armL, armR = self.ob[n + "_armL"], self.ob[n + "_armR"]
        head = self.ob[n + "_head"]
        for o in (legL, legR, armL, armR, head, root):
            o.rotation_euler = (0, 0, 0)
        act, _, prop = act.partition(":")
        rot = rot + sh.get("turned", {}).get(n, 0)
        if act == "turn":
            rot = rot + 180 * smooth((t - 0.15) / 0.55)
        f = fdir(rot)
        pos = Vector((x, y, z))
        ph = seed * 0.37
        fc = face
        held = None
        if act in ("walk", "walk_down", "run", "sneak", "paddle_walk"):
            speed, freq, amp = {"walk": (1.35, 1.7, 0.55), "walk_down": (1.5, 1.8, 0.45), "run": (3.8, 2.8, 0.9),
                                "sneak": (0.7, 1.1, 0.35), "paddle_walk": (0.0, 1.0, 0.0)}[act]
            pos += f * speed * t
            sw = math.sin(2 * math.pi * freq * t + ph)
            legL.rotation_euler.x, legR.rotation_euler.x = amp * sw, -amp * sw
            armL.rotation_euler.x, armR.rotation_euler.x = -amp * 0.9 * sw, amp * 0.9 * sw
            pos.z += 0.05 * abs(math.sin(2 * math.pi * freq * t + ph))
            if act == "walk_down":
                head.rotation_euler.x = -0.4
            if act == "run":
                head.rotation_euler.z = 0.25 * math.sin(2.1 * t)
            if act == "sneak":
                pos.z -= 0.12
                armL.rotation_euler.x = armR.rotation_euler.x = 0.5
                head.rotation_euler.z = 0.35 * math.sin(1.4 * t + ph)
        elif act in ("sit", "sit_talk"):
            pos.z = z + 0.56 - 0.9 * s
            legL.rotation_euler.x = legR.rotation_euler.x = 1.57
            armL.rotation_euler.x = armR.rotation_euler.x = 1.0
            head.rotation_euler.x = 0.03 * math.sin(0.8 * t)
            if act == "sit_talk":
                act = "talk"
        elif act == "lie":     # collapsed on the ground, face up
            root.rotation_euler.x = 1.5
            pos.z = z + 0.32 * s
            armL.rotation_euler.y, armR.rotation_euler.y = -0.6, 0.6
        else:
            armL.rotation_euler.x = 0.04 * math.sin(1.3 * t + ph)
            armR.rotation_euler.x = -0.04 * math.sin(1.3 * t + ph)
            head.rotation_euler.z = 0.08 * math.sin(0.6 * t + ph)
            pos.z += 0.01 * math.sin(2.0 * t + ph)
        if act == "look_down":
            head.rotation_euler.x = -0.5
        if act == "look_up":
            head.rotation_euler.x = 0.35
        if act in ("talk", "whisper", "laugh", "yell", "sing"):
            amp = {"whisper": 0.15, "yell": 0.6, "sing": 0.35}.get(act, 0.3)
            armR.rotation_euler.x = 0.55 + amp * math.sin(4.2 * t + ph)
            armR.rotation_euler.y = 0.15
            if act == "yell":
                armL.rotation_euler.x = 0.9 + 0.3 * math.sin(4.0 * t)
                armL.rotation_euler.y = -0.4
                head.rotation_euler.x = 0.12
            if act == "sing":
                armL.rotation_euler.y = -0.5 - 0.2 * math.sin(2 * t)
                armR.rotation_euler.y = 0.5 + 0.2 * math.sin(2 * t + 1)
                head.rotation_euler.y = 0.14 * math.sin(2.4 * t)
            head.rotation_euler.x += (0.18 if act == "laugh" else 0.06) * math.sin((9 if act == "laugh" else 5) * t)
            if act == "laugh":
                fc = "laughing"
            elif face in ("neutral", "talk"):
                fc = "talk" if int(t * 7 + seed) % 2 == 0 else "neutral"
            elif act in ("whisper", "yell", "sing"):
                fc = "talk" if int(t * 6) % 2 == 0 else face
        if act == "point":
            armR.rotation_euler.x = 1.6
        if act == "clap":
            u = abs(math.sin(7 * t))
            armL.rotation_euler.x = armR.rotation_euler.x = 1.2
            armL.rotation_euler.z, armR.rotation_euler.z = 0.5 * u, -0.5 * u
        if act == "wave":
            armR.rotation_euler.y = 2.4
            armR.rotation_euler.x = 0.3 * math.sin(8 * t)
        if act == "sign":      # hand signals
            armR.rotation_euler.x = 1.1 + 0.4 * math.sin(6 * t)
            armL.rotation_euler.x = 1.0 + 0.4 * math.sin(6 * t + 2)
            armR.rotation_euler.z = 0.3 * math.sin(5 * t)
        if act == "nod":
            head.rotation_euler.x = 0.25 * abs(math.sin(4 * t))
        if act == "shrug":
            u = smooth(t / 0.5)
            armL.rotation_euler.y, armR.rotation_euler.y = -0.45 * u, 0.45 * u
            armL.rotation_euler.x = armR.rotation_euler.x = 0.35 * u
        if act == "hug":
            armL.rotation_euler.x = armR.rotation_euler.x = 1.4
            armL.rotation_euler.z, armR.rotation_euler.z = -0.7, 0.7
        if act in ("read", "hold", "give", "eat", "drink", "pour"):
            held = prop or (self.CAST[n].get("held") or [None])[0]
            armR.rotation_euler.x = {"read": 1.25, "hold": 0.75, "give": 1.45, "eat": 2.3, "drink": 2.5, "pour": 1.6}[act]
            if act == "read":
                armL.rotation_euler.x = 1.1
                head.rotation_euler.x = -0.18
            if act == "eat":
                armR.rotation_euler.x = 2.3 - 0.5 * abs(math.sin(5 * t))
                fc = "talk" if int(t * 6) % 2 == 0 else face
            if act == "drink":
                head.rotation_euler.x = 0.25
        if act == "shake":
            armL.rotation_euler.x = armR.rotation_euler.x = 0.9 + 0.06 * math.sin(41 * t)
        if act == "peek":
            pos.z += 0.04 * math.sin(1.2 * t)
            armL.rotation_euler.x = armR.rotation_euler.x = 1.25
            armL.rotation_euler.z, armR.rotation_euler.z = -0.25, 0.25
            head.rotation_euler.z = 0.25 * math.sin(0.9 * t)
        if act == "stagger":
            u = smooth(t / 0.5)
            root.rotation_euler.x = -0.35 * u
            armL.rotation_euler.y, armR.rotation_euler.y = -1.2 * u, 1.2 * u
        if act == "head_turn":
            head.rotation_euler.z = 0.8 * smooth(t / 0.5)
        if act == "head_turn_r":
            head.rotation_euler.z = -0.8 * smooth(t / 0.5)
        if act == "paddle":
            armL.rotation_euler.x = armR.rotation_euler.x = 1.0 + 0.5 * math.sin(4 * t)
            armL.rotation_euler.y, armR.rotation_euler.y = -0.4, 0.4
            pos.z = z + 0.56 - 0.9 * s
            legL.rotation_euler.x = legR.rotation_euler.x = 1.57
        if act == "cry":
            fc = "scared"
            head.rotation_euler.x = -0.2 + 0.05 * math.sin(10 * t)
            armL.rotation_euler.x = armR.rotation_euler.x = 1.6
        root.location = pos
        root.rotation_euler.z = math.radians(rot - 90)
        self.set_face(n, fc)
        self.show_held(n, held)
        if n + "_cap" in self.ob:
            self.ob[n + "_cap"].location.z = 0.49 if sh.get("capdown") else 0.72
        return pos

    # ------------------------------------------------------------------ targets
    def head_pos(self, n):
        return self.ob[n + "_head"].matrix_world @ Vector((0, 0, 0.33))

    def facing(self, n):
        return math.degrees(self.ob[n + "_root"].rotation_euler.z) + 90

    def target(self, tgt, actors):
        if tgt in actors:
            return self.head_pos(tgt), fdir(self.facing(tgt)), self.CAST[tgt]["scale"], True
        if tgt.startswith("pt:"):
            x, y, z = map(float, tgt[3:].split(","))
            return Vector((x, y, z)), fdir(-90), 1.0, False
        if tgt.endswith("_chest"):
            n = tgt[:-6]
            p = self.ob[n + "_torso"].matrix_world @ Vector((0, 0.3, 1.43))
            return p, fdir(self.facing(n)), 0.5, False
        if "_held_" in tgt:
            p = self.ob[tgt].matrix_world.translation.copy()
            return p, fdir(self.facing(tgt.split("_held_")[0])), 0.45, False
        if tgt in self.ob and tgt not in self.scene.PROPS:
            p = self.ob[tgt].matrix_world.translation.copy()
            return p, fdir(-90), 1.0, False
        for suffix, off in (("_feet", (0.3, 0.15)), ("_hand", None)):
            if tgt.endswith(suffix) and tgt[:-len(suffix)] in actors:
                n = tgt[:-len(suffix)]
                if suffix == "_hand":
                    return self.hand_pos(n), fdir(self.facing(n) - 90), 0.8, False
                r = self.ob[n + "_root"]
                f = fdir(self.facing(n))
                return r.location + f * off[0] + Vector((0, 0, off[1])), f, 1.0, False
        x, y, z, fd = self.scene.PROPS[tgt]
        if isinstance(x, str):          # prop that follows an object: ("obj_name", dx, dy, dz) style
            o = self.ob[x]
            p = o.matrix_world @ Vector((y, z, fd[0]))
            return p, fdir(fd[1]), 1.0, False
        return Vector((x, y, z)), fdir(fd), 1.0, False

    def hand_pos(self, n):
        return self.ob[n + "_armR"].matrix_world @ Vector((0, 0, -0.75))

    # ------------------------------------------------------------------ camera
    def cam_rig(self, sh, t, actors, ang_bias):
        cam = sh["cam"]
        dur = sh["dur"]
        u = smooth(t / max(dur, 0.01))
        T, f, k, is_actor = self.target(sh["tgt"], actors)
        side = Vector((-f.y, f.x, 0))
        rooms = getattr(self.scene, "ROOMS", {})
        interior = sh["set"] in rooms or sh["set"] in getattr(self.scene, "INTERIOR_SETS", set())
        im = 0.45 if interior else 1.0
        lens, roll = 35, 0.0
        look = T.copy()
        ground = 0.0
        if is_actor:
            ground = self.ob[sh["tgt"] + "_root"].location.z if actors[sh["tgt"]][3] not in ("sit", "paddle") else 0.0
        far_props = set(getattr(self.scene, "FAR_PROPS", ()))

        def around(d, ang, dz):
            if sh["tgt"] in getattr(self.scene, "STRAIGHT_PROPS", ()):
                ang = 2
            return T + rot2(f, ang + ang_bias) * d + Vector((0, 0, dz))

        hat = is_actor and sh["tgt"] in self.HATS
        if cam == "ecu":
            pos = around(lerp(2.05, 1.6, u) * k * (1.5 if hat else 1.0), 8, 0.22 if hat else 0.06); lens = 40
            look = T + Vector((0, 0, (0.38 if hat else 0.07) * k))
            if not is_actor:
                pos = around(lerp(1.15, 0.9, u), 15, 0.12); lens = 40
        elif cam == "counter":   # extreme close-up on the chest counter
            C = self.ob[sh["tgt"] + "_torso"].matrix_world @ Vector((0, 0.3, 1.43))
            fa = fdir(self.facing(sh["tgt"]))
            sc_ = self.CAST[sh["tgt"]]["scale"]
            pos = C + rot2(fa, 10 + ang_bias) * lerp(2.6, 2.0, u) * sc_ + Vector((0, 0, 0.05)); lens = 40
            look = C
        elif cam == "cu":
            pos = around(lerp(2.5, 2.0, u) * k * (1.3 if hat else 1.0), 22, 0.15); lens = 40
            look = T + Vector((0, 0, (0.3 if hat else 0.0) * k))
        elif cam == "mcu":   # chest-up: face AND counter in frame
            pos = around(lerp(3.1, 2.6, u) * k * (1.2 if hat else 1.0), 18, -0.2); lens = 40
            look = T - Vector((0, 0, 0.42 * k))
        elif cam in ("push", "pull"):
            a, b = (7.5, 3.6) if cam == "push" else (3.4, 7.8)
            if not is_actor:
                a, b = a * 1.3, b * 1.3
            if sh["tgt"] in far_props:
                a, b = 26, 13
            pos = around(lerp(a, b, u) * k * im, 28, 0.7); lens = 35
            look = T - Vector((0, 0, 0.35 if is_actor else 0))
        elif cam == "low":
            p = around(lerp(3.4, 2.7, u) * k * (0.8 if interior else 1), -24, 0)
            p.z = ground + 0.32
            pos = p; lens = 22; look = T + Vector((0, 0, 0.15))
        elif cam == "high":
            if is_actor:
                pos = around(3.6 * k * (0.7 if interior else 1), 15 + 12 * u, 0)
                pos.z = T.z + (1.0 if interior else 5.5); lens = 24 if interior else 28
                look = T - Vector((0, 0, 0.8))
            else:
                pos = around(lerp(15, 13, u), 20 + 10 * u, 0)
                pos.z = T.z + 12; lens = 28; look = T + Vector((0, 0, 1.0))
        elif cam == "ots":
            O = self.head_pos(sh["over"])
            d2 = (T - O); d2.z = 0
            d2 = d2.normalized() if d2.length > 1e-4 else Vector((1, 0, 0))
            perp = Vector((-d2.y, d2.x, 0))
            back = lerp(1.9, 1.6, u) * (0.6 if interior else 1.0)
            pos = O - d2 * back + perp * (0.6 if interior else 0.95) + Vector((0, 0, 0.28)); lens = 38 if interior else 42
        elif cam == "whip":
            pos = around(3.0 * k, 20, 0.15); lens = 35
            w = 1 - smooth(min(1.0, t / 0.24))
            dv = (T - pos)
            look = pos + rot2(dv, 85 * w) + Vector((0, 0, dv.z))
        elif cam == "track":
            pos = T + side * 3.6 + f * 1.4 + Vector((0, 0, -0.35)); lens = 30
            look = T + f * 0.6
        elif cam == "chase":
            pos = T - f * lerp(6.2, 5.4, u) + side * 1.1 + Vector((0, 0, 1.5)); lens = 26
            look = T + f * 5.0 - Vector((0, 0, 1.2))
        elif cam == "tilt":
            pos = T + rot2(f, 12 + ang_bias) * 3.2 * k + Vector((0, 0, -0.5)); lens = 35
            look = T - Vector((0, 0, 1.9 * k * (1 - u)))
        elif cam == "orbit":
            pos = around(3.6 * k * im, lerp(-45, 45, u), 0.3); lens = 35
        elif cam == "dutch":
            pos = around(lerp(2.3, 1.9, u) * k * (1.3 if hat else 1), -18, 0.1); lens = 40; roll = 13
            if not is_actor:
                pos = around(lerp(2.0, 1.6, u), -18, 0.3)
        elif cam == "wide":
            pos = around(lerp(13, 10.5, u) * im, 18, 2.5); lens = 28
            if not is_actor:
                pos = around(lerp(19, 15, u), 18, 1.5)
        elif cam == "drone":
            a = math.radians(205 + 40 * u)
            r = float(sh.get("radius", 48))
            pos = T + Vector((math.cos(a) * r, math.sin(a) * r, r * 0.66 - 4 * u)); lens = 28
        elif cam == "prop":
            pos = around(lerp(2.4, 1.6, u) * (0.55 if T.z < 1.5 and not interior else 1.0), 18, 0.6); lens = 40
            if sh["tgt"] in far_props:
                pos = around(lerp(12, 9, u), 15, 0.5)
            if "_held_" in sh["tgt"]:
                pos = around(lerp(1.7, 1.35, u), 20, 0.3)
        elif cam == "sky":
            pos = T + f * 2.4 + Vector((0, 0, -1.5)); lens = 24
            look = lerp(T, T + Vector((0, 0, 9)) - f * 3, u)
        elif cam == "pan":
            pos = T + f * 2.1 + Vector((0, 0, -0.1)); lens = 28
            look = T + side * lerp(-1.6, 1.6, u)
        elif cam == "orbit_room":
            a = math.radians(lerp(-30, 70, u) + 40)
            pos = T + Vector((0.3, -0.3, 0)); lens = 22
            look = pos + Vector((math.cos(a) * 3, math.sin(a) * 3, 0.35))
        elif cam == "tilt_wall":
            pos = T + f * 1.9 + Vector((0, 0, -0.4)); lens = 24
            look = T + Vector((0, 0, lerp(-1.4, 1.1, u)))
        elif cam == "ecu_wall":
            pos = T + f * 0.62 + side * lerp(-0.35, 0.35, u) + Vector((0, 0, lerp(-0.1, 0.1, u))); lens = 32
            look = pos - f * 1.0 + side * 0.15
        elif cam == "shelf_pan":
            pos = T + f * 0.95 + side * lerp(-0.85, 0.85, u) + Vector((0, 0, 0.05)); lens = 35
            look = pos - f * 1.0
        elif cam == "ecu_hook":
            pos = T + f * lerp(0.75, 0.5, u) + Vector((0, 0, 0.05)); lens = 40
        elif cam == "hands":
            n = sh["tgt"]
            H = (self.hand_pos(n) + self.ob[n + "_armL"].matrix_world @ Vector((0, 0, -0.75))) / 2
            fa = fdir(self.facing(n))
            pos = H + rot2(fa, 30) * lerp(1.7, 1.4, u) + Vector((0, 0, 0.35)); lens = 35
            look = H + Vector((0, 0, 0.12))
        else:
            pos = around(3.0, 20, 0.2)
        if hasattr(self.scene, "cam_override"):
            r = self.scene.cam_override(self, sh, t, actors, T, f, u)
            if r:
                pos, look, lens = r[0], r[1], r[2]
                roll = r[3] if len(r) > 3 else roll
        if sh["set"] in rooms:
            x0, x1, y0, y1, zmax = rooms[sh["set"]]
            pos.x = min(max(pos.x, x0 + 0.05), x1 - 0.05)
            pos.y = min(max(pos.y, y0 + 0.05), y1 - 0.05)
            pos.z = min(max(pos.z, 0.3), zmax)
        sd = sh["seed"]
        pos = pos + Vector((0.016 * math.sin(13 * t + sd), 0.016 * math.sin(11 * t + 2 * sd), 0.012 * math.sin(17 * t + sd)))
        if pos.z < 0.2:
            pos.z = 0.2
        return pos, look, lens, roll

    def place_cam(self, pos, look, lens, roll):
        q = (look - pos).to_track_quat("-Z", "Y")
        if roll:
            q = q @ Quaternion((0, 0, 1), math.radians(roll))
        self.cam.location = pos
        self.cam.rotation_mode = "QUATERNION"
        self.cam.rotation_quaternion = q
        self.cam.data.lens = lens

    # ------------------------------------------------------------------ shot
    def actors_for(self, sh):
        a = dict(self.scene.SETS[sh["set"]])
        for n in sh.get("hide", []):
            a.pop(n, None)
        a.update({n: tuple(v) for n, v in sh.get("add", {}).items()})
        return a

    def apply(self, sh, t, actors):
        acts, faces = sh.get("acts", {}), sh.get("faces", {})
        gt = sh["frame0"] / 30 + t
        default_face = getattr(self.scene, "DEFAULT_FACE", {})
        for n in self.CAST:
            if n not in actors:
                self.ob[n + "_root"].location = (0, 0, -200)
                continue
            spec = actors[n]
            self.pose(n, spec, acts.get(n, spec[3]), t, faces.get(n, default_face.get(n, "neutral")), hash(n) % 17, sh)
            if self.counter:
                self.set_counter(n, counter_at(self.ckeys.get(n, []), gt), gt)
        if hasattr(self.scene, "apply"):
            self.scene.apply(self, sh, t, gt)
        bpy.context.view_layer.update()

    def choose_bias(self, sh, actors):
        if sh["cam"] in ("drone", "ots", "track", "chase", "sky", "pan", "orbit_room", "tilt_wall", "ecu_wall",
                         "shelf_pan", "ecu_hook", "hands", "counter") or sh["set"] in getattr(self.scene, "ROOMS", {}):
            return 0.0
        others = [n for n in actors if n != sh.get("tgt")]
        for bias in (0, 30, -30, 55, -55, 80, -80, 120, -120):
            ok = True
            for t in (0.0, sh["dur"] * 0.5, sh["dur"]):
                self.apply(sh, t, actors)
                pos, look, _, _ = self.cam_rig(sh, t, actors, bias)
                for n in others:
                    r = self.ob[n + "_root"].location
                    top = r.z + 2.5 * self.CAST[n]["scale"]
                    if Vector((pos.x - r.x, pos.y - r.y)).length < 0.85 and pos.z < top + 0.2:
                        ok = False
                    d = look - pos
                    L = d.length
                    if L > 0.1:
                        dn = d / L
                        c = Vector((r.x, r.y, min(max(pos.z, r.z + 0.3), top - 0.2)))
                        tt = (c - pos).dot(dn)
                        if 0.2 < tt < L - 0.5 and (pos + dn * tt - c).length < 0.45 and tt < 2.5:
                            ok = False
            if ok:
                return bias
        return 0.0

    def inside_cam(self, sh, actors, bias):
        """Characters the camera passes INSIDE during this shot (renders a black frame). Decided once per shot so
        nobody pops in or out mid-shot; such a character is left out of the whole shot."""
        key = (sh["id"], bias)
        cache = self.__dict__.setdefault("_inside", {})
        if key not in cache:
            out = set()
            for k in range(7):
                t = sh["dur"] * k / 6
                self.apply(sh, t, actors)
                pos = self.cam_rig(sh, t, actors, bias)[0]
                for n in actors:
                    if n == sh.get("tgt"):
                        continue
                    sc = self.CAST[n]["scale"]
                    r = self.ob[n + "_root"].location
                    if Vector((pos.x - r.x, pos.y - r.y)).length < 0.31 * sc + 0.08 and r.z < pos.z < r.z + 2.6 * sc:
                        out.add(n)
            cache[key] = out
        return cache[key]

    def frame(self, sh, t, actors, bias, path):
        gone = self.inside_cam(sh, actors, bias)
        self.apply(sh, t, actors)
        if gone:
            for n in gone:
                self.ob[n + "_root"].location = (0, 0, -200)
            bpy.context.view_layer.update()
        self.place_cam(*self.cam_rig(sh, t, actors, bias))
        self.sc.render.filepath = str(path)
        with render_slot():
            bpy.ops.render.render(write_still=True)

    def render_shot(self, sh, log):
        out = frames_dir(self.slug) / sh["id"]
        n_frames = math.ceil(sh["frames"] * RFPS / 30)
        done = out / ".done"
        sig = f"{n_frames}@{self.sc.render.resolution_x}x{self.sc.render.resolution_y}|{sh.get('sig', '')}"
        if done.exists() and done.read_text().strip() == sig:
            # trust the marker only if every frame is really there (a full disk / cleaner tool can lose files)
            if all(png_ok(out / f"f_{i:04d}.png") for i in range(n_frames)):
                return False
        out.mkdir(parents=True, exist_ok=True)
        self.lights_for(sh)
        actors = self.actors_for(sh)
        bias = self.choose_bias(sh, actors)
        t0 = time.time()
        for i in range(n_frames):
            p = out / f"f_{i:04d}.png"
            if png_ok(p):
                continue
            tmp = out / f"f_{i:04d}.tmp.png"
            for attempt in range(8):        # Windows can briefly lock a file (antivirus / indexer): wait and retry
                try:
                    if tmp.exists():
                        tmp.unlink()
                    self.frame(sh, i / RFPS, actors, bias, tmp)
                    os.replace(tmp, p)
                    break
                except (RuntimeError, OSError) as e:
                    if attempt == 7:
                        raise
                    print(f"  (write problem on {tmp.name}: {str(e)[:80]} - retry {attempt + 1}/7)", flush=True)
                    time.sleep(2 + 3 * attempt)
        done.write_text(sig)
        log(f"{self.slug} {sh['id']} {sh['set']}/{sh['cam']}/{sh['tgt']} {n_frames}f {time.time() - t0:.1f}s")
        return True


def main():
    a = args()
    slug = a[0]
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    res = a[a.index("--res") + 1] if "--res" in a else None
    logp = bdir(slug) / ("render_progress_preview.log" if preview() else "render_progress.log")

    def log(msg):
        line = time.strftime("%H:%M:%S ") + msg
        print(line, flush=True)
        with open(logp, "a") as f:
            f.write(line + "\n")

    shots = [s for s in json.loads((vdir(slug) / "shots.json").read_text())["shots"] if s["kind"] == "render"]
    if only:
        shots = [s for s in shots if s["id"] in only]
    st = Stage(slug, res)
    if "--smoke" in a:          # one tiny frame of EVERY shot: finds crashes before a long render
        fails = []
        outd = bdir(slug) / "smoke"
        outd.mkdir(exist_ok=True)
        for sh in shots:
            try:
                st.lights_for(sh)
                actors = st.actors_for(sh)
                bias = st.choose_bias(sh, actors)
                st.frame(sh, sh["dur"] * 0.5, actors, bias, outd / "s.png")
            except Exception as e:
                fails.append((sh["id"], repr(e)[:160]))
        print(f"SMOKE {slug}: {len(shots) - len(fails)}/{len(shots)} shots ok", flush=True)
        for f in fails[:12]:
            print("SMOKE FAIL", slug, *f, flush=True)
        return
    if "--still" in a:          # one test still per listed shot (frame at 60% of the shot)
        outd = Path(a[a.index("--still") + 1])
        outd.mkdir(parents=True, exist_ok=True)
        for sh in shots:
            st.lights_for(sh)
            actors = st.actors_for(sh)
            bias = st.choose_bias(sh, actors)
            st.frame(sh, sh["dur"] * 0.6, actors, bias, outd / f"{sh['id']}.png")
            print("still", outd / f"{sh['id']}.png", flush=True)
        return
    log(f"{slug}: {len(shots)} shots @ {RFPS}fps {st.sc.render.resolution_x}x{st.sc.render.resolution_y} "
        f"samples {st.sc.eevee.taa_render_samples} device {st.device}")
    n = 0
    for sh in shots:
        n += st.render_shot(sh, log)
    left = [s["id"] for s in shots if not (frames_dir(slug) / s["id"] / ".done").exists()]
    if not only and not left:
        progress.mark(slug, "rendered", ok=True, shots=len(shots))
    log(f"{slug}: finished ({n} newly rendered)")


if __name__ == "__main__":
    main()
