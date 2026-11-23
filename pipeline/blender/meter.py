"""Kindness-meter billboards: a glowing 3D number above every head.

Meter(anchor, events) builds a pool of extruded text objects (one per displayed string)
whose scale/emission are keyed per frame, all held in a holder that copies the camera's
rotation so the number always faces the lens.
    events: [frame, value | "0" | "inf", kind]   kind in set | tick | flicker | fall_red
  * tick   : old value pops out, new value pops in with overshoot + emission flash and a
             floating '+1' that rises and fades.
  * flicker: rapid visibility/emission noise with glitched strings (abandonment).
  * fall_red: value glitches red and counts down while sinking.
HeroZero: a segmented red '0' (menacing pulse) that can glitch to a gold infinity for
exactly N frames (the clue) and perform the hero flip (crack -> glow burst -> shards fly
-> gold infinity grows with overshoot while spinning 180 degrees -> spark shower).
"""
import math
import os
import random

import bpy
import bmesh
from mathutils import Vector, Matrix

import kit as K

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_PATH = os.path.join(ROOT, "assets", "fonts", "Inter-Black.otf")

COL = {"white": (0.72, 0.9, 1.0), "gold": (1.0, 0.62, 0.08), "red": (1.0, 0.025, 0.012),
       "grey": (0.7, 0.72, 0.75), "green": (0.4, 1.0, 0.55)}


def _font():
    f = bpy.data.fonts.get("InterBlack")
    if f is None:
        f = bpy.data.fonts.load(FONT_PATH) if os.path.exists(FONT_PATH) else bpy.data.fonts[0]
        f.name = "InterBlack"
    return f


def fmt(v):
    if isinstance(v, str):
        return v
    return f"{int(v):,}"


def _glow_mat(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "Emission"
    em.inputs[0].default_value = (*color, 1)
    em.inputs[1].default_value = strength
    # thin dark core edge so digits read against bright skies
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*[c * 0.3 for c in color], 1)
    mix = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(em.outputs[0], mix.inputs[0])
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(mix.outputs[0], out.inputs[0])
    return m


def text_obj(name, body, size, mat, parent=None, extrude=0.05):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    cu.font = _font()
    cu.size = size
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.extrude = extrude * size
    cu.bevel_depth = 0.012 * size
    cu.bevel_resolution = 1
    cu.resolution_u = 6
    o = bpy.data.objects.new(name, cu)
    K.coll("meters").objects.link(o)
    o.data.materials.append(mat)
    o.rotation_euler = (math.radians(90), 0, 0)   # stand up, facing -Y
    if parent:
        o.parent = parent
    return o


def _key_scale(o, frame, s):
    o.scale = (s, s, s)
    o.keyframe_insert("scale", frame=frame)


def _key_em(mat, frame, v):
    em = mat.node_tree.nodes["Emission"].inputs[1]
    em.default_value = v
    em.keyframe_insert("default_value", frame=frame)


