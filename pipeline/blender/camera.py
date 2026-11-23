"""Framing-driven cinematic camera system.

A shot's camera is described the way a DP talks ("85mm low-angle MCU on the hero,
push in"), not with coordinates.  camera spec keys:
    subject   : "hero" | "<char id>" | "monster" | "mark:<name>" | [x,y,z]
    subject2  : second subject (whip-pan destination, OTS / POV look target, rack focus)
    framing   : ecu | cu | mcu | ms | mws | ws | ews
    angle     : worm | low | eye | high | top
    az        : azimuth (deg) relative to subject facing; 0 = in front, 180 = behind
    move      : push_in | pull_out | orbit_left | orbit_right | crane_up | crane_down |
                tilt_up | tilt_down | whip_pan | dolly_left | dolly_right | drone_orbit |
                track | pov | ots | handheld | rack_focus | dolly_zoom | static_drift
    lens      : mm (24/35/50/85 ...)
    amount    : move strength multiplier (default 1)
    shake     : constant handheld amount 0..1 (impact shake is added automatically)
"""
import math
import random

import bpy
from mathutils import Vector

FRAME_H = {"ecu": 0.6, "cu": 1.2, "mcu": 1.7, "ms": 2.5, "mws": 4.0, "ws": 7.0, "ews": 30.0}
MON_FRAME_H = {"ecu": 0.12, "cu": 0.32, "mcu": 0.5, "ms": 0.75, "mws": 1.0, "ws": 1.4, "ews": 3.2}
ELEV = {"worm": -14, "low": -8, "eye": 4, "high": 32, "top": 68}


def _vfov(lens, sensor=36.0):
    return 2 * math.atan(sensor / 2 / lens)


class Subjects:
    """Resolves subject names to animated world points (evaluated per frame)."""

    def __init__(self, chars, monster, marks):
        self.chars, self.monster, self.marks = chars, monster, marks

    def point(self, name, part="head"):
        if isinstance(name, (list, tuple)):
            return Vector(name), 0.0, 2.0
        if name == "monster" and self.monster:
            m = self.monster
            hw = m.head.matrix_world.translation
            base = m.root.matrix_world.translation
            yaw = math.degrees(m.root.matrix_world.to_euler().z)
            if part == "base":
                return Vector((base.x, base.y, 0.5)), yaw, m.H
            if part == "chest":
                return base.lerp(hw, 0.6), yaw, m.H
            return hw + Vector((0, 0, 2 * m.u)), yaw, m.H
        if isinstance(name, str) and name.startswith("mark:"):
            return Vector(self.marks[name[5:]]) + Vector((0, 0, 1.5)), 0.0, 3.0
        c = self.chars.get(name) or (next(iter(self.chars.values())) if self.chars else None)
        if c is None:
            return Vector((0, 0, 1.6)), 0.0, 2.1
        hp = c.head.matrix_world.translation + Vector((0, 0, 0.3 * c.s))
        yaw = math.degrees(c.root.matrix_world.to_euler().z)
        if part == "base":
            return c.root.matrix_world.translation.copy(), yaw, 2.1 * c.s
        if part == "chest":
            return c.torso.matrix_world.translation + Vector((0, 0, 0.45 * c.s)), yaw, 2.1 * c.s
        return hp, yaw, 2.1 * c.s

    def is_monster(self, name):
        return name == "monster"


def _dir(az_world_deg, elev_deg):
    # front of a figure at yaw 0 is -Y, so azimuth 0 = camera on -Y side
    a = math.radians(az_world_deg - 90)
    e = math.radians(elev_deg)
    return Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))


