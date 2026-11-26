"""Render every 3D shot of shots.json with Eevee (headless). Resume-safe, logs progress.

usage: python3 render_shots.py [worker_index worker_count] [--only shot_001,shot_002]
env:   MM_RENDER_FPS (default 30), MM_RES (default 1080x1920)
"""
import bpy, json, math, os, sys, time
from mathutils import Vector, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scene_lib import CAST, SETS, INTERIOR_SETS, NIGHT_SETS, PROPS, HATS, HELD, DOBBS_HOUSE

RFPS = int(os.environ.get("MM_RENDER_FPS", "30"))
RES = os.environ.get("MM_RES", "1080x1920")
FR = os.path.join(HERE, "build", "frames")
LOG = os.path.join(HERE, "build", "render_progress.log")
FACES = os.path.join(HERE, "build", "faces")
EXPR = ("neutral", "scared", "tired", "shocked", "blank", "talk")
DX, DY = DOBBS_HOUSE
DOBBS_ROOM = (DX - 2.75, DX + 2.75, DY - 2.75, DY + 2.75)


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c] + [1]


MOODS = {
    #           elev az   strength sun_col    horizon    mid        top        bg_strength
    "day":      (52, 220, 3.6, "#fff2dc", "#e6dcc4", "#c9d3d6", "#8fa9bf", 1.0),
    "golden":   (28, 250, 3.2, "#ffd9a8", "#efcf9e", "#c9c3b4", "#8e9fb2", 1.1),
    "dusk":     (15, 235, 2.4, "#ffb68a", "#e3a27c", "#a08f94", "#4f5a76", 1.25),
    "night":    (40, 150, 1.7, "#a8bcf0", "#55658f", "#3a4670", "#1c2442", 3.2),
    "interior": (68, 230, 1.5, "#ffe2bc", "#d9a685", "#8f8592", "#4a5370", 0.7),
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


class Stage:
    def __init__(self):
        bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "build", "town.blend"))
        self.sc = bpy.context.scene
        w, h = RES.split("x")
        self.sc.render.resolution_x, self.sc.render.resolution_y = int(w), int(h)
        self.cam = bpy.data.objects["cam"]
        self.sun = bpy.data.objects["sun"]
        self.ramp = self.sc.world.node_tree.nodes["SKYRAMP"]
        self.bg = self.sc.world.node_tree.nodes["SKYBG"]
        self.ob = bpy.data.objects
        self.imgs = {(n, e): bpy.data.images.load(os.path.join(FACES, f"{n}_{e}.png"), check_existing=True)
                     for n in CAST for e in EXPR}
        self.face_node = {n: self.ob[n + "_face"].active_material.node_tree.nodes["FACE"] for n in CAST}
        self.cur_face = {}
        ee = self.sc.eevee
        ee.use_fast_gi = False
        ee.shadow_resolution_scale = 0.5
        self.sc.render.use_persistent_data = True

    def mood(self, m):
        el, az, st, sc, hz, mid, top, bgs = MOODS[m]
        self.sun.rotation_euler = Euler((math.radians(90 - el), 0, math.radians(az)), "XYZ")
        self.sun.data.energy = st
        self.sun.data.color = lin(sc)[:3]
        els = sorted(self.ramp.color_ramp.elements, key=lambda e: e.position)
        els[0].color, els[1].color, els[2].color = lin(hz), lin(mid), lin(top)
        self.bg.inputs["Strength"].default_value = bgs

    def set_face(self, n, e):
        if self.cur_face.get(n) != e:
            self.face_node[n].image = self.imgs[(n, e)]
            self.cur_face[n] = e

    # ------------------------------------------------------------------ actors
    def pose(self, n, spec, act, t, face, seed, sh):
        x, y, rot, _, z = spec
        s = CAST[n]["scale"]
        root = self.ob[n + "_root"]
        legL, legR = self.ob[n + "_legL"], self.ob[n + "_legR"]
        armL, armR = self.ob[n + "_armL"], self.ob[n + "_armR"]
        head = self.ob[n + "_head"]
        for o in (legL, legR, armL, armR, head):
            o.rotation_euler = (0, 0, 0)
        root.rotation_euler = (0, 0, 0)
        if n == "eli" and sh.get("eli_turned"):
            rot = rot + 180
        if act == "turn":
            rot = rot + 180 * smooth((t - 0.15) / 0.55)
        f = fdir(rot)
        pos = Vector((x, y, z))
        ph = seed * 0.37
        fc = face
        held = False
        if act in ("walk", "walk_down", "run", "sneak"):
            speed, freq, amp = {"walk": (1.35, 1.7, 0.55), "walk_down": (1.5, 1.8, 0.45), "run": (3.8, 2.8, 0.9),
                                "sneak": (0.7, 1.1, 0.35)}[act]
            pos += f * speed * t
            sw = math.sin(2 * math.pi * freq * t + ph)
            legL.rotation_euler.x, legR.rotation_euler.x = amp * sw, -amp * sw
            armL.rotation_euler.x, armR.rotation_euler.x = -amp * 0.9 * sw, amp * 0.9 * sw
            pos.z += 0.05 * abs(math.sin(2 * math.pi * freq * t + ph))
            if act == "walk_down":
                head.rotation_euler.x = -0.4
            if act == "run":
                head.rotation_euler.z = 0.25 * math.sin(2.1 * t)   # glancing back
            if act == "sneak":
                pos.z -= 0.12
                armL.rotation_euler.x = armR.rotation_euler.x = 0.5
                head.rotation_euler.z = 0.35 * math.sin(1.4 * t + ph)
        elif act == "sit":
            pos.z = 0.56 - 0.9 * s
            legL.rotation_euler.x = legR.rotation_euler.x = 1.57
            armL.rotation_euler.x = armR.rotation_euler.x = 1.0
            head.rotation_euler.x = 0.03 * math.sin(0.8 * t)
        else:
            armL.rotation_euler.x = 0.04 * math.sin(1.3 * t + ph)
            armR.rotation_euler.x = -0.04 * math.sin(1.3 * t + ph)
            head.rotation_euler.z = 0.08 * math.sin(0.6 * t + ph)
            pos.z += 0.01 * math.sin(2.0 * t + ph)
        if act == "look_down":
            head.rotation_euler.x = -0.5
        if act in ("talk", "whisper", "laugh"):
            amp = 0.15 if act == "whisper" else 0.3
            armR.rotation_euler.x = 0.55 + amp * math.sin(4.2 * t + ph)
            armR.rotation_euler.y = 0.15
            head.rotation_euler.x = (0.18 if act == "laugh" else 0.06) * math.sin((9 if act == "laugh" else 5) * t)
            if face in ("neutral", "talk") or act == "laugh":
                fc = "talk" if int(t * 7 + seed) % 2 == 0 else ("neutral" if act != "laugh" else "talk")
            if act == "whisper":
                fc = "talk" if int(t * 5) % 2 == 0 else face
        if act == "point":
            armR.rotation_euler.x = 1.6
        if act in ("read", "hold", "give"):
            held = True
            armR.rotation_euler.x = {"read": 1.25, "hold": 0.75, "give": 1.45}[act]
            if act == "read":
                armL.rotation_euler.x = 1.1
                head.rotation_euler.x = -0.18
        if act == "shake":
            armL.rotation_euler.x = armR.rotation_euler.x = 0.9 + 0.06 * math.sin(41 * t)
            armL.rotation_euler.y = 0.05 * math.sin(37 * t)
        if act == "peek":
            pos.z += 0.04 * math.sin(1.2 * t)
            armL.rotation_euler.x = armR.rotation_euler.x = 1.25
            armL.rotation_euler.z, armR.rotation_euler.z = -0.25, 0.25
            head.rotation_euler.z = 0.25 * math.sin(0.9 * t)
        if act == "stagger":
            u = smooth(t / 0.5)
            root.rotation_euler.x = -0.35 * u
            armL.rotation_euler.y, armR.rotation_euler.y = -1.2 * u, 1.2 * u
        if act == "look_mailbox":
            head.rotation_euler.z = 0.75 * smooth(t / 0.6)
            head.rotation_euler.x = -0.15
        if act == "look_house":
            head.rotation_euler.z = 0.9 * smooth(t / 0.5)
        root.location = pos
        root.rotation_euler.z = math.radians(rot - 90)
        self.set_face(n, fc)
        if n in HELD:
            self.ob[n + "_env"].hide_render = not held
            for zs in (1, -1):
                self.ob[f"{n}_env_text{zs}"].hide_render = not held
        if n == "dobbs":
            self.ob["dobbs_cap"].location.z = 0.49 if sh.get("capdown") else 0.72
            self.ob["dobbs_cap"].rotation_euler.x = 0.0
        return pos

    # ------------------------------------------------------------------ targets
    def head_pos(self, n):
        return self.ob[n + "_head"].matrix_world @ Vector((0, 0, 0.33))

    def target(self, tgt, actors):
        if tgt in actors:
            return self.head_pos(tgt), fdir(self.facing(tgt, actors)), CAST[tgt]["scale"], True
        if tgt.startswith("pt:"):
            x, y, z = map(float, tgt[3:].split(","))
            return Vector((x, y, z)), fdir(-90), 1.0, False
        if tgt.endswith("_env"):
            holder = tgt[:-4]
            p = self.ob[tgt].matrix_world.translation.copy()
            return p, fdir(self.facing(holder, actors)), 0.45, False
        x, y, z, fd = PROPS[tgt]
        return Vector((x, y, z)), fdir(fd), 1.0, False

    def facing(self, n, actors):
        return math.degrees(self.ob[n + "_root"].rotation_euler.z) + 90

    def hand_pos(self, n):
        return self.ob[n + "_armR"].matrix_world @ Vector((0, 0, -0.75))

    # ------------------------------------------------------------------ camera
    def cam_rig(self, sh, t, actors, ang_bias):
        cam = sh["cam"]
        dur = sh["dur"]
        u = smooth(t / max(dur, 0.01))
        T, f, k, is_actor = self.target(sh["tgt"], actors)
        side = Vector((-f.y, f.x, 0))
        interior = sh["set"] in INTERIOR_SETS
        im = 0.45 if interior else 1.0
        lens, roll = 35, 0.0
        look = T.copy()
        ground = 0.0
        if is_actor:
            ground = self.ob[sh["tgt"] + "_root"].location.z if actors[sh["tgt"]][3] != "sit" else 0.0

        def around(d, ang, dz):
            if sh["tgt"] == "eli_house":
                ang = 2
            return T + rot2(f, ang + ang_bias) * d + Vector((0, 0, dz))

        hat = is_actor and sh["tgt"] in HATS
        if cam == "ecu":
            pos = around(lerp(2.05, 1.6, u) * k * (1.5 if hat else 1.0), 8, 0.22 if hat else 0.06); lens = 40
            look = T + Vector((0, 0, (0.38 if hat else 0.07) * k))
            if not is_actor:
                pos = around(lerp(1.15, 0.9, u), 15, 0.12); lens = 40
        elif cam == "cu":
            pos = around(lerp(2.5, 2.0, u) * k * (1.3 if hat else 1.0), 22, 0.15); lens = 40
            look = T + Vector((0, 0, (0.3 if hat else 0.0) * k))
        elif cam in ("push", "pull"):
            a, b = (7.5, 3.6) if cam == "push" else (3.4, 7.8)
            if not is_actor:
                a, b = a * 1.3, b * 1.3
            if sh["tgt"] in ("eli_house", "post_office", "dobbs_house", "mill"):
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
            d2 = (T - O); d2.z = 0; d2.normalize()
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
        elif cam == "chase":   # behind the subject, slightly high, looking down the road ahead of him
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
            pos = T + Vector((math.cos(a) * 48, math.sin(a) * 48, 32 - 4 * u)); lens = 28
        elif cam == "prop":
            pos = around(lerp(2.4, 1.6, u) * (0.55 if T.z < 1.5 and not interior else 1.0), 18, 0.6); lens = 40
            if sh["tgt"] in ("eli_house", "bakery_sign", "mill", "hall_sign", "post_office", "dobbs_house", "barn"):
                pos = around(lerp(12, 9, u), 15, 0.5)
            if sh["tgt"].endswith("_env"):
                pos = around(lerp(1.7, 1.35, u), 20, 0.3)
        elif cam == "sky":
            pos = T + f * 2.4 + Vector((0, 0, -1.5)); lens = 24
            look = lerp(T, T + Vector((0, 0, 9)) - f * 3, u)
        elif cam == "pan":           # sweep along a wall of envelopes
            pos = T + f * 2.1 + Vector((0, 0, -0.1)); lens = 28
            look = T + side * lerp(-1.6, 1.6, u)
        elif cam == "orbit_room":    # spin in the middle of the room, walls of envelopes all around
            a = math.radians(lerp(-30, 70, u) + 40)
            pos = T + Vector((0.3, -0.3, 0)); lens = 22
            look = pos + Vector((math.cos(a) * 3, math.sin(a) * 3, 0.35))
        elif cam == "tilt_wall":     # floor to ceiling
            pos = T + f * 1.9 + Vector((0, 0, -0.4)); lens = 24
            look = T + Vector((0, 0, lerp(-1.4, 1.1, u)))
        elif cam == "ecu_wall":      # nose against the envelopes, drifting sideways
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
            fa = fdir(self.facing(n, actors))
            pos = H + rot2(fa, 30) * lerp(1.7, 1.4, u) + Vector((0, 0, 0.35)); lens = 35
            look = H + Vector((0, 0, 0.12))
        else:
            pos = around(3.0, 20, 0.2)
        # keep interior cameras inside the blue house's walls
        if sh["set"] in ("int", "int_door", "int_talk", "int_final"):
            x0, x1, y0, y1 = DOBBS_ROOM
            pos.x = min(max(pos.x, x0 + 0.05), x1 - 0.05)
            pos.y = min(max(pos.y, y0 + 0.05), y1 - 0.05)
            pos.z = min(max(pos.z, 0.3), 3.05)
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
        a = dict(SETS[sh["set"]])
        if sh.get("nodobbs"):
            a.pop("dobbs", None)
        for n in sh.get("hide", []):
            a.pop(n, None)
        return a

    def apply(self, sh, t, actors):
        acts, faces = sh.get("acts", {}), sh.get("faces", {})
        for n in CAST:
            if n not in actors:
                self.ob[n + "_root"].location = (0, 0, -200)
                continue
            spec = actors[n]
            self.pose(n, spec, acts.get(n, spec[3]), t, faces.get(n, "blank" if n == "eli2" else "neutral"), hash(n) % 17, sh)
        hinge = self.ob["dh_door_hinge"]
        if sh.get("door") == "opening":
            hinge.rotation_euler.z = math.radians(-100) * smooth(t / (sh["dur"] * 0.85))
        elif sh.get("door") == "open":
            hinge.rotation_euler.z = math.radians(-100)
        else:
            hinge.rotation_euler.z = 0
        gt = sh["frame0"] / 30 + t
        self.ob["mill_hub"].rotation_euler.y = 0.55 * gt
        fire = bool(sh.get("fire"))
        self.ob["barn_fire"].hide_render = not fire
        self.ob["barn_smoke"].hide_render = not fire
        if fire:
            self.ob["barn_fire"].scale.z = 1 + 0.12 * math.sin(23 * t)
            self.ob["barn_smoke"].location.z = 0.6 * t
        bpy.context.view_layer.update()

    def lights_for(self, sh):
        light = sh.get("light", "day")
        if sh["set"] == "kitchen":
            light = "interior" if light != "dusk" else "dusk"
        self.mood(light)
        self.ob["kitchen_lamp"].hide_render = sh["set"] != "kitchen"
        self.ob["dobbs_lamp"].hide_render = sh["set"] not in NIGHT_SETS

    def choose_bias(self, sh, actors):
        if sh["cam"] in ("drone", "ots", "track", "chase", "sky", "pan", "orbit_room", "tilt_wall", "ecu_wall",
                         "shelf_pan", "ecu_hook", "hands") or sh["set"] in ("int", "int_door", "int_talk", "int_final"):
            return 0.0
        others = [n for n in actors if n != sh.get("tgt")]
        for bias in (0, 30, -30, 55, -55, 80, -80, 120, -120):
            ok = True
            for t in (0.0, sh["dur"] * 0.5, sh["dur"]):
                self.apply(sh, t, actors)
                pos, look, _, _ = self.cam_rig(sh, t, actors, bias)
                for n in others:
                    r = self.ob[n + "_root"].location
                    top = r.z + 2.5 * CAST[n]["scale"]
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

    def render_shot(self, sh):
        out = os.path.join(FR, sh["id"])
        n_frames = math.ceil(sh["frames"] * RFPS / 30)
        done = os.path.join(out, ".done")
        sig = f"{n_frames}@{RES}"
        if os.path.exists(done) and open(done).read().strip() == sig:
            return False
        os.makedirs(out, exist_ok=True)
        self.lights_for(sh)
        actors = self.actors_for(sh)
        bias = self.choose_bias(sh, actors)
        t0 = time.time()
        for i in range(n_frames):
            p = os.path.join(out, f"f_{i:04d}.png")
            if os.path.exists(p) and os.path.getsize(p) > 0:
                continue
            t = i / RFPS
            self.apply(sh, t, actors)
            self.place_cam(*self.cam_rig(sh, t, actors, bias))
            self.sc.render.filepath = p + ".tmp.png"
            bpy.ops.render.render(write_still=True)
            os.replace(p + ".tmp.png", p)
        open(done, "w").write(sig)
        log(f"{sh['id']} {sh['set']}/{sh['cam']}/{sh['tgt']} {n_frames}f {time.time() - t0:.1f}s")
        return True


def main():
    args = list(sys.argv[1:])
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = set(args[i + 1].split(","))
        args = args[:i] + args[i + 2:]
    wi, wn = (int(args[0]), int(args[1])) if len(args) >= 2 else (0, 1)
    shots = [s for s in json.load(open(os.path.join(HERE, "shots.json")))["shots"] if s["kind"] == "render"]
    shots = [s for k, s in enumerate(shots) if k % wn == wi and (only is None or s["id"] in only)]
    st = Stage()
    log(f"worker {wi}/{wn}: {len(shots)} shots @ {RFPS}fps {RES}")
    for sh in shots:
        st.render_shot(sh)
    log(f"worker {wi}/{wn} finished")


if __name__ == "__main__":
    main()