class Meter:
    """Number above a character. anchor: object to follow (char.meter_anchor)."""

    def __init__(self, name, anchor, events, size=0.42, color="white", strength=7.0, f_range=(-10, 400), seed=0):
        self.name, self.anchor = name, anchor
        self.size, self.color, self.strength = size, color, strength
        self.events = sorted(events, key=lambda e: e[0])
        self.fa, self.fb = f_range
        self.rng = random.Random(seed)
        self.holder = K.empty(f"{name}_mholder", (0, 0, 0), None, "meters")
        cl = self.holder.constraints.new('COPY_LOCATION')
        cl.target = anchor
        self.pivot = K.empty(f"{name}_mpivot", (0, 0, 0), self.holder, "meters")
        self.pivot.rotation_euler = (math.radians(-90), 0, 0)
        self.pool = {}
        self.objs = []

    def _get(self, body, color):
        k = (body, color)
        if k not in self.pool:
            m = _glow_mat(f"{self.name}_m{len(self.pool)}", COL.get(color, color), self.strength)
            o = text_obj(f"{self.name}_n{len(self.pool)}", body, self.size, m, self.pivot)
            o.scale = (0.0001,) * 3
            o.keyframe_insert("scale", frame=self.fa)
            self.pool[k] = (o, m)
        return self.pool[k]

    def build(self, cam):
        cr = self.holder.constraints.new('COPY_ROTATION')
        cr.target = cam
        ev = self.events
        if not ev:
            return
        cur = None
        for i, (f, val, kind) in enumerate(ev):
            color = self.color if kind != "fall_red" else "red"
            body = fmt(val)
            if kind == "set" and cur is None:
                o, m = self._get(body, color)
                _key_scale(o, self.fa, 1.0)
                cur = (o, m, body)
                continue
            if kind in ("set", "tick", "fall_red"):
                o, m = self._get(body, color)
                if cur is not None and cur[0] is not o:
                    po = cur[0]
                    _key_scale(po, f - 1, 1.0)
                    _key_scale(po, f + 1, 0.0001)
                if kind == "tick":
                    _key_scale(o, f - 1, 0.0001)
                    _key_scale(o, f + 1, 1.45)
                    _key_scale(o, f + 4, 0.9)
                    _key_scale(o, f + 7, 1.0)
                    _key_em(m, f - 1, self.strength)
                    _key_em(m, f + 1, self.strength * 4)
                    _key_em(m, f + 8, self.strength)
                    self._plus_one(f)
                elif kind == "fall_red":
                    _key_scale(o, f - 1, 0.0001)
                    _key_scale(o, f, 1.15)
                    _key_scale(o, f + 2, 1.0)
                    # sink as it drains
                    o.location = (0, 0, 0)
                    o.keyframe_insert("location", frame=f)
                    o.location = (0, 0, -0.08)
                    o.keyframe_insert("location", frame=f + 6)
                else:
                    _key_scale(o, f - 1, 0.0001)
                    _key_scale(o, f, 1.0)
                cur = (o, m, body)
            elif kind == "flicker":
                f1 = int(val)
                if cur is None:
                    continue
                o, m, body = cur
                glitches = [self._glitch(body) for _ in range(3)]
                gobjs = [self._get(g, self.color) for g in glitches]
                for fr in range(f, f1):
                    r = self.rng.random()
                    vis = r > 0.35
                    gsel = self.rng.randrange(3) if r < 0.18 else None
                    _key_scale(o, fr, 1.0 if vis and gsel is None else 0.0001)
                    _key_em(m, fr, self.strength * self.rng.uniform(0.2, 1.6))
                    for k, (go, gm) in enumerate(gobjs):
                        _key_scale(go, fr, 1.0 if gsel == k else 0.0001)
                _key_scale(o, f1, 1.0)
                _key_em(m, f1, self.strength)
                for go, gm in gobjs:
                    _key_scale(go, f1, 0.0001)
            elif kind == "hide":
                if cur:
                    _key_scale(cur[0], f - 1, 1.0)
                    _key_scale(cur[0], f, 0.0001)
        for o, m in self.pool.values():
            for fc in K._fcurves(o):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'BEZIER'

    def _glitch(self, body):
        chars = list(body)
        for _ in range(2):
            i = self.rng.randrange(len(chars))
            if chars[i].isdigit():
                chars[i] = self.rng.choice("#?7_0/")
        return "".join(chars)

    def _plus_one(self, f):
        m = _glow_mat(f"{self.name}_p1_{f}", COL["green"], self.strength * 1.3)
        o = text_obj(f"{self.name}_plus{f}", "+1", self.size * 0.7, m, self.pivot)
        o.location = (self.size * 1.6, 0, 0.1)
        _key_scale(o, f - 1, 0.0001)
        _key_scale(o, f + 1, 1.2)
        _key_scale(o, f + 4, 1.0)
        o.keyframe_insert("location", frame=f)
        o.location = (self.size * 1.9, 0, 0.75)
        o.keyframe_insert("location", frame=f + 16)
        _key_scale(o, f + 12, 1.0)
        _key_scale(o, f + 17, 0.0001)