def build_camera(spec, subj, f0, f1, impacts=(), fps=24, step=2):
    """Create the camera, key it over [f0,f1]. Returns camera object."""
    scn = bpy.context.scene
    cd = bpy.data.cameras.new("CAM")
    cam = bpy.data.objects.new("CAM", cd)
    scn.collection.objects.link(cam)
    scn.camera = cam
    tgt = bpy.data.objects.new("CAM_TGT", None)
    scn.collection.objects.link(tgt)
    tc = cam.constraints.new('TRACK_TO')
    tc.target = tgt
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'

    lens = float(spec.get("lens", 35))
    cd.lens = lens
    cd.sensor_fit = 'AUTO'
    cd.clip_start = 0.1
    cd.clip_end = 3000
    cd.dof.use_dof = True
    cd.dof.focus_object = tgt
    cd.dof.aperture_fstop = float(spec.get("fstop", 2.0 if lens >= 70 else 2.8))

    move = spec.get("move", "push_in")
    amt = float(spec.get("amount", 1.0))
    s1 = spec.get("subject", "hero")
    s2 = spec.get("subject2")
    framing = spec.get("framing", "ms")
    angle = spec.get("angle", "eye")
    az_rel = float(spec.get("az", 20))
    rng = random.Random(hash(str(spec)) & 0xffff)
    hand = float(spec.get("shake", 0.15))
    dur = max(1, f1 - f0)

    def ease(t):
        return t * t * (3 - 2 * t)

    def ease_out(t):
        return 1 - (1 - t) ** 3

    is_mon = subj.is_monster(s1)
    if move not in ("pov", "ots") and spec.get("auto_clear", True) and spec.get("pos") is None:
        az_rel = _clear_azimuth(spec, subj, s1, f0, az_rel, lens, framing, angle)
    roll_seed = rng.uniform(0, 100)
    keys = []
    for f in range(f0, f1 + 1, step):
        scn.frame_set(f)
        t = (f - f0) / dur
        te = ease(t)
        P, yaw, H = subj.point(s1, spec.get("part", "chest" if framing in ("ms", "mws", "ws") and not is_mon else "head"))
        fh = (MON_FRAME_H[framing] * H) if is_mon else FRAME_H[framing] * (H / 2.1)
        dist = fh * lens / 36.0
        az = yaw + az_rel
        elev = ELEV.get(angle, 4)
        target = P.copy()
        cam_pos = None
        if move == "push_in":
            dist *= 1.35 - 0.45 * amt * te
        elif move == "pull_out":
            dist *= 0.85 + 0.6 * amt * te
        elif move == "dolly_zoom":
            k = 1.5 - 0.6 * te
            dist *= k
            cd.lens = lens / k * 1.0
            cd.keyframe_insert("lens", frame=f)
        elif move in ("orbit_left", "orbit_right"):
            az += (-1 if move == "orbit_left" else 1) * 40 * amt * (te - 0.5)
        elif move == "drone_orbit":
            elev = max(elev, 30)
            dist *= 1.2
            az += 35 * amt * (te - 0.5)
        elif move in ("crane_up", "crane_down"):
            a, b = (ELEV["low"], 40) if move == "crane_up" else (45, ELEV["eye"])
            elev = a + (b - a) * te * amt
            dist *= 1.0 + 0.25 * te
        elif move in ("tilt_up", "tilt_down"):
            Pb, _, _ = subj.point(s1, "base")
            lo, hi = (Pb, P) if move == "tilt_up" else (P, Pb)
            target = lo.lerp(hi, ease_out(t) if move == "tilt_up" else te)
            Pc = Pb.lerp(P, 0.5)
            d = _dir(az, ELEV["worm"] if angle in ("low", "worm") else elev)
            cam_pos = Pc + d * dist * 1.05
            cam_pos.z = max(0.4, Pb.z + (0.6 if is_mon else 0.3))
        elif move in ("dolly_left", "dolly_right", "track"):
            side = -1 if move == "dolly_left" else 1
            if move == "track":
                side = 0
            perp = _dir(az + 90, 0)
            dist *= 1.05
            offset = perp * side * fh * 0.9 * amt * (te - 0.5)
            cam_pos = P + _dir(az, elev) * dist + offset
        elif move == "whip_pan" and s2 is not None:
            P2, _, H2 = subj.point(s2, "chest" if not subj.is_monster(s2) else "head")
            w = float(spec.get("whip_at", 0.45))
            k = min(1.0, max(0.0, (t - w) / 0.12))
            k = ease(k)
            target = P.lerp(P2, k)
            if f == f0:
                anchor = P + _dir(az, elev) * dist
                build_camera._anchor = anchor
            cam_pos = build_camera._anchor
        elif move == "pov" and s2 is not None:
            P2, _, _ = subj.point(s2)
            fwd = (P2 - P).normalized()
            cam_pos = P + fwd * 1.6 * (H / 2.1) + Vector((0, 0, -0.1))
            target = P2
            hand = max(hand, 0.35)
        elif move == "ots" and s2 is not None:
            P2, _, H2 = subj.point(s2, "head")
            back = (P - P2).normalized()
            right = back.cross(Vector((0, 0, 1))).normalized()
            cam_pos = P + back * (1.6 + 0.4 * te) * (H / 2.1) + right * 0.7 * (H / 2.1) + Vector((0, 0, 0.15))
            if subj.is_monster(s2):
                cam_pos.z = P.z - 0.4
            target = P2.lerp(P2 + (P - P2) * 0.05, te)
        elif move == "rack_focus" and s2 is not None:
            P2, _, _ = subj.point(s2)
            dist *= 1.1
            # focus moves from subject2 (bg/fg) to subject; framing on subject
        elif move == "static_drift" or move == "handheld":
            dist *= 1.0 + 0.04 * te
        if cam_pos is None:
            cam_pos = P + _dir(az, elev) * dist
            if angle in ("worm", "low"):
                floor_z = subj.point(s1, "base")[0].z
                cam_pos.z = max(floor_z + (0.25 if angle == "worm" else 0.7) * (H / 2.1 if not is_mon else 2.0),
                                min(cam_pos.z, P.z - 0.1))
        if spec.get("pos") is not None:  # authored camera position (optionally travelling to pos2)
            a_ = Vector(spec["pos"]); b_ = Vector(spec.get("pos2", spec["pos"]))
            cam_pos = a_.lerp(b_, te)
        if spec.get("min_z") is not None:
            cam_pos.z = max(cam_pos.z, float(spec["min_z"]))
        if spec.get("height") is not None:
            cam_pos.z = float(spec["height"])
        # handheld drift
        hx = math.sin(f * 0.21 + roll_seed) * 0.6 + math.sin(f * 0.53 + roll_seed * 2) * 0.4
        hy = math.cos(f * 0.17 + roll_seed) * 0.6 + math.sin(f * 0.47) * 0.4
        sc = hand * 0.04 * dist ** 0.5
        cam_pos += Vector((hx * sc, hy * sc, hx * hy * sc))
        target += Vector((hy * sc * 0.6, hx * sc * 0.6, 0))
        # impact shake (decaying, distance-scaled)
        for (fi, loc, power) in impacts:
            if fi - 1 <= f < fi + 16:
                dd = (Vector(loc) - cam_pos).length
                amp = power * max(0.2, min(1.0, 80.0 / (dd + 20))) * math.exp(-max(0, f - fi) / 4.0)
                j = random.Random(f * 7 + fi)
                aim = (target - cam_pos).length
                v = Vector((j.uniform(-1, 1), j.uniform(-1, 1), j.uniform(-1, 1)))
                target += v * aim * 0.012 * amp
                cam_pos += v * 0.04 * amp
        cam.location = cam_pos
        cam.keyframe_insert("location", frame=f)
        tgt.location = target
        tgt.keyframe_insert("location", frame=f)
        keys.append((f, tuple(cam_pos), tuple(target)))
        if move == "rack_focus" and s2 is not None:
            P2, _, _ = subj.point(s2)
            fd = ((P2.lerp(P, ease(min(1, max(0, (t - 0.35) / 0.3))))) - cam_pos).length
            cd.dof.focus_object = None
            cd.dof.focus_distance = fd
            cd.dof.keyframe_insert("focus_distance", frame=f)
    # slight dutch on handheld/pov/panic
    if spec.get("dutch"):
        tc.up_axis = 'UP_Y'
        cam.rotation_euler = (0, 0, 0)
    return cam, keys


