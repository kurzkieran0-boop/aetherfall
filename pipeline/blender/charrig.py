"""Armature-rigged brick characters + procedural animation library (rig v2).

Every character is a real Blender armature:
    root ─ hips ─ spine ─ chest ─ neck ─ head ─ hairpivot
                    │        └─ upperarm ─ forearm(IK) ─ hand        (L/R)
                    └─ thigh ─ shin(IK) ─ foot(copy-rot footik)       (L/R)
    footik_L/R, handik_L/R : unparented world-space IK targets
    knee_pole_L/R (child of root), elbow_pole_L/R (child of chest)
Chunky toy-brick meshes are rigidly bound to the bones (no skin deformation), with
ball joints at knees/elbows. Faces are one mesh with shape keys:
    blink_L blink_R squint eye_wide brow_up brow_angry brow_sad mouth_open mouth_wide
    mouth_O smile frown look_L look_R look_U look_D

Animation is procedural and baked per frame:
  * locomotion uses a phase-driven gait planner: a foot that is in stance is pinned to a
    world position (heel-strike -> flat -> toe-roll pivots keep the contact point locked),
    so feet cannot slide by construction; hips height is clamped to the IK reach so legs
    never over-extend (no popping).
  * stationary actions keep feet planted; if the root turns or shifts, the planner takes
    real settle steps (one foot at a time).
  * actions are layered: body pose (12-principles keyed curves: anticipation, overshoot,
    follow-through, squash/stretch on the blocks, arcs, eased timing), face (expressions,
    blinks, eye darts, amplitude/spectral lip-sync), secondary motion (hair lag).
  * consecutive actions cross-fade over a few frames, never pop.
`check()` evaluates the rig after IK and reports foot sliding, ground penetration,
character overlap, IK over-reach and bone popping.
"""
import math
import random

import bpy
import bmesh
from bpy_extras import anim_utils
from mathutils import Vector, Matrix, Quaternion, Euler

import kit as K

TAU = math.tau

# ---------------------------------------------------------------- rest skeleton
LEG_LEN = 0.822
HIPJ = 0.93
STAND_DROP = -0.035            # hips offset when standing (soft knees)


def _bones():
    B = [("root", (0, 0, 0), (0, 0.5, 0), None, False),
         ("hips", (0, 0, 0.95), (0, 0, 1.12), "root", False),
         ("spine", (0, 0, 1.02), (0, 0, 1.36), "hips", False),
         ("chest", (0, 0, 1.36), (0, 0, 1.76), "spine", True),
         ("neck", (0, 0, 1.76), (0, 0, 1.84), "chest", True),
         ("head", (0, 0, 1.84), (0, 0, 2.42), "neck", True),
         ("hairpivot", (0, 0.05, 2.4), (0, 0.05, 2.5), "head", False)]
    for s, sx in (("L", 1), ("R", -1)):
        B += [(f"upperarm_{s}", (0.5 * sx, 0, 1.66), (0.5 * sx, 0.03, 1.33), "chest", False),
              (f"forearm_{s}", (0.5 * sx, 0.03, 1.33), (0.5 * sx, 0, 1.0), f"upperarm_{s}", True),
              (f"hand_{s}", (0.5 * sx, 0, 1.0), (0.5 * sx, 0, 0.86), f"forearm_{s}", True),
              (f"thigh_{s}", (0.19 * sx, 0, HIPJ), (0.19 * sx, -0.03, 0.52), "hips", False),
              (f"shin_{s}", (0.19 * sx, -0.03, 0.52), (0.19 * sx, 0, 0.11), f"thigh_{s}", True),
              (f"foot_{s}", (0.19 * sx, 0, 0.11), (0.19 * sx, -0.22, 0.11), f"shin_{s}", False),
              (f"footik_{s}", (0.19 * sx, 0, 0.11), (0.19 * sx, -0.22, 0.11), None, False),
              (f"knee_pole_{s}", (0.19 * sx, -1.4, 0.52), (0.19 * sx, -1.4, 0.7), "root", False),
              (f"handik_{s}", (0.5 * sx, 0, 1.0), (0.5 * sx, 0, 0.86), None, False),
              (f"elbow_pole_{s}", (0.62 * sx, 1.0, 1.33), (0.62 * sx, 1.0, 1.5), "chest", False)]
    return B


FACE_KEYS = ["blink_L", "blink_R", "squint", "eye_wide", "brow_up", "brow_angry", "brow_sad", "mouth_open",
             "mouth_wide", "mouth_O", "smile", "frown", "look_L", "look_R", "look_U", "look_D"]

EXPR = {
    "neutral": {},
    "calm": {"smile": 0.1},
    "sad": {"brow_sad": 0.85, "frown": 0.45, "look_D": 0.15},
    "lonely": {"brow_sad": 0.6, "frown": 0.25, "look_D": 0.25},
    "fear": {"brow_sad": 0.55, "brow_up": 0.5, "mouth_open": 0.25, "eye_wide": 0.6, "frown": 0.3},
    "shock": {"brow_up": 1.0, "mouth_open": 0.55, "mouth_O": 0.3, "eye_wide": 0.9},
    "determined": {"brow_angry": 0.65, "mouth_wide": 0.25, "squint": 0.25},
    "angry": {"brow_angry": 1.0, "frown": 0.45, "squint": 0.3},
    "happy": {"smile": 1.0, "brow_up": 0.3, "squint": 0.3},
    "smug": {"smile": 0.65, "brow_angry": 0.3, "squint": 0.45},
    "hopeful": {"brow_sad": 0.35, "brow_up": 0.35, "smile": 0.35},
    "strain": {"brow_angry": 0.85, "squint": 0.75, "mouth_wide": 0.75, "mouth_open": 0.12},
    "pain": {"squint": 1.0, "brow_sad": 0.6, "mouth_wide": 0.55, "mouth_open": 0.2},
    "scream": {"brow_up": 0.8, "mouth_open": 1.0, "mouth_O": 0.3, "eye_wide": 0.7},
    "disgust": {"brow_angry": 0.5, "frown": 0.6, "squint": 0.35},
    "awe": {"brow_up": 0.8, "mouth_O": 0.6, "mouth_open": 0.3, "eye_wide": 0.5},
    "tender": {"smile": 0.5, "brow_sad": 0.3, "squint": 0.2},
    "hurt": {"brow_sad": 1.0, "frown": 0.35, "mouth_open": 0.1, "eye_wide": 0.25},
    "wary": {"brow_angry": 0.35, "brow_sad": 0.2, "frown": 0.2, "squint": 0.2},
    "blank": {},
}


# ---------------------------------------------------------------- small math helpers
def clamp(x, a, b):
    return a if x < a else b if x > b else x


def smooth(t):
    t = clamp(t, 0, 1)
    return t * t * (3 - 2 * t)


def smoother(t):
    t = clamp(t, 0, 1)
    return t * t * t * (t * (6 * t - 15) + 10)


def ease_out(t, p=3):
    return 1 - (1 - clamp(t, 0, 1)) ** p


def ease_in(t, p=2):
    return clamp(t, 0, 1) ** p


def back_out(t, s=1.6):
    """Overshoot then settle (follow-through)."""
    t = clamp(t, 0, 1) - 1
    return t * t * ((s + 1) * t + s) + 1