# ------------------------------------------------------------------ hero zero / infinity
def _ring_segments(n=30, rx=0.26, rz=0.36, thick=0.11, depth=0.09):
    """Elliptical bold '0' as n separate wedge meshes (for cracking)."""
    segs = []
    for i in range(n):
        a0 = i / n * math.tau
        a1 = (i + 1) / n * math.tau
        me = bpy.data.meshes.new(f"zseg{i}")
        bm = bmesh.new()
        vs = []
        for a in (a0, a1):
            for r in (0.0, 1.0):
                for y in (-depth / 2, depth / 2):
                    ox = (rx - thick * r) * math.sin(a)
                    oz = (rz - thick * r) * math.cos(a)
                    vs.append(bm.verts.new((ox, y, oz)))
        q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for f in q:
            try:
                bm.faces.new([vs[k] for k in f])
            except ValueError:
                pass
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        c = Vector(((rx - thick / 2) * math.sin((a0 + a1) / 2), 0, (rz - thick / 2) * math.cos((a0 + a1) / 2)))
        segs.append((me, c))
    return segs


def _lemniscate_obj(name, mat, scale=0.36, tube=0.055):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('POLY')
    N = 96
    sp.points.add(N - 1)
    for i in range(N):
        t = i / N * math.tau
        d = 1 + math.sin(t) ** 2
        x = scale * 1.25 * math.cos(t) / d
        z = scale * 1.25 * math.sin(t) * math.cos(t) / d
        sp.points[i].co = (x, 0, z, 1)
    sp.use_cyclic_u = True
    cu.bevel_depth = tube
    cu.bevel_resolution = 4
    o = bpy.data.objects.new(name, cu)
    K.coll("meters").objects.link(o)
    o.data.materials.append(mat)
    return o