def _blocked(scn, origin, target, subject_colls):
    dg = bpy.context.evaluated_depsgraph_get()
    d = target - origin
    dist = d.length
    if dist < 0.5:
        return False
    for o, v in ((origin, d), (target, -d)):  # both directions: also catches a camera inside a mesh
        hit, loc, nrm, idx, ob, mtx = scn.ray_cast(dg, o, v.normalized(), distance=dist - 0.3)
        if hit and ob is not None:
            names = {c.name for c in ob.users_collection}
            if not (names & subject_colls) and "fx" not in names and "lights" not in names:
                if v is d or (loc - target).length > 1.0:
                    return True
    return False


def _clear_azimuth(spec, subj, s1, f0, az_rel, lens, framing, angle):
    """Swing the camera around the subject until nothing (buildings, props) sits between
    lens and subject; prefer the authored angle, then small swings, then the reverse."""
    scn = bpy.context.scene
    scn.frame_set(f0)
    is_mon = subj.is_monster(s1)
    P, yaw, H = subj.point(s1, "chest" if is_mon else "head")
    fh = (MON_FRAME_H[framing] * H) if is_mon else FRAME_H[framing] * (H / 2.1)
    dist = fh * lens / 36.0
    if spec.get("move") == "push_in":
        dist *= 1.35
    colls = {"monster"} if is_mon else {"chars"}
    elev = ELEV.get(angle, 4)
    for da in (0, 15, -15, 30, -30, 50, -50, 180, 160, 200, 80, -80):
        a = az_rel + da
        cp = P + _dir(yaw + a, elev) * dist
        if spec.get("height") is not None:
            cp.z = float(spec["height"])
        if angle in ("low", "worm"):
            cp.z = max(0.4, min(cp.z, P.z - 0.1))
        if not _blocked(scn, cp, P, colls):
            if da:
                print(f"[camera] az {az_rel:.0f} blocked -> {a:.0f}", flush=True)
            return a
    return az_rel