def keys(t, pts):
    """Piecewise eased interpolation through [(t, value), ...]; value may be tuple."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (ta, va), (tb, vb) in zip(pts, pts[1:]):
        if t <= tb:
            u = smooth((t - ta) / max(1e-6, tb - ta))
            if isinstance(va, (tuple, list)):
                return tuple(a + (b - a) * u for a, b in zip(va, vb))
            return va + (vb - va) * u
    return pts[-1][1]


def lerp(a, b, u):
    if isinstance(a, (tuple, list)):
        return tuple(x + (y - x) * u for x, y in zip(a, b))
    return a + (b - a) * u


def yaw_to(dx, dy):
    return math.degrees(math.atan2(dy, dx)) + 90.0


def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def fwd_vec(yaw):
    a = math.radians(yaw)
    return Vector((math.sin(a), -math.cos(a), 0.0))


def side_vec(yaw):            # character's +X (left side) in world
    a = math.radians(yaw)
    return Vector((math.cos(a), math.sin(a), 0.0))


# ---------------------------------------------------------------- neutral pose
def neutral():
    return {"hip": (0.0, 0.0, STAND_DROP), "hipr": (0.0, 0.0, 0.0), "spine": (0.0, 0.0, 0.0),
            "chest": (0.0, 0.0, 0.0), "neck": (0.0, 0.0, 0.0), "head": (0.0, 0.0, 0.0),
            "uaL": (0.0, 6.0, 0.0), "uaR": (0.0, 6.0, 0.0), "faL": 10.0, "faR": 10.0,
            "hdL": (0.0, 0.0), "hdR": (0.0, 0.0), "sq": 1.0, "hsq": 1.0, "legik": 1.0,
            "thL": (0.0, 0.0), "thR": (0.0, 0.0), "shL": 0.0, "shR": 0.0,
            "armikL": 0.0, "armikR": 0.0, "face": {}, "look": (0.0, 0.0)}


def blend_pose(a, b, u):
    out = {}
    for k in a:
        if k == "face":
            ks = set(a["face"]) | set(b["face"])
            out["face"] = {n: lerp(a["face"].get(n, 0.0), b["face"].get(n, 0.0), u) for n in ks}
        else:
            out[k] = lerp(a[k], b.get(k, a[k]), u)
    return out


def add(p, k, d):
    v = p[k]
    if isinstance(v, (tuple, list)):
        p[k] = tuple(x + y for x, y in zip(v, d))
    else:
        p[k] = v + d


# =================================================================== CHARACTER
_FONT_MATS = {}


def _mesh_box(bm, c, s, group, groups):
    """Add an axis-aligned box to bmesh; record its vertex indices under `group`."""
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    vs = []
    for dx in (-hx, hx):
        for dy in (-hy, hy):
            for dz in (-hz, hz):
                vs.append(bm.verts.new((c[0] + dx, c[1] + dy, c[2] + dz)))
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for q in f:
        bm.faces.new([vs[i] for i in q])
    bm.verts.index_update()
    groups.setdefault(group, []).extend(vs)
    return vs


class BrickChar:
    """A rigged brick figure. spec: palette{shirt,pants,hair,hat,stripe,shoes}, accessory,
    scale, skin, style ('normal'|'default'|'vip')."""

    def __init__(self, name, spec=None):
        spec = spec or {}
        self.name = name
        self.spec = spec
        self.s = float(spec.get("scale", 1.0))
        self.style = spec.get("style", "normal")
        p = spec.get("palette", {})
        self.mats = {
            "shirt": K.plastic(tuple(p.get("shirt", (0.8, 0.15, 0.1))), 0.38),
            "pants": K.plastic(tuple(p.get("pants", (0.1, 0.15, 0.4))), 0.45),
            "skin": K.plastic(tuple(spec.get("skin", (0.95, 0.78, 0.3))), 0.36, coat=0.5),
            "shoes": K.plastic(tuple(p.get("shoes", (0.06, 0.06, 0.07))), 0.3),
            "dark": K.plastic((0.02, 0.02, 0.025), 0.25),
            "white": K.plastic((0.96, 0.96, 0.96), 0.15),
            "hair": K.plastic(tuple(p.get("hair", (0.15, 0.08, 0.04))), 0.55),
            "hat": K.plastic(tuple(p.get("hat", (0.1, 0.2, 0.7))), 0.4),
            "mouthin": K.plastic((0.25, 0.04, 0.05), 0.4),
        }
        if "stripe" in p:
            self.mats["stripe"] = K.plastic(tuple(p["stripe"]), 0.3)
        if "sleeve" in p:
            self.mats["sleeve"] = K.plastic(tuple(p["sleeve"]), 0.38)
        self._build_armature()
        self._build_body(spec.get("accessory", "none"))
        self._build_face()
        self.parts = [o for o in bpy.data.objects if o.name.startswith(name + "_") and o.type == 'MESH']
        # proxies the camera system reads (head / torso / root world points)
        self.root = self._proxy("rootpt", "root", (0, 0, 0))
        self.torso = self._proxy("torsopt", "spine", (0, 0, 1.2))
        self.head = self._proxy("headpt", "head", (0, 0, 1.9))
        self.meter_anchor = self._proxy("meterpt", "head", (0, 0, 2.98))
        self.timeline = []          # [(f0, f1, action, kw)]
        self.lips = []              # [(frame, open, wide, round)]
        self.facing = 0.0
        self.start = (0.0, 0.0, 0.0)

    # ---------------------------------------------------------- construction
    def _build_armature(self):
        n = self.name
        ad = bpy.data.armatures.new(n + "_armdata")
        ao = bpy.data.objects.new(n + "_rig", ad)
        K.coll("chars").objects.link(ao)
        ao.scale = (self.s,) * 3
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = ao
        bpy.ops.object.mode_set(mode='EDIT')
        eb = {}
        for bn, h, t, par, con in _bones():
            b = ad.edit_bones.new(bn)
            b.head, b.tail = h, t
            b.roll = 0.0
            if par:
                b.parent = eb[par]
                b.use_connect = con
            if bn.startswith(("footik", "handik", "knee_pole", "elbow_pole", "root", "hairpivot")):
                b.use_deform = False
            eb[bn] = b
        bpy.ops.object.mode_set(mode='OBJECT')
        self.arm = ao
        self.rest = {b.name: b.matrix_local.copy() for b in ad.bones}
        self.rest3 = {k: m.to_3x3() for k, m in self.rest.items()}
        for pb in ao.pose.bones:
            pb.rotation_mode = 'QUATERNION'
        for s in ("L", "R"):
            ik = ao.pose.bones[f"shin_{s}"].constraints.new('IK')
            ik.name = "IK"
            ik.target, ik.subtarget = ao, f"footik_{s}"
            ik.pole_target, ik.pole_subtarget = ao, f"knee_pole_{s}"
            ik.pole_angle = math.radians(-90)
            ik.chain_count = 2
            cr = ao.pose.bones[f"foot_{s}"].constraints.new('COPY_ROTATION')
            cr.name = "FOOTROT"
            cr.target, cr.subtarget = ao, f"footik_{s}"
            aik = ao.pose.bones[f"forearm_{s}"].constraints.new('IK')
            aik.name = "IK"
            aik.target, aik.subtarget = ao, f"handik_{s}"
            aik.pole_target, aik.pole_subtarget = ao, f"elbow_pole_{s}"
            aik.pole_angle = math.radians(-90)
            aik.chain_count = 2
            aik.influence = 0.0

    def _bind(self, ob, bone):
        """Rigidly parent mesh `ob` (posed in rest armature space) to `bone`."""
        ao = self.arm
        mw = ob.matrix_world.copy() if ob.parent is None else ob.matrix_world.copy()
        ob.parent = ao
        ob.parent_type = 'BONE'
        ob.parent_bone = bone
        b = ao.data.bones[bone]
        tail_m = Matrix.Translation((0, b.length, 0))
        ob.matrix_parent_inverse = (Matrix.Diagonal((self.s,) * 3 + (1,)) @ b.matrix_local @ tail_m).inverted()
        ob.matrix_world = Matrix.Diagonal((self.s,) * 3 + (1,)) @ mw
        return ob

    def _part(self, tag, bone, c, size, mat, bevel=0.04, rot=(0, 0, 0)):
        ob = K.box(f"{self.name}_{tag}", c, size, mat, None, bevel=bevel, rot=rot, collection="chars")
        bpy.context.view_layer.update()
        return self._bind(ob, bone)

    def _ball(self, tag, bone, c, r, mat):
        ob = K.sphere(f"{self.name}_{tag}", c, r, mat, None, collection="chars")
        bpy.context.view_layer.update()
        return self._bind(ob, bone)

    def attach(self, ob, bone, rest_loc, rest_rot=(0, 0, 0)):
        """Parent a prop to a bone, placing it where it would sit on the character in its REST
        pose (character at origin facing -Y, unscaled units). Works at any frame/pose."""
        b = self.arm.data.bones[bone]
        ob.parent = self.arm
        ob.parent_type = 'BONE'
        ob.parent_bone = bone
        S = Matrix.Diagonal((self.s,) * 3 + (1,))
        ob.matrix_parent_inverse = (S @ b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
        ob.matrix_basis = S @ Matrix.LocRotScale(Vector(rest_loc), Euler(rest_rot), None)
        return ob

    def _proxy(self, tag, bone, c):
        e = K.empty(f"{self.name}_{tag}", c, None, "rig")
        bpy.context.view_layer.update()
        return self._bind(e, bone)

    def _build_body(self, acc):
        M = self.mats
        sh = M["shirt"]
        sleeve = M.get("sleeve", sh)
        default = self.style == "default"
        if default:
            sleeve = sh
        self._part("pelvis", "hips", (0, 0, 0.99), (0.74, 0.42, 0.2), M["pants"], 0.04)
        self._part("body", "spine", (0, 0, 1.38), (0.78, 0.44, 0.7), sh, 0.06)
        if "stripe" in M:
            self._part("stripe", "chest", (0, -0.224, 1.5), (0.79, 0.02, 0.12), M["stripe"], 0.0)
        if self.spec.get("badge"):
            self._part("badge", "chest", (0.2, -0.228, 1.56), (0.12, 0.02, 0.12),
                       K.emissive(tuple(self.spec["badge"]), 6), 0.0)
        self._part("neckblk", "neck", (0, 0, 1.79), (0.26, 0.24, 0.1), M["skin"], 0.02)
        self._part("skull", "head", (0, 0, 2.11), (0.66, 0.6, 0.6), M["skin"], 0.09)
        for s, sx in (("L", 1), ("R", -1)):
            self._part(f"shoulder{s}", "chest", (0.47 * sx, 0, 1.6), (0.22, 0.42, 0.2), sh, 0.06)
            self._part(f"uarm{s}", f"upperarm_{s}", (0.5 * sx, 0.015, 1.5), (0.23, 0.27, 0.36), sleeve, 0.05)
            self._ball(f"elbow{s}", f"forearm_{s}", (0.5 * sx, 0.03, 1.33), 0.12, sleeve if not default else M["skin"])
            self._part(f"farm{s}", f"forearm_{s}", (0.5 * sx, 0.015, 1.17), (0.215, 0.25, 0.32),
                       M["skin"] if self.spec.get("bare_arms") or default else sleeve, 0.05)
            self._part(f"hand{s}", f"hand_{s}", (0.5 * sx, -0.01, 0.92), (0.2, 0.24, 0.17), M["skin"], 0.06)
            self._part(f"thigh{s}", f"thigh_{s}", (0.19 * sx, -0.015, 0.73), (0.32, 0.36, 0.44), M["pants"], 0.05)
            self._ball(f"knee{s}", f"shin_{s}", (0.19 * sx, -0.03, 0.52), 0.15, M["pants"])
            self._part(f"shin{s}", f"shin_{s}", (0.19 * sx, -0.015, 0.33), (0.3, 0.34, 0.4), M["pants"], 0.05)
            self._part(f"shoe{s}", f"foot_{s}", (0.19 * sx, -0.06, 0.065), (0.34, 0.5, 0.13), M["shoes"], 0.04)
        hatm, hair = M["hat"], M["hair"]
        if acc == "cap":
            self._part("cap", "hairpivot", (0, 0, 2.47), (0.7, 0.64, 0.16), hatm, 0.04)
            self._part("brim", "hairpivot", (0, -0.4, 2.42), (0.54, 0.26, 0.04), hatm, 0.01)
        elif acc == "hair":
            self._part("hair", "hairpivot", (0, 0.03, 2.45), (0.72, 0.66, 0.2), hair, 0.05)
            self._part("hairback", "hairpivot", (0, 0.29, 2.2), (0.7, 0.1, 0.5), hair, 0.03)
            self._part("fringe", "hairpivot", (0.14, -0.3, 2.36), (0.42, 0.06, 0.12), hair, 0.02, rot=(0, 0.15, 0))
        elif acc == "ponytail":
            self._part("hair", "hairpivot", (0, 0.03, 2.45), (0.72, 0.66, 0.18), hair, 0.05)
            self._part("tail", "hairpivot", (0, 0.4, 2.2), (0.2, 0.18, 0.5), hair, 0.06)
        elif acc == "spiky":
            self._part("hair", "hairpivot", (0, 0.02, 2.46), (0.7, 0.64, 0.16), hair, 0.03)
            for k in range(5):
                self._part(f"spike{k}", "hairpivot", (-0.24 + k * 0.12, 0.02, 2.6), (0.1, 0.5, 0.2), hair, 0.02,
                           rot=(0, 0.25 * (k - 2), 0))
        elif acc == "hood":
            self._part("hood", "hairpivot", (0, 0.06, 2.2), (0.76, 0.7, 0.68), hatm, 0.1)
        elif acc == "crown":       # VIP: gold band
            self._part("hair", "hairpivot", (0, 0.03, 2.45), (0.72, 0.66, 0.16), hair, 0.05)
            gold = K.plastic((1.0, 0.72, 0.18), 0.15)
            self._part("crown", "hairpivot", (0, 0.03, 2.58), (0.56, 0.5, 0.12), gold, 0.02)
        elif acc == "shades":
            self._part("hair", "hairpivot", (0, 0.03, 2.45), (0.72, 0.66, 0.18), hair, 0.05)
            self._part("shades", "head", (0, -0.315, 2.18), (0.5, 0.03, 0.12), K.plastic((0.02, 0.02, 0.03), 0.05), 0.01)
        elif acc == "beanie":
            self._part("beanie", "hairpivot", (0, 0.02, 2.47), (0.7, 0.64, 0.24), hatm, 0.08)

    def _build_face(self):
        n = self.name
        me = bpy.data.meshes.new(n + "_face")
        bm = bmesh.new()
        g = {}
        default = self.style == "default"
        ex, ez, fy = 0.135, 2.17, -0.304
        for s, sx in (("L", 1), ("R", -1)):
            if default:      # blank default: plain dot eyes, no whites
                _mesh_box(bm, (ex * sx, fy - 0.012, ez), (0.075, 0.02, 0.11), f"pupil{s}", g)
                _mesh_box(bm, (ex * sx + 0.012, fy - 0.022, ez + 0.03), (0.022, 0.01, 0.025), f"glint{s}", g)
            else:
                _mesh_box(bm, (ex * sx, fy, ez), (0.16, 0.02, 0.17), f"eye{s}", g)
                _mesh_box(bm, (ex * sx, fy - 0.012, ez - 0.01), (0.085, 0.02, 0.11), f"pupil{s}", g)
                _mesh_box(bm, (ex * sx + 0.018, fy - 0.022, ez + 0.022), (0.03, 0.01, 0.034), f"glint{s}", g)
            _mesh_box(bm, (ex * sx, fy - 0.006, ez + 0.135), (0.19, 0.03, 0.045), f"brow{s}", g)
        my = fy - 0.006
        _mesh_box(bm, (0, my, 2.0), (0.13, 0.02, 0.045), "mouthC", g)
        for s, sx in (("L", 1), ("R", -1)):
            _mesh_box(bm, (0.09 * sx, my, 2.0), (0.05, 0.02, 0.045), f"mouth{s}", g)
        _mesh_box(bm, (0, my - 0.006, 2.016), (0.16, 0.012, 0.0005), "teeth", g)
        bm.verts.index_update()
        gi = {k: [v.index for v in vs] for k, vs in g.items()}
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(n + "_face", me)
        K.coll("chars").objects.link(ob)
        # material slots: dark default, whites for eyes/glint/teeth
        me.materials.append(self.mats["dark"])
        me.materials.append(self.mats["white"])
        idx = {vi for grp in ("eyeL", "eyeR", "glintL", "glintR", "teeth") for vi in gi.get(grp, [])}
        for p in me.polygons:
            if all(vi in idx for vi in p.vertices):
                p.material_index = 1
        ob.shape_key_add(name="Basis")
        co = [Vector(v.co) for v in me.vertices]

        def sk(name, fn):
            k = ob.shape_key_add(name=name, from_mix=False)
            for i, c in enumerate(co):
                nc = fn(i, c.copy())
                if nc is not None:
                    k.data[i].co = nc

        def in_(i, *grps):
            return any(i in gi.get(x, ()) for x in grps)

        def eye_c(side):
            return Vector((ex * (1 if side == "L" else -1), 0, ez))

        def squash_z(c, cz, f):
            c.z = cz + (c.z - cz) * f
            return c
        for s in ("L", "R"):
            sk(f"blink_{s}", lambda i, c, s=s: squash_z(c, ez - 0.03, 0.08) if in_(i, f"eye{s}", f"pupil{s}", f"glint{s}") else None)
        sk("squint", lambda i, c: squash_z(c, ez - 0.02, 0.55) if in_(i, "eyeL", "eyeR", "pupilL", "pupilR", "glintL", "glintR") else None)
        sk("eye_wide", lambda i, c: squash_z(c, ez, 1.28) if in_(i, "eyeL", "eyeR") else (c + Vector((0, 0, 0.025)) if in_(i, "browL", "browR") else None))

        def brow(i, c, inner_dz, outer_dz, all_dz=0.0):
            if not in_(i, "browL", "browR"):
                return None
            inner = abs(c.x) < ex
            c.z += all_dz + (inner_dz if inner else outer_dz)
            return c
        sk("brow_up", lambda i, c: brow(i, c, 0.05, 0.045))
        sk("brow_angry", lambda i, c: brow(i, c, -0.05, 0.012, -0.01))
        sk("brow_sad", lambda i, c: brow(i, c, 0.05, -0.022))

        def mouth(i, c, mode):
            if not in_(i, "mouthC", "mouthL", "mouthR", "teeth"):
                return None
            corner = in_(i, "mouthL", "mouthR")
            bottom = c.z < 2.0
            sx = 1 if c.x > 0 else -1
            if mode == "open":
                if in_(i, "teeth"):
                    if c.z < 2.016:
                        c.z -= 0.022
                    return c
                if bottom:
                    c.z -= 0.075 if not corner else 0.035
                return c
            if mode == "wide":
                if in_(i, "teeth"):
                    c.x *= 1.3
                    return c
                c.x = c.x * 1.32 + (0.02 * sx if corner else 0)
                c.z = 2.0 + (c.z - 2.0) * 0.7
                return c
            if mode == "O":
                if in_(i, "teeth"):
                    c.x *= 0.5
                    return c
                c.x *= 0.55
                if bottom:
                    c.z -= 0.04
                elif not corner:
                    c.z += 0.01
                return c
            if mode in ("smile", "frown"):
                if in_(i, "teeth"):
                    return None
                d = 1 if mode == "smile" else -1
                if corner:
                    c.z += d * (0.02 + 0.03 * (abs(c.x) - 0.065) / 0.05)
                    c.x *= 1.06 if d > 0 else 0.97
                elif d < 0:
                    c.z += 0.006
                return c
        for mode, nm in (("open", "mouth_open"), ("wide", "mouth_wide"), ("O", "mouth_O"), ("smile", "smile"), ("frown", "frown")):
            sk(nm, lambda i, c, m=mode: mouth(i, c, m))
        for nm, d in (("look_L", (0.035, 0, 0)), ("look_R", (-0.035, 0, 0)), ("look_U", (0, 0, 0.035)), ("look_D", (0, 0, -0.04))):
            sk(nm, lambda i, c, d=d: (c + Vector(d)) if in_(i, "pupilL", "pupilR", "glintL", "glintR") else None)
        bpy.context.view_layer.update()
        self.face = self._bind(ob, "head")

    # ---------------------------------------------------------- scripting API
    def place(self, loc, facing):
        self.start = tuple(loc)
        self.facing = float(facing)

    def add(self, action, f0, f1, **kw):
        self.timeline.append((int(f0), int(f1), action, kw))

    # ---------------------------------------------------------- baking
    def bake(self, fa, fb, look_tracks=None, seed=0):
        """Solve root/feet/body/face over [fa, fb] and write per-frame keys."""
        Animator(self, fa, fb, look_tracks or {}, seed).run()

    def ground_points(self):
        return []


# =================================================================== fcurve writer
def _channelbag(idblock):
    ad = idblock.animation_data
    act = ad.action
    try:
        return anim_utils.action_get_channelbag_for_slot(act, ad.action_slot)
    except Exception:
        return None


def bake_curve(idblock, path, index, frames, values):
    idblock.keyframe_insert(data_path=path, index=index, frame=frames[0])
    cb = _channelbag(idblock)
    fc = cb.fcurves.find(path, index=index) if cb else None
    if fc is None:
        for f in (idblock.animation_data.action.fcurves if hasattr(idblock.animation_data.action, "fcurves") else []):
            if f.data_path == path and f.array_index == max(0, index):
                fc = f
        if fc is None:
            return
    fc.keyframe_points.clear()
    n = len(frames)
    fc.keyframe_points.add(n)
    co = [0.0] * (2 * n)
    co[0::2] = frames
    co[1::2] = values
    fc.keyframe_points.foreach_set("co", co)
    fc.keyframe_points.foreach_set("interpolation", [1] * n)  # LINEAR
    fc.update()


# =================================================================== ANIMATOR
GAIT = {  # stride L, duty, lift, base hip drop, bob, arm swing, lean, speed ref
    "walk": dict(L=1.0, duty=0.62, lift=0.13, drop=-0.05, bob=0.03, arm=26, lean=4, v=1.5),
    "sad_walk": dict(L=0.75, duty=0.66, lift=0.08, drop=-0.07, bob=0.02, arm=10, lean=12, v=1.0),
    "sneak": dict(L=0.65, duty=0.7, lift=0.1, drop=-0.16, bob=0.015, arm=12, lean=16, v=0.8),
    "run": dict(L=2.0, duty=0.38, lift=0.3, drop=-0.1, bob=0.06, arm=55, lean=12, v=5.0),
    "sprint": dict(L=2.3, duty=0.34, lift=0.34, drop=-0.12, bob=0.07, arm=65, lean=16, v=6.5),
    "panic_sprint": dict(L=2.1, duty=0.36, lift=0.3, drop=-0.1, bob=0.07, arm=40, lean=10, v=6.0),
    "back_away": dict(L=0.6, duty=0.66, lift=0.1, drop=-0.08, bob=0.02, arm=8, lean=-6, v=0.9, back=True),
    "drag": dict(L=0.45, duty=0.75, lift=0.07, drop=-0.22, bob=0.02, arm=0, lean=28, v=0.5, back=True),
    "carry_walk": dict(L=0.7, duty=0.68, lift=0.09, drop=-0.1, bob=0.03, arm=0, lean=6, v=0.9),
    "stagger": dict(L=0.6, duty=0.6, lift=0.1, drop=-0.12, bob=0.04, arm=20, lean=10, v=0.8),
}
LOCO = set(GAIT)

STATIONARY = {"idle", "talk", "listen", "gasp", "flinch", "look_up", "point", "slump", "hug", "dig", "lift", "shove",
              "cheer", "pose", "emote", "wave", "whisper", "cross_arms", "offer", "kneel", "kneel_reach", "hold_pet",
              "panic", "look_around", "take_hand", "fall", "get_up", "lie", "shoved", "turn", "mock", "stare",
              "brace", "reach", "tremble", "lift_beam", "pinned", "sit_up", "fix", "pickup", "give", "selfie",
              "hands_mouth", "pet_hug", "slam", "laugh", "stand", "sit"}


class Animator:
    def __init__(self, ch, fa, fb, look_tracks, seed):
        self.c = ch
        self.fa, self.fb = fa, fb
        self.frames = list(range(fa, fb + 1))
        self.look_tracks = look_tracks
        self.rng = random.Random(seed * 7919 + hash(ch.name) % 10007)
        tl = sorted(ch.timeline, key=lambda a: a[0]) or [(fa, fb, "idle", {})]
        self.tl = tl
        self.report = {"overreach": 0}

    # ------------------------------------------------------------ action at frame
    def act_at(self, f):
        cur = None
        for a in self.tl:
            if a[0] <= f:
                cur = a
        return cur or self.tl[0]

    # ------------------------------------------------------------ 1) root trajectory
    def solve_root(self):
        c = self.c
        pos = Vector(c.start)
        yaw = c.facing
        P, Y, M, SP = {}, {}, {}, {}
        disp = {}
        f = self.fa
        idx = 0
        tl = self.tl
        # first action may carry its own placement
        a0 = tl[0][3]
        if "at" in a0:
            pos = Vector(a0["at"])
        if "facing" in a0:
            yaw = float(a0["facing"])
        if a0.get("path"):
            pos = Vector(a0["path"][0])
        if a0.get("traj"):
            pos = Vector((a0["traj"][0][1], a0["traj"][0][2], a0["traj"][0][3] if len(a0["traj"][0]) > 3 else 0))
        prev_yaw = yaw
        for f in self.frames:
            a = self.act_at(f)
            f0, f1, name, kw = a
            dur = max(1, f1 - f0)
            u = clamp((f - f0) / dur, 0, 1)
            mode = None
            if name in LOCO and (kw.get("path") or kw.get("traj")):
                g = GAIT[name]
                if kw.get("traj"):
                    tr = kw["traj"]
                    # traj: [[frame, x, y(, z)], ...] linear interpolation
                    if f <= tr[0][0]:
                        q = tr[0]
                    elif f >= tr[-1][0]:
                        q = tr[-1]
                    else:
                        q = tr[-1]
                        for k in range(len(tr) - 1):
                            if tr[k][0] <= f <= tr[k + 1][0]:
                                w = (f - tr[k][0]) / max(1e-6, tr[k + 1][0] - tr[k][0])
                                q = [lerp(tr[k][j], tr[k + 1][j], w) for j in range(len(tr[k]))]
                                break
                    newp = Vector((q[1], q[2], q[3] if len(q) > 3 else pos.z))
                else:
                    pts = [Vector(p) for p in kw["path"]]
                    segs = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
                    D = sum(segs)
                    acc = kw.get("accel", 0.22 if name not in ("drag", "back_away") else 0.15)
                    dec = 0.0 if kw.get("keep_going") else kw.get("decel", acc)
                    s = _trapezoid(u, acc, dec, start_moving=kw.get("start_moving", False)) * D
                    newp = _along(pts, segs, s)
                dv = newp - pos
                dv.z = 0
                if dv.length > 1e-5:
                    hy = yaw_to(dv.x, dv.y) + (180 if g.get("back") else 0)
                    yaw = prev_yaw + wrap180(hy - prev_yaw) * kw.get("turn_rate", 0.32)
                pos = newp
                mode = name
            else:
                tgt_yaw = None
                if f == f0:
                    if "at" in kw and a is not tl[0]:
                        pos = Vector(kw["at"])
                if "facing" in kw:
                    tgt_yaw = float(kw["facing"])
                elif kw.get("face_to") is not None:
                    d = Vector(kw["face_to"]) - pos
                    tgt_yaw = yaw_to(d.x, d.y)
                if tgt_yaw is not None:
                    # turn: head leads, body follows with overshoot over ~10 frames
                    tf = kw.get("turn_frames", 10)
                    w = back_out(clamp((f - f0) / tf, 0, 1), 1.2)
                    if f == f0:
                        self._turn_from = getattr(self, "_turn_from", {})
                        self._turn_from[a[0]] = yaw
                    y0 = getattr(self, "_turn_from", {}).get(a[0], yaw)
                    yaw = y0 + wrap180(tgt_yaw - y0) * w
                # displacement actions
                if kw.get("slide"):
                    pts = [Vector(p) for p in kw["slide"]]
                    w = smooth(clamp((f - f0) / dur, 0, 1))
                    pos = pts[0].lerp(pts[-1], w)
                if name == "shoved":
                    dirv = Vector(kw.get("dir", (0, 1, 0))).normalized()
                    d0 = kw.get("dist", 1.1)
                    w = ease_out(clamp((f - f0) / 10, 0, 1), 3)
                    w0 = ease_out(clamp((f - 1 - f0) / 10, 0, 1), 3) if f > f0 else 0
                    pos = pos + dirv * d0 * (w - w0)
                    mode = "stagger" if 0 < f - f0 < 12 else None
                elif name == "fall":
                    pass
            P[f], Y[f], M[f] = pos.copy(), yaw, mode
            prev_yaw = yaw
        # speeds
        for f in self.frames:
            fp = P.get(f - 1, P[f])
            d = P[f] - fp
            d.z = 0
            SP[f] = d.length * 24.0
        self.P, self.Y, self.M, self.SP = P, Y, M, SP

    # ------------------------------------------------------------ 2) feet planner
    def solve_feet(self):
        c = self.c
        s = c.s
        P, Y, M, SP = self.P, self.Y, self.M, self.SP
        lat = 0.2 * s
        phase = {}
        ph = 0.0
        for f in self.frames:
            if M[f]:
                g = GAIT[M[f]]
                L = g["L"] * s * clamp((SP[f] / (g["v"] * s)) ** 0.5 if SP[f] > 0 else 1, 0.75, 1.2)
                dd = (P[f] - P.get(f - 1, P[f])).length if f - 1 in P else 0.0
                ph += dd / max(1e-6, L)
            phase[f] = ph
        self.phase = phase

        def stand(f, sx):
            return P[f] + side_vec(Y[f]) * (lat * sx)
        feet = {}
        for side, sx, off in (("L", 1, 0.0), ("R", -1, 0.5)):
            st = {"P": stand(self.fa, sx), "Y": Y[self.fa], "sw": None, "cool": 0, "lifted": None}
            out = {}
            prev_frac = None
            for f in self.frames:
                mode = M[f]
                sw = st["sw"]
                if sw and f >= sw["fe"]:
                    st["P"], st["Y"] = sw["to"], sw["toY"]
                    st["sw"] = None
                    sw = None
                    st["cool"] = 3
                fr = (phase[f] + off) % 1.0
                if sw is None:
                    if mode:
                        g = GAIT[mode]
                        cyc = math.floor(phase[f] + off)
                        if fr >= g["duty"] and st["lifted"] != cyc and phase[f] > phase.get(f - 1, -1):
                            st["lifted"] = cyc
                            # lift-off: find landing frame (next phase wrap)
                            n0 = math.floor(phase[f] + off)
                            land = None
                            stop = None
                            for h in range(f + 1, min(self.fb, f + 60) + 1):
                                if not M[h]:
                                    stop = h
                                    break
                                if math.floor(phase[h] + off) > n0:
                                    land = h
                                    break
                            if land is not None:
                                a = g["duty"] * GAIT[mode]["L"] * s * 0.5
                                back = -1 if g.get("back") else 1
                                mv = P[land] - P[land - 1]
                                mv.z = 0
                                fdir = mv.normalized() if mv.length > 1e-6 else fwd_vec(Y[land]) * back
                                tgt = P[land] + fdir * a + side_vec(Y[land]) * (lat * sx)
                                st["sw"] = {"from": st["P"].copy(), "fromY": st["Y"], "to": tgt, "toY": Y[land],
                                            "fs": f, "fe": land, "lift": g["lift"] * s * 0.85, "kind": mode}
                            else:
                                h = stop if stop is not None else min(self.fb, f + 8)
                                fe = max(h + 2, f + 6)
                                fe = min(fe, self.fb + 30)
                                tgt = stand(min(h, self.fb), sx)
                                st["sw"] = {"from": st["P"].copy(), "fromY": st["Y"], "to": tgt,
                                            "toY": Y[min(h, self.fb)], "fs": f, "fe": fe, "lift": g["lift"] * s * 0.7,
                                            "kind": mode}
                    else:
                        st["lifted"] = None
                        # stationary: settle step if the stance drifted too far from ideal
                        if st["cool"] > 0:
                            st["cool"] -= 1
                        ideal = stand(f, sx)
                        err = (st["P"] - ideal)
                        err.z = 0
                        yerr = abs(wrap180(st["Y"] - Y[f]))
                        other = feet.get("L" if side == "R" else "R")
                        other_sw = other is not None and other.get(f, {}).get("swing")
                        lock = self.act_at(f)[2] in ("fall", "lie", "dig", "kneel", "kneel_reach", "get_up", "pinned", "sit_up", "sit", "fix", "pickup")
                        if not lock and st["cool"] == 0 and not other_sw and (err.length > 0.24 * s or yerr > 32):
                            # look ahead a few frames for where the body is going
                            h = min(self.fb, f + 6)
                            st["sw"] = {"from": st["P"].copy(), "fromY": st["Y"], "to": stand(h, sx), "toY": Y[h],
                                        "fs": f, "fe": f + 7, "lift": 0.09 * s, "kind": "step"}
                prev_frac = fr
                sw = st["sw"]
                if sw:
                    t = (f - sw["fs"]) / max(1, sw["fe"] - sw["fs"])
                    pos = sw["from"].lerp(sw["to"], smoother(t))
                    pos.z = sw["from"].z + (sw["to"].z - sw["from"].z) * t + sw["lift"] * math.sin(math.pi * t) ** 0.9
                    y = sw["fromY"] + wrap180(sw["toY"] - sw["fromY"]) * smooth(t)
                    if sw["kind"] == "step":
                        pitch = -10 * math.sin(math.pi * t)
                    else:   # continue out of the toe-roll, then dorsiflex for heel strike
                        pitch = -30 * (1 - smooth(t / 0.55)) + 14 * smooth((t - 0.55) / 0.45)
                    out[f] = {"pos": pos, "yaw": y, "pitch": pitch, "swing": True, "contact": None}
                else:
                    pos = st["P"].copy()
                    pitch = 0.0
                    contact = "flat"
                    if mode:
                        g = GAIT[mode]
                        fr2 = (phase[f] + off) % 1.0
                        if fr2 < 0.1 and not g.get("back"):
                            pitch = 14 * (1 - fr2 / 0.1)       # heel strike rolling flat
                            contact = "heel"
                        elif fr2 > g["duty"] - 0.16:
                            pitch = -30 * smooth((fr2 - (g["duty"] - 0.16)) / 0.16)   # toe roll
                            contact = "toe"
                    out[f] = {"pos": pos, "yaw": st["Y"], "pitch": pitch, "swing": False, "contact": contact,
                              "plant": st["P"].copy()}
            feet[side] = out
        self.feet = feet

    # ------------------------------------------------------------ 3) body pose
    def body_pose(self, f):
        a = self.act_at(f)
        i = self.tl.index(a)
        p = self.pose_for(a, f)
        # cross-fade from previous action
        bl = a[3].get("blend", 6)
        if i > 0 and f - a[0] < bl:
            prev = self.tl[i - 1]
            pp = self.pose_for(prev, f, frozen=True)
            p = blend_pose(pp, p, smooth((f - a[0] + 1) / (bl + 1)))
        return p

    def pose_for(self, a, f, frozen=False):
        f0, f1, name, kw = a
        if frozen:
            f = min(f, f1)
        dur = max(1, f1 - f0)
        t = f - f0
        u = clamp(t / dur, 0, 1)
        p = neutral()
        sec = f / 24.0
        rng = random.Random(hash((self.c.name, f0, name)) & 0xffffff)
        ph0 = rng.uniform(0, TAU)
        expr = kw.get("expr")
        # --- breathing + weight shift baseline (alive even when 'still')
        br = math.sin(sec * TAU / kw.get("breath", 3.4) + ph0)
        p["chest"] = (-1.2 * br, 0, 0)
        p["sq"] = 1 + 0.012 * br
        ws = math.sin(sec * TAU / 6.0 + ph0 * 1.7)
        p["hip"] = (0.028 * ws, 0, STAND_DROP + 0.006 * br)
        p["hipr"] = (0, 2.2 * ws, 0)
        p["spine"] = (0, -1.6 * ws, 0)
        p["neck"] = (0.8 * br, 0, 0)
        p["uaL"] = (1.5 * br, 6 + 0.8 * ws, 0)
        p["uaR"] = (1.5 * br, 6 - 0.8 * ws, 0)
        mode = self.M.get(f)
        if name in LOCO:
            self._loco_pose(p, f, name, kw)
        elif name in ("idle", "listen", "stand", "stare"):
            p["face"] = dict(EXPR.get(expr or "neutral", {}))
            if name == "stare":
                p["neck"] = (kw.get("pitch", 0), 0, 0)
        elif name == "talk":
            p["face"] = dict(EXPR.get(expr or "neutral", {}))
            env = self._lip_env(f)
            g = math.sin(t / 9.0 + ph0)
            p["uaR"] = (18 + 16 * g + 25 * env, 12, -10)
            p["faR"] = 55 + 20 * g
            p["hdR"] = (0, 30 * g)
            p["neck"] = (4 * env - 2, 0, 3 * math.sin(t / 13.0))
            p["head"] = (2 * env, 0, 0)
            if kw.get("both_hands"):
                p["uaL"] = (18 - 14 * g + 20 * env, 12, 10)
                p["faL"] = 55 - 18 * g
        elif name == "gasp":
            tf = t
            p["face"] = dict(EXPR.get(expr or "shock", {}))
            p["chest"] = keys(tf, [(0, (0, 0, 0)), (3, (4, 0, 0)), (7, (-12, 0, 0)), (11, (-8, 0, 0)), (40, (-7, 0, 0))])
            p["neck"] = keys(tf, [(0, (0, 0, 0)), (3, (6, 0, 0)), (7, (-14, 0, 0)), (11, (-9, 0, 0))])
            p["uaL"] = keys(tf, [(0, (0, 6, 0)), (3, (5, 8, 0)), (7, (52, 18, 25)), (11, (46, 16, 25))])
            p["uaR"] = keys(tf, [(0, (0, 6, 0)), (3, (5, 8, 0)), (7, (52, 18, 25)), (11, (46, 16, 25))])
            p["faL"] = p["faR"] = keys(tf, [(0, 10), (7, 115), (11, 105)])
            p["sq"] = keys(tf, [(0, 1.0), (3, 0.94), (7, 1.06), (11, 1.0)])
            p["hip"] = (0, 0.03 * smooth(tf / 7), STAND_DROP + keys(tf, [(0, 0), (3, -0.03), (7, 0.01), (11, 0)]))
        elif name == "flinch":
            tf = t
            p["face"] = dict(EXPR.get(expr or "fear", {}))
            p["face"]["squint"] = keys(tf, [(0, 0), (2, 1), (8, 0.6), (14, 0.2)])
            p["chest"] = keys(tf, [(0, (0, 0, 0)), (2, (-14, 0, 6)), (6, (-9, 0, 4)), (14, (-3, 0, 1))])
            p["neck"] = keys(tf, [(0, (0, 0, 0)), (2, (-12, 0, -8)), (8, (2, 0, -4)), (16, (0, 0, 0))])
            p["uaL"] = keys(tf, [(0, (0, 6, 0)), (3, (70, 20, 30)), (10, (60, 18, 28)), (20, (20, 10, 0))])
            p["uaR"] = keys(tf, [(0, (0, 6, 0)), (3, (66, 22, 30)), (10, (58, 18, 28)), (20, (18, 10, 0))])
            p["faL"] = p["faR"] = keys(tf, [(0, 10), (3, 115), (20, 40)])
            p["sq"] = keys(tf, [(0, 1.0), (2, 0.88), (5, 1.05), (9, 0.98), (13, 1.0)])
            p["hip"] = (0, 0.06 * smooth(tf / 3), STAND_DROP - keys(tf, [(0, 0), (2, 0.07), (8, 0.03), (16, 0.0)]))
        elif name == "look_up":
            tf = t
            p["face"] = dict(EXPR.get(expr or "awe", {}))
            p["face"]["look_U"] = 0.9
            p["chest"] = keys(tf, [(0, (0, 0, 0)), (4, (5, 0, 0)), (11, (-14, 0, 0)), (16, (-10, 0, 0))])
            p["neck"] = keys(tf, [(0, (0, 0, 0)), (4, (8, 0, 0)), (11, (-38, 0, 0)), (16, (-32, 0, 0))])
            p["head"] = keys(tf, [(0, (0, 0, 0)), (11, (-8, 0, 0)), (16, (-6, 0, 0))])
            p["uaL"] = p["uaR"] = keys(tf, [(0, (0, 6, 0)), (11, (4, 14, 0)), (16, (3, 11, 0))])
        elif name == "point":
            tf = t
            p["face"] = dict(EXPR.get(expr or "shock", {}))
            p["uaR"] = keys(tf, [(0, (0, 6, 0)), (3, (-14, 10, 0)), (8, (96, 6, 0)), (11, (86, 6, 0)), (14, (90, 6, 0))])
            p["faR"] = keys(tf, [(0, 10), (3, 40), (8, 0), (14, 4)])
            p["chest"] = keys(tf, [(0, (0, 0, 0)), (3, (-3, 0, 6)), (8, (5, 0, -12)), (14, (3, 0, -9))])
            p["neck"] = (0, 0, -8)
        elif name == "slump":
            tf = t
            p["face"] = dict(EXPR.get(expr or "sad", {}))
            w = smooth(tf / 14)
            p["spine"] = (12 * w, 0, 0)
            p["chest"] = (14 * w - 1.6 * br, 0, 0)
            p["neck"] = (22 * w, 0, 0)
            p["uaL"] = (6 * w, 3, 10)
            p["uaR"] = (6 * w, 3, -10)
            p["faL"] = p["faR"] = 5
            p["hip"] = (p["hip"][0] * 0.4, 0.02 * w, STAND_DROP - 0.06 * w)
            p["sq"] = 1 - 0.04 * w + 0.02 * br
        elif name == "cheer":
            tf = t
            p["face"] = dict(EXPR.get(expr or "happy", {}))
            bounce = abs(math.sin(tf / 5.5 * math.pi + ph0))
            p["uaL"] = (160 + 10 * bounce, 18, 0)
            p["uaR"] = (160 + 10 * bounce, 18, 0)
            p["faL"] = p["faR"] = 20
            p["hip"] = (0, 0, STAND_DROP + 0.07 * bounce)
            p["sq"] = 1 + 0.06 * (bounce - 0.5)
            p["chest"] = (-6, 0, 0)
            p["neck"] = (-10, 0, 0)
        elif name in ("pose", "emote", "selfie"):
            # staged 'helping' pose for onlookers: anticipation -> snap to a hero pose -> hold with a smug bob
            tf = t
            kind = kw.get("kind", "thumbs")
            p["face"] = dict(EXPR.get(expr or "smug", {}))
            w = back_out(clamp((tf - 4) / 6, 0, 1), 2.2)
            ant = smooth(tf / 4) * (1 - smooth((tf - 4) / 3))
            if kind == "thumbs":
                p["uaR"] = lerp((-15 * ant, 6, 0), (88, 30, 0), w)
                p["faR"] = lerp(30 * ant, 85, w)
                p["uaL"] = lerp((0, 6, 0), (8, 42, 0), w)
                p["faL"] = lerp(10, 100, w)
                p["hdL"] = (0, -30 * w)
            elif kind == "flex":
                p["uaL"] = lerp((0, 6, 0), (0, 92, 0), w)
                p["uaR"] = lerp((0, 6, 0), (0, 92, 0), w)
                p["faL"] = p["faR"] = lerp(10, 125, w)
            elif kind == "wave_crowd":
                p["uaR"] = lerp((0, 6, 0), (150, 25, 0), w)
                p["faR"] = 25 + 25 * math.sin(tf / 3.0)
                p["uaL"] = lerp((0, 6, 0), (8, 40, 0), w)
                p["faL"] = lerp(10, 100, w)
            elif kind == "selfie":
                p["uaR"] = lerp((0, 6, 0), (115, 30, -20), w)
                p["faR"] = lerp(10, 25, w)
                p["uaL"] = lerp((0, 6, 0), (20, 30, 20), w)
                p["faL"] = lerp(10, 90, w)
                p["neck"] = (0, -10 * w, 12 * w)
            p["chest"] = (-6 * w - 1.2 * br, 0, 8 * w * (1 if kind != "selfie" else -1))
            p["hip"] = (0.05 * w, 0, STAND_DROP + 0.02 * math.sin(tf / 5.0) * w - 0.05 * ant)
            p["hipr"] = (0, 5 * w, 0)
            p["sq"] = 1 - 0.07 * ant + 0.04 * w * (1 - clamp((tf - 10) / 6, 0, 1))
            p["neck"] = (p["neck"][0] - 6 * w, p["neck"][1], p["neck"][2] + 10 * w)
        elif name == "wave":
            p["face"] = dict(EXPR.get(expr or "happy", {}))
            p["uaR"] = (140, 28, 0)
            p["faR"] = 30 + 28 * math.sin(t / 3.2)
        elif name == "whisper":
            sd = kw.get("side", 1)
            p["face"] = dict(EXPR.get(expr or "disgust", {}))
            w = smooth(t / 8)
            p["chest"] = (6 * w, -9 * sd * w, 0)
            p["neck"] = (4 * w, -8 * sd * w, 14 * sd * w)
            key_ = "uaR" if sd > 0 else "uaL"
            p[key_] = (70 * w, 20, 30 * sd)
            p["faR" if sd > 0 else "faL"] = 120 * w
            env = self._lip_env(f)
            p["face"]["mouth_open"] = p["face"].get("mouth_open", 0) + 0.3 * abs(math.sin(t / 2.3)) * w
        elif name == "cross_arms":
            p["face"] = dict(EXPR.get(expr or "wary", {}))
            w = smooth(t / 8)
            p["uaL"] = (48 * w, 14, 55 * w)
            p["uaR"] = (48 * w, 14, -55 * w)
            p["faL"] = p["faR"] = 10 + 110 * w
            p["chest"] = (-5 * w, 0, 0)
        elif name == "offer":
            p["face"] = dict(EXPR.get(expr or "hopeful", {}))
            w = back_out(clamp((t - 3) / 9, 0, 1), 1.4)
            ant = smooth(t / 3) * (1 - smooth((t - 3) / 3))
            p["uaR"] = (-10 * ant + 62 * w, 10, -12 * w)
            p["faR"] = 25 * w
            p["hdR"] = (-30 * w, 70 * w)
            p["chest"] = (7 * w, 0, -5 * w)
            p["neck"] = (-4 * w, 0, 0)
            p["hip"] = (p["hip"][0], -0.04 * w, p["hip"][2])
            if kw.get("withdraw") is not None and t > kw["withdraw"]:
                k = smooth((t - kw["withdraw"]) / 10)
                p["uaR"] = lerp(p["uaR"], (4, 6, 0), k)
                p["faR"] = lerp(p["faR"], 15, k)
                p["chest"] = lerp(p["chest"], (10, 0, 0), k)
                p["neck"] = lerp(p["neck"], (14, 0, 0), k)
                p["face"] = blend_face(p["face"], EXPR["hurt"], k)
        elif name in ("kneel", "kneel_reach", "dig", "fix", "pickup"):
            self._kneel_pose(p, t, name, kw, ph0, br)
        elif name == "hold_pet":
            p["face"] = dict(EXPR.get(expr or "smug", {}))
            p["uaL"] = (52, 14, 40)
            p["uaR"] = (52, 14, -40)
            p["faL"] = p["faR"] = 95
            p["chest"] = (-4 - 1.2 * br, 0, 0)
        elif name == "pet_hug":
            p["face"] = dict(EXPR.get(expr or "fear", {}))
            p["uaL"] = (60, 10, 48)
            p["uaR"] = (60, 10, -48)
            p["faL"] = p["faR"] = 110
            p["chest"] = (10, 0, 0)
            p["neck"] = (14, 0, 0)
        elif name == "panic":
            p["face"] = dict(EXPR.get(expr or "scream", {}))
            j = math.sin(t * 1.7 + ph0)
            k2 = math.sin(t * 2.3 + ph0 * 2)
            p["uaL"] = (150 + 25 * j, 25, 0)
            p["uaR"] = (145 - 25 * k2, 25, 0)
            p["faL"] = 30 + 20 * k2
            p["faR"] = 30 + 20 * j
            p["chest"] = (-6, 4 * j, 10 * k2)
            p["neck"] = (-12 + 8 * j, 0, 30 * math.sin(t / 7.0 + ph0))
            p["hip"] = (0.03 * j, 0, STAND_DROP - 0.03)
        elif name == "look_around":
            p["face"] = dict(EXPR.get(expr or "fear", {}))
            sc = math.sin(t / 10.0 + ph0)
            p["neck"] = (-4, 0, 38 * sc)
            p["chest"] = (0, 0, 10 * sc)
            p["face"]["look_L" if sc > 0 else "look_R"] = abs(sc) * 0.8
        elif name == "hug":
            p["face"] = dict(EXPR.get(expr or "tender", {}))
            w = smooth(t / 10)
            low = kw.get("low", 0.0)
            p["uaL"] = (72 * w + 20 * low, 16, 52 * w)
            p["uaR"] = (72 * w + 20 * low, 16, -52 * w)
            p["faL"] = p["faR"] = 10 + 70 * w
            p["chest"] = (8 * w + 18 * low, 0, 0)
            p["spine"] = (10 * low * w, 0, 0)
            p["neck"] = (10 * w, 0, 8 * w)
            p["hip"] = (p["hip"][0], 0, STAND_DROP - 0.12 * low * w)
        elif name == "take_hand":
            p["face"] = dict(EXPR.get(expr or "tender", {}))
            sd = kw.get("side", -1)
            w = smooth(t / 10)
            key_, fk = ("uaR", "faR") if sd < 0 else ("uaL", "faL")
            p[key_] = (24 * w, 18 * w, 0)
            p[fk] = 18
            p["neck"] = (12 * w * kw.get("look_down", 1), 0, -12 * sd * w)
        elif name in ("shove", "slam"):
            tf = t
            p["face"] = dict(EXPR.get(expr or "angry", {}))
            w = keys(tf, [(0, 0.0), (4, -0.4), (7, 1.0), (10, 1.15), (18, 0.6), (26, 0.2)])
            if name == "slam":
                p["uaR"] = (110 * max(0, w) - 25 * min(0, w) * -1, 10, 0)
                p["faR"] = 30
                p["chest"] = (10 * w, 0, -12 * w)
            else:
                p["uaL"] = (85 * w + 5, 12, 0)
                p["uaR"] = (85 * w + 5, 12, 0)
                p["faL"] = p["faR"] = 20 + 40 * (1 - clamp(w, 0, 1))
                p["chest"] = (14 * w, 0, 0)
            p["hip"] = (0, -0.12 * w, STAND_DROP - 0.04 * abs(w))
            p["sq"] = 1 + 0.06 * min(w, 0) - 0.03 * max(0, w - 1)
        elif name == "shoved":
            tf = t
            p["face"] = dict(EXPR.get(expr or "pain", {}))
            p["chest"] = keys(tf, [(0, (0, 0, 0)), (2, (18, 0, 8)), (6, (6, 0, -6)), (12, (12, 0, 0)), (20, (8, 0, 0))])
            p["neck"] = keys(tf, [(0, (0, 0, 0)), (2, (-20, 0, 0)), (6, (10, 0, 6)), (14, (12, 0, 0))])
            p["uaL"] = keys(tf, [(0, (0, 6, 0)), (3, (-30, 60, 0)), (8, (40, 40, 0)), (16, (10, 10, 0))])
            p["uaR"] = keys(tf, [(0, (0, 6, 0)), (3, (-40, 55, 0)), (8, (50, 35, 0)), (16, (12, 10, 0))])
            p["faL"] = p["faR"] = keys(tf, [(0, 10), (3, 30), (8, 70), (16, 20)])
            p["sq"] = keys(tf, [(0, 1.0), (2, 0.86), (5, 1.06), (9, 1.0)])
            p["hip"] = (0, 0, STAND_DROP + keys(tf, [(0, 0.0), (3, -0.07), (9, -0.1), (18, -0.04)]))
        elif name in ("fall", "lie"):
            self._fall_pose(p, t, name, kw, br)
        elif name == "get_up":
            self._getup_pose(p, t, dur, kw, br)
        elif name in ("lift", "lift_beam"):
            self._lift_pose(p, t, dur, kw, ph0, br)
        elif name == "pinned":
            # lying on back under rubble, one arm free, reaching
            p["legik"] = 0.0
            p["hipr"] = (-86, 0, 0)
            p["hip"] = (0, 0.0, -0.73)
            p["thL"] = p["thR"] = (0, 0)
            p["shL"] = p["shR"] = 0
            reach = math.sin(t / 11.0 + ph0)
            p["uaR"] = (150 + 15 * reach, 25, 0)
            p["faR"] = 20 + 15 * reach
            p["uaL"] = (10, 40, 0)
            p["neck"] = (-25 + 6 * reach, 0, 14 * math.sin(t / 17.0))
            p["face"] = dict(EXPR.get(expr or "fear", {}))
        elif name == "sit_up":
            w = smooth(t / max(8, dur))
            p["legik"] = 0.0
            p["hipr"] = (lerp(-86, -10, w), 0, 0)
            p["hip"] = (0, lerp(0.0, 0.1, w), lerp(-0.73, -0.62, w))
            p["thL"] = p["thR"] = (lerp(0, 78, w), 6)
            p["shL"] = p["shR"] = lerp(0, 10, w)
            p["face"] = dict(EXPR.get(expr or "awe", {}))
            p["uaL"] = p["uaR"] = (lerp(10, 20, w), 14, 0)
        elif name == "brace":
            p["face"] = dict(EXPR.get(expr or "fear", {}))
            p["uaL"] = (80, 25, 35)
            p["uaR"] = (80, 25, -35)
            p["faL"] = p["faR"] = 120
            p["neck"] = (18, 0, 0)
            p["chest"] = (16, 0, 0)
            p["hip"] = (0, 0, STAND_DROP - 0.18)
            p["sq"] = 0.93
        elif name == "reach":
            p["face"] = dict(EXPR.get(expr or "determined", {}))
            w = back_out(clamp(t / 10, 0, 1), 1.3)
            p["uaR"] = (80 * w, 10, -6 * w)
            p["faR"] = 10
            p["uaL"] = (40 * w, 30, 0)
            p["chest"] = (16 * w, 0, -8 * w)
            p["hip"] = (0, -0.05 * w, STAND_DROP - 0.05 * w)
        elif name == "tremble":
            p["face"] = dict(EXPR.get(expr or "hurt", {}))
            j = math.sin(t * 2.9) * 0.6 + math.sin(t * 4.1) * 0.4
            p["chest"] = (6 + 1.5 * j, 0, 0)
            p["neck"] = (10 + 2 * j, 0, 0)
            p["uaL"] = (6, 4, 8)
            p["uaR"] = (6, 4, -8)
        elif name == "hands_mouth":
            p["face"] = dict(EXPR.get(expr or "shock", {}))
            w = back_out(clamp(t / 8, 0, 1), 1.4)
            p["uaL"] = (62 * w, 24, 32 * w)
            p["uaR"] = (62 * w, 24, -32 * w)
            p["faL"] = p["faR"] = 10 + 118 * w
            p["chest"] = (-8 * w, 0, 0)
            p["neck"] = (6 * w, 0, 0)
        elif name in ("mock", "laugh"):
            p["face"] = dict(EXPR.get(expr or "happy", {}))
            hh = abs(math.sin(t / 3.0 + ph0))
            p["chest"] = (-10 + 8 * hh, 0, 0)
            p["neck"] = (-14 + 8 * hh, 0, 0)
            p["face"]["mouth_open"] = 0.4 + 0.4 * hh
            p["uaL"] = (30, 25, 30)
            p["faL"] = 100
            if name == "mock":
                p["uaR"] = (90, 6, 0)
                p["faR"] = 8
                p["hdR"] = (0, 0)
            p["sq"] = 1 + 0.03 * (hh - 0.5)
        elif name == "turn":
            p["face"] = dict(EXPR.get(expr or "neutral", {}))
        elif name == "sit":
            w = smooth(t / 10) if not kw.get("seated") else 1.0
            p["legik"] = 1 - w
            sw = 6 * math.sin(sec * TAU / 5.0 + ph0) * kw.get("swing", 0)
            p["thL"] = (86 * w, 5)
            p["thR"] = (86 * w, 5)
            p["shL"] = 84 * w + sw
            p["shR"] = 84 * w - sw
            p["hip"] = (0, 0.1 * w, lerp(STAND_DROP, -0.24, w))
            sl = kw.get("slump", 0.0)
            p["spine"] = (10 * sl * w, 0, 0)
            p["chest"] = (8 * sl * w - 1.2 * br, 0, 0)
            p["neck"] = (12 * sl * w + 0.8 * br, 0, 0)
            p["uaL"] = (lerp(0, 34, w), 8, 6)
            p["uaR"] = (lerp(0, 34, w), 8, -6)
            p["faL"] = p["faR"] = lerp(10, 42, w)
            p["face"] = dict(EXPR.get(expr or "neutral", {}))
        elif name == "give":
            p["face"] = dict(EXPR.get(expr or "tender", {}))
            w = back_out(clamp(t / 10, 0, 1), 1.3)
            p["uaR"] = p["uaL"] = (55 * w, 10, 0)
            p["faR"] = p["faL"] = 25
            p["chest"] = (10 * w, 0, 0)
            p["hip"] = (0, 0, STAND_DROP - 0.08 * w)
        else:
            p["face"] = dict(EXPR.get(expr or "neutral", {}))
        # generic expression override / sequence: kw["exprs"] = [[t_frames, expr], ...]
        if kw.get("exprs"):
            seq = kw["exprs"]
            cur = None
            nxt = None
            for k, (tt, ee) in enumerate(seq):
                if t >= tt:
                    cur = (tt, ee)
                    nxt = seq[k + 1] if k + 1 < len(seq) else None
            if cur:
                base = dict(EXPR.get(cur[1], {}))
                if nxt and t > nxt[0] - 4:
                    base = blend_face(base, EXPR.get(nxt[1], {}), smooth((t - (nxt[0] - 4)) / 4))
                p["face"] = base
        return p

    def _loco_pose(self, p, f, name, kw):
        g = GAIT[name]
        ph = self.phase[f]
        c = math.cos(TAU * ph)
        sp = self.SP[f] / max(1e-6, g["v"] * self.c.s)
        sp = clamp(sp, 0, 1.4)
        mv = clamp(sp * 1.5, 0, 1)
        acc = (self.SP[f] - self.SP.get(f - 1, self.SP[f])) * 24 / max(1, g["v"])
        A = g["arm"] * mv
        p["uaL"] = (-A * c, 8 + (6 if name in ("run", "sprint", "panic_sprint") else 0), 0)
        p["uaR"] = (A * c, 8 + (6 if name in ("run", "sprint", "panic_sprint") else 0), 0)
        if name in ("run", "sprint", "panic_sprint"):
            p["faL"] = 75 + 15 * c
            p["faR"] = 75 - 15 * c
        else:
            p["faL"] = 14 + 10 * max(0, -c)
            p["faR"] = 14 + 10 * max(0, c)
        duty = g["duty"]
        if name in ("run", "sprint", "panic_sprint", "stagger"):
            bob = -g["bob"] * math.cos(4 * math.pi * (ph - duty / 2))
        else:
            bob = -g["bob"] * math.cos(4 * math.pi * ph)
        sway = 0.022 * math.cos(TAU * ph) * (1 if name not in ("run", "sprint") else 0.5)
        p["hip"] = (sway * mv, 0, g["drop"] * mv + STAND_DROP * (1 - mv) + bob * mv)
        p["hipr"] = (0, 0, 7 * c * mv)
        lean = g["lean"] * mv + clamp(acc * 2.0, -6, 10)
        p["spine"] = (lean * 0.5, 0, -5 * c * mv)
        p["chest"] = (lean * 0.5, 0, -4 * c * mv)
        p["neck"] = (-lean * 0.55, 0, 2 * c * mv)
        p["sq"] = 1 + (0.03 * math.cos(4 * math.pi * (ph - duty / 2)) * mv if name in ("run", "sprint", "panic_sprint") else 0)
        expr = kw.get("expr")
        p["face"] = dict(EXPR.get(expr or ({"panic_sprint": "scream", "sprint": "determined", "back_away": "fear",
                                              "drag": "strain", "sad_walk": "lonely"}.get(name, "neutral")), {}))
        if name == "panic_sprint":
            j = math.sin(f * 0.9 + hash(self.c.name) % 7)
            p["uaL"] = (150 + 20 * j, 30, 0)
            p["uaR"] = (140 - 20 * j, 30, 0)
            p["faL"] = p["faR"] = 40
            p["neck"] = (-14, 0, 20 * math.sin(f / 9.0))
        if name == "back_away":
            p["uaL"] = (40, 20, 20)
            p["uaR"] = (40, 20, -20)
            p["faL"] = p["faR"] = 90
        if name == "drag":
            p["uaL"] = (62, 10, 8)
            p["uaR"] = (62, 10, -8)
            p["faL"] = p["faR"] = 10
            p["spine"] = (22, 0, -4 * c)
            p["chest"] = (14, 0, -3 * c)
            p["neck"] = (-24, 0, 0)
        if name == "carry_walk":
            p["uaL"] = (55, 14, 30)
            p["uaR"] = (55, 14, -30)
            p["faL"] = p["faR"] = 80
            p["chest"] = (-6, 0, -3 * c)
        if kw.get("carry_pet"):
            p["uaL"] = (52, 14, 40)
            p["uaR"] = (52, 14, -40)
            p["faL"] = p["faR"] = 95
        # stumble overlay: kw["stumble"] = frame offset within the action
        st = kw.get("stumble")
        if st is not None:
            tt = f - (self.act_at(f)[0] + st)
            if 0 <= tt <= 16:
                w = keys(tt, [(0, 0.0), (3, 1.0), (8, 0.7), (16, 0.0)])
                add(p, "spine", (22 * w, 0, 6 * w))
                add(p, "chest", (10 * w, 0, 0))
                add(p, "hip", (0, 0, -0.12 * w))
                p["uaL"] = lerp(p["uaL"], (70, 60, 0), w)
                p["uaR"] = lerp(p["uaR"], (30, 70, 0), w)
                p["sq"] = p["sq"] - 0.06 * w
                p["face"] = blend_face(p["face"], EXPR["shock"], w)

    def _kneel_pose(self, p, t, name, kw, ph0, br):
        w = smooth(t / 9)
        p["legik"] = 1 - w
        # kneel on right knee, left foot planted
        p["thL"] = (lerp(0, 70, w), 4)
        p["shL"] = lerp(0, 70, w)
        p["thR"] = (lerp(0, -6, w), 4)
        p["shR"] = lerp(0, 95, w)
        p["hip"] = (0, lerp(0, 0.06, w), lerp(STAND_DROP, -0.42, w))
        p["face"] = dict(EXPR.get(kw.get("expr") or ("strain" if name == "dig" else "tender" if name == "kneel_reach" else "determined"), {}))
        if name == "kneel":
            p["spine"] = (6 * w, 0, 0)
        elif name == "kneel_reach":
            k = back_out(clamp((t - 6) / 10, 0, 1), 1.3)
            p["spine"] = (14 * w, 0, 0)
            p["uaR"] = (70 * k, 8, -10 * k)
            p["faR"] = 15
            p["neck"] = (8 * w, 0, 0)
        elif name in ("dig", "pickup"):
            sp = kw.get("rate", 9.0)
            sL = math.sin(t / sp * TAU + ph0)
            sR = math.sin(t / sp * TAU + ph0 + math.pi * 0.8)
            p["spine"] = (28 * w, 0, 6 * sL * w)
            p["chest"] = (16 * w, 0, 8 * sL * w)
            p["neck"] = (-12 * w, 0, 0)
            p["uaL"] = (lerp(0, 55 + 30 * sL, w), 18, 10)
            p["uaR"] = (lerp(0, 55 + 30 * sR, w), 18, -10)
            p["faL"] = 20 + 50 * max(0, -sL)
            p["faR"] = 20 + 50 * max(0, -sR)
            p["sq"] = 1 - 0.04 * abs(sL) * w
            if kw.get("toss"):
                p["uaR"] = (lerp(0, 95 + 50 * max(0, sR), w), 18, -10)
        elif name == "fix":
            hm = abs(math.sin(t / 5.0 * math.pi))
            p["spine"] = (30 * w, 0, 0)
            p["chest"] = (12 * w, 0, 0)
            p["neck"] = (-6 * w, 0, 0)
            p["uaR"] = (lerp(0, 60 + 40 * hm, w), 10, -10)
            p["faR"] = 30 + 50 * hm
            p["uaL"] = (lerp(0, 50, w), 20, 15)
            p["faL"] = 30

    def _fall_pose(self, p, t, name, kw, br):
        if name == "lie":
            t = 999
        tf = t
        # anticipation (6f): arms up, lean back; then pivot over the feet to the ground; impact squash
        th = keys(tf, [(0, 0.0), (5, -6.0), (14, 60.0), (18, 86.0), (21, 82.0), (25, 84.0)])
        L = 0.95
        th_r = math.radians(max(0, th))
        p["legik"] = keys(tf, [(0, 1.0), (6, 1.0), (12, 0.0)])
        lay = clamp((th - 40) / 46, 0, 1)
        p["hipr"] = (th, 0, 0)
        p["hip"] = (0, -L * math.sin(th_r) * 0.92, lerp(STAND_DROP, -0.73, smooth(lay)) if th > 0 else STAND_DROP)
        p["thL"] = (keys(tf, [(0, 0), (10, -20), (18, 6)]), 4)
        p["thR"] = (keys(tf, [(0, 0), (10, 25), (18, 2)]), 4)
        p["shL"] = keys(tf, [(0, 0), (10, 30), (18, 12)])
        p["shR"] = keys(tf, [(0, 0), (10, 10), (18, 20)])
        p["uaL"] = keys(tf, [(0, (0, 6, 0)), (5, (140, 30, 0)), (14, (150, 30, 0)), (18, (165, 40, 0)), (25, (160, 35, 0))])
        p["uaR"] = keys(tf, [(0, (0, 6, 0)), (5, (130, 30, 0)), (14, (140, 30, 0)), (18, (150, 40, 0)), (25, (148, 35, 0))])
        p["faL"] = p["faR"] = keys(tf, [(0, 10), (14, 30), (18, 70), (25, 60)])
        p["neck"] = keys(tf, [(0, (0, 0, 0)), (14, (-30, 0, 0)), (18, (-45, 0, 0)), (22, (-38, 0, 0))])
        p["sq"] = keys(tf, [(0, 1.0), (17, 1.0), (18, 0.82), (20, 1.05), (23, 1.0)])
        p["hsq"] = keys(tf, [(0, 1.0), (18, 1.0), (19, 0.88), (22, 1.0)])
        p["face"] = dict(EXPR.get(kw.get("expr") or ("shock" if tf < 18 else "pain"), {}))
        if tf > 18:
            p["face"]["squint"] = keys(tf, [(18, 1.0), (30, 0.6)])

    def _getup_pose(self, p, t, dur, kw, br):
        # prone -> push-up -> kneel -> stand (with a stagger of effort)
        tf = t
        k1 = smooth(tf / (dur * 0.35))
        k2 = smooth((tf - dur * 0.3) / (dur * 0.35))
        k3 = smooth((tf - dur * 0.62) / (dur * 0.38))
        th = lerp(lerp(84, 40, k1), lerp(40, 0, k3), k2 * 0 + k3) if k3 > 0 else lerp(84, 40, k1)
        th_r = math.radians(th)
        p["legik"] = smooth((tf - dur * 0.7) / (dur * 0.3))
        p["hipr"] = (th, 0, 0)
        p["hip"] = (0, -0.92 * 0.95 * math.sin(th_r) * (1 - k2 * 0.6), lerp(-0.73, lerp(-0.5, STAND_DROP, k3), max(k1 * 0.5, k2)))
        p["thL"] = (lerp(6, 85, k2) * (1 - k3), 6)
        p["thR"] = (lerp(2, 10, k2) * (1 - k3), 4)
        p["shL"] = lerp(12, 95, k2) * (1 - k3)
        p["shR"] = lerp(20, 80, k1) * (1 - k3)
        push = keys(tf, [(0, 0.0), (dur * 0.3, 1.0), (dur * 0.65, 0.6), (dur, 0.0)])
        p["uaL"] = (lerp(150, 75, k1) * (1 - k3) + 6 * k3, 20, 0)
        p["uaR"] = (lerp(140, 75, k1) * (1 - k3) + 6 * k3, 20, 0)
        p["faL"] = p["faR"] = 20 + 40 * push
        p["neck"] = (-30 * (1 - k3), 0, 0)
        p["face"] = dict(EXPR.get(kw.get("expr") or "strain", {}))
        p["sq"] = 1 - 0.04 * push

    def _lift_pose(self, p, t, dur, kw, ph0, br):
        # squat (anticipation) -> grip -> strain up with tremor -> hold overhead/at chest
        grip = kw.get("grip", 0.3) * dur
        up = kw.get("up", 0.75) * dur
        k0 = smooth(t / max(6, grip))
        k1 = smooth((t - grip) / max(6, up - grip))
        trem = (math.sin(t * 2.7) * 0.6 + math.sin(t * 4.3) * 0.4) * (k0 - k1 * 0.5)
        drop = lerp(lerp(STAND_DROP, -0.36, k0), -0.08, k1)
        p["hip"] = (0.01 * trem, 0.04 * k0, drop)
        p["spine"] = (lerp(0, 30, k0) * (1 - k1) + 6 * k1, 0, 0)
        p["chest"] = (lerp(0, 18, k0) * (1 - k1) - 4 * k1 + 1.5 * trem, 0, 0)
        p["neck"] = (lerp(0, -20, k0) * (1 - k1) - 10 * k1, 0, 0)
        hi = kw.get("height", 0.5)
        p["uaL"] = (lerp(lerp(0, 72, k0), 70 + 60 * hi, k1) + 2 * trem, 16, 12)
        p["uaR"] = (lerp(lerp(0, 72, k0), 70 + 60 * hi, k1) - 2 * trem, 16, -12)
        p["faL"] = p["faR"] = lerp(lerp(10, 15, k0), 30 + 40 * (1 - hi), k1)
        p["face"] = dict(EXPR.get(kw.get("expr") or "strain", {}))
        if k1 > 0.9 and kw.get("relief"):
            p["face"] = blend_face(p["face"], EXPR["determined"], smooth((k1 - 0.9) / 0.1))
        p["sq"] = 1 - 0.05 * k0 * (1 - k1) + 0.02 * trem

    # ------------------------------------------------------------ helpers
    def _lip_env(self, f):
        L = self.c.lips
        if not L:
            return 0.0
        for fr, o, w, r in L:
            if fr == f:
                return o
        return 0.0

    # ------------------------------------------------------------ 4) face
    def face_tracks(self, poses):
        c = self.c
        rng = self.rng
        frames = self.frames
        W = {k: [0.0] * len(frames) for k in FACE_KEYS}
        lips = {fr: (o, w, r) for fr, o, w, r in c.lips}
        # blinks: every 2-5 s, plus on big head turns; 4 frame asymmetric blink
        next_blink = self.fa + rng.randint(6, 40)
        blinks = []
        prev_y = self.Y[self.fa]
        for i, f in enumerate(frames):
            dy = abs(wrap180(self.Y[f] - prev_y))
            prev_y = self.Y[f]
            if f >= next_blink or (dy > 6 and (not blinks or f - blinks[-1] > 10)):
                blinks.append(f)
                next_blink = f + rng.randint(48, 120)
        # saccades
        sac = []
        f = self.fa
        cur = (0.0, 0.0)
        while f <= self.fb:
            sac.append((f, cur))
            cur = (rng.uniform(-0.35, 0.35), rng.uniform(-0.25, 0.2))
            f += rng.randint(14, 40)
        for i, f in enumerate(frames):
            p = poses[i]
            for k, v in p["face"].items():
                if k in W:
                    W[k][i] = v
            # eye darts (saccade = instant 2-frame move)
            sx, sy = 0.0, 0.0
            for (fs, v), nxt in zip(sac, sac[1:] + [(10 ** 9, (0, 0))]):
                if fs <= f < nxt[0]:
                    pv = sac[sac.index((fs, v)) - 1][1] if sac.index((fs, v)) > 0 else v
                    u = clamp((f - fs) / 2.0, 0, 1)
                    sx, sy = lerp(pv[0], v[0], u), lerp(pv[1], v[1], u)
            lx, ly = p.get("look", (0, 0))
            sx += lx
            sy += ly
            if sx > 0:
                W["look_L"][i] = clamp(W["look_L"][i] + sx, 0, 1)
            else:
                W["look_R"][i] = clamp(W["look_R"][i] - sx, 0, 1)
            if sy > 0:
                W["look_U"][i] = clamp(W["look_U"][i] + sy, 0, 1)
            else:
                W["look_D"][i] = clamp(W["look_D"][i] - sy, 0, 1)
            # blink
            b = 0.0
            for bf in blinks:
                d = f - bf
                if 0 <= d <= 4:
                    b = max(b, (0.6, 1.0, 1.0, 0.55, 0.15)[d])
            W["blink_L"][i] = max(W["blink_L"][i], b)
            W["blink_R"][i] = max(W["blink_R"][i], b)
            # lip-sync (additive over expression)
            if f in lips:
                o, wd, rd = lips[f]
                W["mouth_open"][i] = clamp(W["mouth_open"][i] * 0.4 + o, 0, 1.1)
                W["mouth_wide"][i] = clamp(W["mouth_wide"][i] * 0.6 + wd * o, 0, 1)
                W["mouth_O"][i] = clamp(W["mouth_O"][i] * 0.6 + rd * o, 0, 1)
                W["smile"][i] *= 0.7
        return W

    # ------------------------------------------------------------ 5) run + bake
    def run(self):
        self.solve_root()
        self.solve_feet()
        c = self.c
        ao = c.arm
        s = c.s
        frames = self.frames
        poses = [self.body_pose(f) for f in frames]
        # look-at overlay (head + eyes lead)
        tracks = {}
        for i, f in enumerate(frames):
            a = self.act_at(f)
            look = a[3].get("look_at")
            if look is None:
                continue
            tgt = self.look_tracks.get(look) if isinstance(look, str) else look
            if isinstance(tgt, dict):
                tgt = tgt.get(f) or tgt.get(min(tgt, key=lambda k: abs(k - f)))
            if tgt is None:
                continue
            P = self.P[f] + Vector((0, 0, 2.1 * s))
            d = Vector(tgt) - P
            yaw_rel = wrap180(yaw_to(d.x, d.y) - self.Y[f])
            pitch = -math.degrees(math.atan2(d.z, max(0.1, Vector((d.x, d.y)).length)))
            yaw_rel = clamp(yaw_rel, -70, 70)
            pitch = clamp(pitch, -45, 35)
            p = poses[i]
            w = smooth((f - a[0]) / 6.0)
            p["neck"] = (p["neck"][0] + pitch * 0.55 * w, p["neck"][1], p["neck"][2] + yaw_rel * 0.6 * w)
            p["chest"] = (p["chest"][0], p["chest"][1], p["chest"][2] + yaw_rel * 0.25 * w)
            p["look"] = (clamp(-yaw_rel / 60, -0.8, 0.8), clamp(-pitch / 40, -0.8, 0.8))
        # secondary motion: hair pivot lags head angular velocity (spring-damper)
        hair = []
        hv, hx = 0.0, 0.0
        hv2, hx2 = 0.0, 0.0
        prev = None
        for i, f in enumerate(frames):
            p = poses[i]
            hd = p["neck"][0] + p["chest"][0] + p["spine"][0] + p["hipr"][0]
            hz = p["neck"][2] + p["chest"][2] + self.Y[f]
            if prev is None:
                prev = (hd, hz)
            drive, drive2 = (hd - prev[0]), wrap180(hz - prev[1])
            prev = (hd, hz)
            hv += -0.35 * hx - 0.28 * hv - drive * 0.9
            hx += hv
            hv2 += -0.35 * hx2 - 0.28 * hv2 - drive2 * 0.5
            hx2 += hv2
            hair.append((clamp(hx, -14, 14), clamp(hx2, -12, 12)))
        # ---- bake channels
        ch = {}

        def put(bone, kind, val):
            ch.setdefault((bone, kind), []).append(val)

        def q_char(bone, e):
            q = Euler((math.radians(e[0]), math.radians(e[1]), math.radians(e[2])), 'XYZ').to_quaternion()
            R = c.rest3[bone]
            Rq = R.to_quaternion()
            return Rq.inverted() @ q @ Rq

        def loc_unparented(bone, world, rotq=None):
            head = c.rest[bone].translation
            v = Vector(world) / s - head
            return c.rest3[bone].transposed() @ v

        def loc_child(bone, d):
            return c.rest3[bone].transposed() @ Vector(d)

        foot_hist = {"L": [], "R": []}
        for i, f in enumerate(frames):
            p = poses[i]
            P = self.P[f]
            Yw = self.Y[f]
            # root
            put("root", "loc", loc_unparented("root", P))
            put("root", "rot", Euler((0, 0, math.radians(Yw))).to_quaternion())
            # hips: clamp height for IK reach
            hx_, hy_, hz_ = p["hip"]
            legik = p["legik"]
            if legik > 0.5:
                for side, sx in (("L", 1), ("R", -1)):
                    ft = self.feet[side][f]["pos"]
                    hipj = P + (side_vec(Yw) * (0.19 * sx + hx_) + fwd_vec(Yw) * (-hy_)) * s
                    hj = Vector((hipj.x, hipj.y, 0))
                    h = (Vector((ft.x, ft.y, 0)) - hj).length
                    reach = LEG_LEN * s * 0.985
                    if h >= reach:
                        self.report["overreach"] += 1
                        maxz = (ft.z + 0.11 * s + 0.02 * s - P.z) / s - HIPJ
                    else:
                        maxz = (ft.z + 0.11 * s + math.sqrt(reach * reach - h * h) - P.z) / s - HIPJ
                    if hz_ > maxz:
                        hz_ = maxz
            put("hips", "loc", loc_child("hips", (hx_, hy_, hz_)))
            put("hips", "rot", q_char("hips", p["hipr"]))
            sq = p["sq"]
            put("spine", "rot", q_char("spine", p["spine"]))
            put("spine", "scl", (1 / math.sqrt(sq), sq, 1 / math.sqrt(sq)))
            put("chest", "rot", q_char("chest", p["chest"]))
            put("neck", "rot", q_char("neck", p["neck"]))
            hs = p["hsq"]
            put("head", "rot", q_char("head", p["head"]))
            put("head", "scl", (1 / math.sqrt(hs), hs, 1 / math.sqrt(hs)))
            put("hairpivot", "rot", q_char("hairpivot", (hair[i][0], 0, hair[i][1])))
            for side, sx in (("L", 1), ("R", -1)):
                fw, out, tw = p["ua" + side]
                e = (-fw, -out * sx, tw * sx * 0 + tw)
                q = Euler((0, math.radians(-out * sx), 0)).to_quaternion()
                q = Euler((math.radians(-fw), 0, 0)).to_quaternion() @ q
                q = q @ Euler((0, 0, math.radians(tw))).to_quaternion()
                R = c.rest3[f"upperarm_{side}"].to_quaternion()
                put(f"upperarm_{side}", "rot", R.inverted() @ q @ R)
                put(f"forearm_{side}", "rot", q_char(f"forearm_{side}", (-p["fa" + side], 0, 0)))
                hp, hr = p["hd" + side]
                put(f"hand_{side}", "rot", q_char(f"hand_{side}", (-hp, 0, hr)))
                th, tho = p["th" + side]
                put(f"thigh_{side}", "rot", q_char(f"thigh_{side}", (-th, 0, 0)) @ q_char(f"thigh_{side}", (0, -tho * sx, 0)))
                put(f"shin_{side}", "rot", q_char(f"shin_{side}", (p["sh" + side], 0, 0)))
                ft = self.feet[side][f]
                fpos = ft["pos"].copy()
                pitch = ft["pitch"]
                yw = ft["yaw"]
                # pivot heel/toe so the contact point stays put
                toe = 0.2 * s
                heel = 0.06 * s
                fv = fwd_vec(yw)
                pr = math.radians(pitch)
                if pitch < 0:      # toe roll: ankle rotates up about the toe
                    tp = fpos + fv * toe
                    off = -fv * (toe * math.cos(-pr)) + Vector((0, 0, toe * math.sin(-pr)))
                    fpos = tp + off
                elif pitch > 0 and not ft["swing"]:   # heel strike: rotate about the heel
                    hp_ = fpos - fv * heel
                    off = fv * (heel * math.cos(pr)) + Vector((0, 0, heel * math.sin(pr)))
                    fpos = hp_ + off
                fpos.z += 0.11 * s
                put(f"footik_{side}", "loc", loc_unparented(f"footik_{side}", fpos))
                qf = Euler((0, 0, math.radians(yw))).to_quaternion() @ Euler((math.radians(-pitch), 0, 0)).to_quaternion()
                Rf = c.rest3[f"footik_{side}"].to_quaternion()
                put(f"footik_{side}", "rot", Rf.inverted() @ qf @ Rf)
                put(f"shin_{side}", "ik", legik)
                put(f"foot_{side}", "fr", legik)
                put(f"forearm_{side}", "ik", p["armik" + side])
        # write
        for (bone, kind), vals in ch.items():
            pb = ao.pose.bones[bone]
            if kind == "loc":
                path, n = f'pose.bones["{bone}"].location', 3
            elif kind == "rot":
                path, n = f'pose.bones["{bone}"].rotation_quaternion', 4
                # keep quaternion hemisphere continuous
                fixed = [vals[0]]
                for q in vals[1:]:
                    fixed.append(-q if fixed[-1].dot(q) < 0 else q)
                vals = fixed
            elif kind == "scl":
                path, n = f'pose.bones["{bone}"].scale', 3
            elif kind == "ik":
                path, n = f'pose.bones["{bone}"].constraints["IK"].influence', 1
            elif kind == "fr":
                path, n = f'pose.bones["{bone}"].constraints["FOOTROT"].influence', 1
            for k in range(n):
                vv = [float(v[k]) if n > 1 else float(v) for v in vals]
                bake_curve(ao, path, k if n > 1 else -1, frames, vv)
        W = self.face_tracks(poses)
        keyd = c.face.data.shape_keys
        for k, vals in W.items():
            bake_curve(keyd, f'key_blocks["{k}"].value', -1, frames, [clamp(v, 0, 1.2) for v in vals])
        self.c.solved = {"P": self.P, "Y": self.Y, "feet": self.feet, "report": self.report}


def blend_face(a, b, u):
    ks = set(a) | set(b)
    return {k: lerp(a.get(k, 0.0), b.get(k, 0.0), u) for k in ks}


def _trapezoid(u, acc, dec, start_moving=False):
    """Normalised distance for a trapezoidal speed profile (ease-in accel, ease-out decel)."""
    a = 0.0 if start_moving else max(1e-4, acc)
    d = max(1e-4, dec) if dec > 0 else 0.0
    # integrate speed shape numerically (cheap, robust)
    def v(x):
        w = 1.0
        if a > 1e-3 and x < a:
            w = smooth(x / a)
        if d > 1e-3 and x > 1 - d:
            w = min(w, smooth((1 - x) / d))
        return w
    N = 60
    tot = sum(v((k + 0.5) / N) for k in range(N)) / N
    n = int(u * N)
    acc_ = sum(v((k + 0.5) / N) for k in range(n)) / N + v((n + 0.5) / N) * (u * N - n) / N
    return clamp(acc_ / tot, 0, 1)


def _along(pts, segs, s):
    for i, L in enumerate(segs):
        if s <= L or i == len(segs) - 1:
            return pts[i].lerp(pts[i + 1], clamp(s / max(1e-6, L), 0, 1))
        s -= L
    return pts[-1].copy()


# =================================================================== QA CHECK
def check(chars, f0, f1, step=1):
    """Evaluate the posed rigs after IK and report animation faults.
    Returns {"slide_cm_max", "slides", "penetrations", "overlaps", "pops", "overreach"}."""
    scn = bpy.context.scene
    hist = {c.name: {"L": [], "R": []} for c in chars}
    roots = {c.name: [] for c in chars}
    rots = {c.name: [] for c in chars}
    res = {"slide_cm_max": 0.0, "slides": 0, "penetrations": 0, "overlaps": 0, "pops": 0, "overreach": 0,
           "frames": 0, "worst": []}
    for c in chars:
        res["overreach"] += getattr(c, "solved", {}).get("report", {}).get("overreach", 0)
    for f in range(f0, f1 + 1, step):
        scn.frame_set(f)
        res["frames"] += 1
        for c in chars:
            ao = c.arm
            M = ao.matrix_world
            for s in ("L", "R"):
                pb = ao.pose.bones[f"foot_{s}"]
                mm = M @ pb.matrix
                heel = mm @ Vector((0, -0.06, -0.11)) if False else M @ (pb.matrix @ Vector((0, 0.0, 0)))
                # foot bone: head = ankle, +Y local = toward toe; ground contact points = sole under heel & toe
                ank = M @ pb.head
                toe = M @ pb.tail
                down = Vector((0, 0, -0.11 * c.s))
                fv = (toe - ank)
                fv.z = 0
                fvn = fv.normalized() if fv.length > 1e-6 else Vector((0, -1, 0))
                heelp = ank - fvn * 0.06 * c.s + down
                toep = toe + down
                ik = ao.pose.bones[f"shin_{s}"].constraints["IK"].influence
                hist[c.name][s].append((f, heelp.copy(), toep.copy(), ik))
                if ik > 0.5 and min(heelp.z, toep.z) < -0.03:
                    res["penetrations"] += 1
            roots[c.name].append((f, (M @ ao.pose.bones["hips"].head).copy()))
            rots[c.name].append({b: (M @ ao.pose.bones[b].matrix).to_quaternion() for b in ("chest", "head", "forearm_L", "forearm_R", "shin_L", "shin_R")})
    # sliding: a sole point that stays on the ground for consecutive frames must not move
    for nm, sides in hist.items():
        for s, seq in sides.items():
            for (fa, ha, ta, ika), (fb, hb, tb, ikb) in zip(seq, seq[1:]):
                if ika < 0.99 or ikb < 0.99:
                    continue
                for pa, pb_ in ((ha, hb), (ta, tb)):
                    if pa.z < 0.025 and pb_.z < 0.025:
                        d = (Vector((pa.x, pa.y)) - Vector((pb_.x, pb_.y))).length / (fb - fa)
                        if d > 0.012:
                            res["slides"] += 1
                            res["worst"].append([nm, s, fb, round(d * 100, 1)])
                        res["slide_cm_max"] = max(res["slide_cm_max"], round(d * 100, 2))
    # bone pops: angular jumps > 40 deg/frame on core bones (excluding authored fast actions)
    res["pop_list"] = []
    for nm, seq in rots.items():
        for k in seq[0]:
            d = []
            for a, b in zip(seq, seq[1:]):
                ang = math.degrees(a[k].rotation_difference(b[k]).angle)
                d.append(min(ang, 360 - ang))
            for i in range(1, len(d) - 1):
                # a pop is a spike: much faster than both neighbouring frames
                if d[i] > 25 * step and d[i] > 2.5 * max(d[i - 1], d[i + 1], 4.0):
                    res["pops"] += 1
                    res["pop_list"].append([nm, k, f0 + (i + 1) * step, round(d[i])])
    res["pop_list"] = res["pop_list"][:12]
    # character overlaps (hips closer than 0.55 units)
    names = list(roots)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            for (f, a), (_, b) in zip(roots[names[i]], roots[names[j]]):
                if (Vector((a.x, a.y)) - Vector((b.x, b.y))).length < 0.55:
                    res["overlaps"] += 1
                    break
    res["worst"] = sorted(res["worst"], key=lambda w: -w[3])[:6]
    return res