class HeroZero:
    """The hero's red 0 + hidden gold infinity."""

    def __init__(self, name, anchor, f_range=(-10, 400), size=1.0, seed=3):
        self.name = name
        self.fa, self.fb = f_range
        self.rng = random.Random(seed)
        self.holder = K.empty(f"{name}_zholder", (0, 0, 0), None, "meters")
        cl = self.holder.constraints.new('COPY_LOCATION')
        cl.target = anchor
        self.holder.scale = (size,) * 3
        self.pivot = K.empty(f"{name}_zpivot", (0, 0, 0), self.holder, "meters")
        self.pivot.rotation_euler = (math.radians(-90), 0, 0)
        self.red = _glow_mat(f"{name}_red", COL["red"], 4.0)
        self.gold = _glow_mat(f"{name}_gold", COL["gold"], 6.0)
        self.zero = K.empty(f"{name}_zero", (0, 0, 0), self.pivot, "meters")
        self.segs = []
        for i, (me, c) in enumerate(_ring_segments()):
            o = bpy.data.objects.new(f"{name}_seg{i}", me)
            K.coll("meters").objects.link(o)
            me.materials.append(self.red)
            o.parent = self.zero
            self.segs.append((o, c))
        self.inf = _lemniscate_obj(f"{name}_inf", self.gold)
        self.inf.parent = self.pivot
        self.inf.scale = (0.0001,) * 3
        self.inf.keyframe_insert("scale", frame=self.fa)
        # inner glow light that sells the pulse in the scene
        self.lamp = K.light('POINT', (0, 0, 0), 40, COL["red"], size=0.3, name=f"{name}_zlamp", volume=0.5)
        self.lamp.parent = self.pivot
        self.lamp.location = (0, -0.25, 0)
        self.lamp.data.use_shadow = False

    def pulse(self, f0, f1, period=20, lo=2.6, hi=7.5):
        """Menacing heartbeat: double-thump emission + tiny scale throb."""
        em = self.red.node_tree.nodes["Emission"].inputs[1]
        for f in range(f0, f1 + 1):
            ph = ((f - f0) % period) / period
            beat = math.exp(-((ph - 0.05) / 0.05) ** 2) + 0.6 * math.exp(-((ph - 0.25) / 0.05) ** 2)
            em.default_value = lo + (hi - lo) * beat
            em.keyframe_insert("default_value", frame=f)
            s = 1.0 + 0.06 * beat
            self.zero.scale = (s, s, s)
            self.zero.keyframe_insert("scale", frame=f)
            self.lamp.data.energy = 25 + 60 * beat
            self.lamp.data.keyframe_insert("energy", frame=f)

    def glitch_inf(self, f, n=2):
        """The clue: exactly n frames of gold infinity in place of the 0."""
        self.zero.scale = (1, 1, 1)
        self.zero.keyframe_insert("scale", frame=f - 1)
        self.inf.scale = (0.0001,) * 3
        self.inf.keyframe_insert("scale", frame=f - 1)
        self.zero.scale = (0.0001,) * 3
        self.zero.keyframe_insert("scale", frame=f)
        self.inf.scale = (1, 1, 1)
        self.inf.keyframe_insert("scale", frame=f)
        self.inf.keyframe_insert("scale", frame=f + n - 1)
        self.zero.keyframe_insert("scale", frame=f + n - 1)
        self.zero.scale = (1, 1, 1)
        self.zero.keyframe_insert("scale", frame=f + n)
        self.inf.scale = (0.0001,) * 3
        self.inf.keyframe_insert("scale", frame=f + n)
        for o in (self.zero, self.inf):
            K._constant_all(o)

    def flip(self, f_crack, f_burst, f_settle, sparks=140):
        """Hero transition. f_crack: cracks open & gold light leaks; f_burst: shards blow out,
        flash; f_settle: infinity fully formed (it spins 180 deg while growing)."""
        rng = self.rng
        # cracks: segments separate slightly with jitter, emission flickers hotter
        em = self.red.node_tree.nodes["Emission"].inputs[1]
        for i, (o, c) in enumerate(self.segs):
            o.location = (0, 0, 0)
            o.rotation_euler = (0, 0, 0)
            o.keyframe_insert("location", frame=f_crack - 1)
            o.keyframe_insert("rotation_euler", frame=f_crack - 1)
            gap = c.normalized() * rng.uniform(0.02, 0.05) if i % 3 == 0 else c.normalized() * 0.012
            o.location = gap
            o.keyframe_insert("location", frame=f_crack + 2)
            o.location = gap * 1.6 + Vector((rng.uniform(-0.01, 0.01), 0, rng.uniform(-0.01, 0.01)))
            o.keyframe_insert("location", frame=f_burst - 1)
            o.keyframe_insert("rotation_euler", frame=f_burst - 1)
            # burst: fly outward, tumble, shrink
            v = (c.normalized() * rng.uniform(1.4, 2.6) + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-1.2, -0.3), rng.uniform(-0.2, 0.6))))
            for k in range(1, 22, 3):
                t = k / 24
                o.location = gap * 1.6 + v * t * 1.6 + Vector((0, 0, -2.5 * t * t))
                o.rotation_euler = (rng.uniform(-6, 6) * t, rng.uniform(-6, 6) * t, rng.uniform(-6, 6) * t)
                o.keyframe_insert("location", frame=f_burst + k)
                o.keyframe_insert("rotation_euler", frame=f_burst + k)
            o.scale = (1, 1, 1)
            o.keyframe_insert("scale", frame=f_burst + 6)
            o.scale = (0.0001,) * 3
            o.keyframe_insert("scale", frame=f_burst + 22)
        em.default_value = 10
        em.keyframe_insert("default_value", frame=f_crack - 1)
        for f in range(f_crack, f_burst):
            em.default_value = rng.uniform(4, 10) * (1 + (f - f_crack) / max(1, f_burst - f_crack))
            em.keyframe_insert("default_value", frame=f)
        # gold light leaking from inside the cracks
        core = K.sphere(f"{self.name}_core", (0, 0.02, 0), 0.3, self.gold, self.pivot, collection="meters")
        core.scale = (0.0001,) * 3
        core.keyframe_insert("scale", frame=f_crack)
        core.scale = (0.45, 0.05, 0.6)
        core.keyframe_insert("scale", frame=f_burst - 1)
        core.scale = (0.9, 0.25, 0.9)
        core.keyframe_insert("scale", frame=f_burst + 1)
        core.scale = (0.0001,) * 3
        core.keyframe_insert("scale", frame=f_burst + 7)
        # flash lights
        L = self.lamp.data
        L.color = COL["red"]
        L.keyframe_insert("color", frame=f_crack - 1)
        L.energy = 120
        L.keyframe_insert("energy", frame=f_crack - 1)
        L.color = COL["gold"]
        L.keyframe_insert("color", frame=f_crack + 3)
        L.energy = 300
        L.keyframe_insert("energy", frame=f_burst - 1)
        L.energy = 1500
        L.keyframe_insert("energy", frame=f_burst + 1)
        L.energy = 500
        L.keyframe_insert("energy", frame=f_burst + 10)
        L.energy = 260
        L.keyframe_insert("energy", frame=f_settle + 10)
        flash = K.light('POINT', (0, 0, 0), 0, COL["gold"], size=2.0, name=f"{self.name}_flash", volume=2.0)
        flash.parent = self.pivot
        flash.data.use_shadow = False
        flash.data.keyframe_insert("energy", frame=f_burst - 1)
        flash.data.energy = 4000
        flash.data.keyframe_insert("energy", frame=f_burst + 1)
        flash.data.energy = 0
        flash.data.keyframe_insert("energy", frame=f_burst + 9)
        # infinity: grow with overshoot while spinning 180 about the vertical (the flip)
        inf = self.inf
        inf.scale = (0.0001,) * 3
        inf.rotation_euler = (0, 0, math.radians(-180))  # spins about the screen-vertical axis
        inf.keyframe_insert("scale", frame=f_burst)
        inf.keyframe_insert("rotation_euler", frame=f_burst)
        span = max(6, f_settle - f_burst)
        for k, (u, s) in enumerate(((0.35, 0.8), (0.65, 1.25), (0.85, 0.95), (1.0, 1.0))):
            inf.scale = (s, s, s)
            inf.keyframe_insert("scale", frame=f_burst + int(span * u))
        inf.rotation_euler = (0, 0, math.radians(8))
        inf.keyframe_insert("rotation_euler", frame=f_burst + int(span * 0.75))
        inf.rotation_euler = (0, 0, 0)
        inf.keyframe_insert("rotation_euler", frame=f_settle)
        gem = self.gold.node_tree.nodes["Emission"].inputs[1]
        gem.default_value = 6
        gem.keyframe_insert("default_value", frame=f_burst)
        gem.default_value = 30
        gem.keyframe_insert("default_value", frame=f_burst + 3)
        gem.default_value = 7
        gem.keyframe_insert("default_value", frame=f_settle + 6)
        # gentle breathing glow after
        for f in range(f_settle + 8, self.fb, 12):
            gem.default_value = 7 + 2 * math.sin(f / 8.0)
            gem.keyframe_insert("default_value", frame=f)
        # gold spark shower
        spark_burst(self.pivot, f_burst, sparks, COL["gold"], name=f"{self.name}_spk", speed=3.2, seed=7)

    def hide(self, f):
        self.zero.scale = (1, 1, 1)
        self.zero.keyframe_insert("scale", frame=f - 1)
        self.zero.scale = (0.0001,) * 3
        self.zero.keyframe_insert("scale", frame=f)


def spark_burst(parent, frame, count, color, name="spk", speed=3.0, seed=0, life=30, gravity=3.0, size=0.035):
    """Keyed ballistic emissive sparks (deterministic, motion-blurred streaks)."""
    rng = random.Random(seed + frame)
    mat = K.emissive(color, 40, name=f"{name}_mat")
    pw = parent.matrix_world.translation.copy() if parent is not None else Vector((0, 0, 0))
    for i in range(count):
        o = K.box(f"{name}{i}", (0, 0, 0), (size, size, size * 3), mat, None, collection="fx")
        if parent is not None:
            o.parent = parent
        v = Vector((rng.gauss(0, 1), rng.gauss(0, 1) - 0.4, rng.gauss(0, 1) + 0.6)).normalized() * speed * rng.uniform(0.4, 1.3)
        lf = int(life * rng.uniform(0.6, 1.3))
        o.scale = (0.0001,) * 3
        o.keyframe_insert("scale", frame=frame - 1)
        o.scale = (1, 1, 1)
        o.keyframe_insert("scale", frame=frame)
        for k in range(0, lf + 1, 2):
            t = k / 24
            o.location = v * t + Vector((0, 0, -0.5 * gravity * t * t))
            o.keyframe_insert("location", frame=frame + k)
        o.scale = (0.0001,) * 3
        o.keyframe_insert("scale", frame=frame + lf + 1)
