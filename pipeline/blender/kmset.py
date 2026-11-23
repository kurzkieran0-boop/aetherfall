"""THE KINDNESS METER — night city set, props and disaster VFX.

set_meter_city(seed, frame_range, sky="night"|"red", damage=0..1, ...) builds:
  plaza (wet reflective paving) · shop row with a hinged door (west) · VIP lounge with gold
  rope + red carpet (east) · the Spire leaning tower with leaderboard (north) · canal with a
  plank footbridge (south) · floodlight towers · streetlamps · lit skyline · giant number
  billboards · police/ambulance flashers.
VFX: meteor() trails, impact() = flash + shockwave ring + rigid-body debris blast + dust +
fire + embers + sparks + crater; fire_volume(); smoke_column(); red_sky(); signs that tear
off (rigid bodies released at a frame); crowd_flee() panic sim feeding the gait planner.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector

import kit as K
import meter as MT

MARKS = {
    "plaza": (0, 0, 0.05), "shop_door": (-18.7, -3.58, 0.05), "shop_out": (-16.0, -3.58, 0.05),
    "shop_in": (-20.7, -3.58, 0.05), "vip": (21, 5, 0.05), "vip_carpet": (15.5, 5, 0.05),
    "spire": (0, 40, 0.05), "pin": (2.5, 33.4, 0.05), "pin_rubble": (2.8, 34.4, 0.05),
    "bridge": (-8, -30, 0.55), "bridge_n": (-8, -25.6, 0.05), "bridge_s": (-8, -34.4, 0.05),
    "bench": (12, -24.6, 0.05), "alley": (-30, 14, 0.05), "crowd": (0, -4, 0.05),
    "street_e": (40, 0, 0.05), "street_s": (0, -18, 0.05), "fountain": (0, 6, 0.05),
    "impact1": (6, 2, 0.05), "impact2": (-6, 30, 0.05), "impact3": (-16, -12, 0.05),
    "hero": (0, 0, 0.05),
}

CANAL_Y = -30.0
SPIRE_LEAN = 9.0


def _wet_ground():
    return K.pbr("asphalt", 0.22, tint=(0.55, 0.57, 0.62), wet=0.85, name="asph_wet")


def _paving():
    return K.pbr("paving", 0.4, tint=(0.62, 0.62, 0.68), wet=0.7, name="plaza_pave")


def neon(name, text, loc, size, color, rot_z=0.0, strength=14, parent=None):
    m = MT._glow_mat(name + "_m", color, strength)
    o = MT.text_obj(name, text, size, m, parent)
    o.location = loc
    o.rotation_euler = (math.radians(90), 0, rot_z)
    return o


def shop(name, x, y, w, d, h, face_rot, color, sign, seed=0, door=False):
    """Shop block facing +X when face_rot=0 (rotation about Z)."""
    rng = random.Random(seed)
    root = K.empty(name, (x, y, 0), collection="set")
    root.rotation_euler = (0, 0, face_rot)
    wall = K.pbr("bricks", 0.5, tint=color, wet=0.0, name=f"{name}_brick")
    if door:
        dy = w * 0.22          # door centre (local y)
        K.box(f"{name}_blk", (-(d + 1.4) / 2, 0, h / 2), (d - 1.4, w, h), wall, root)
        K.box(f"{name}_fw1", (-0.7, (dy - 0.6 + (-w / 2)) / 2, h / 2), (1.4, (dy - 0.6) - (-w / 2), h), wall, root)
        K.box(f"{name}_fw2", (-0.7, (w / 2 + dy + 0.6) / 2, h / 2), (1.4, w / 2 - (dy + 0.6), h), wall, root)
        K.box(f"{name}_lintel", (-0.7, dy, (h + 2.3) / 2), (1.4, 1.2, h - 2.3), wall, root)
    else:
        K.box(f"{name}_blk", (-d / 2, 0, h / 2), (d, w, h), wall, root)
    glass_lit = K.emissive((1.0, 0.78, 0.48), 4.0, name=f"{name}_win")
    K.box(f"{name}_win", (0.02, -w * 0.18, 1.7), (0.06, w * 0.42, 2.0), glass_lit, root)
    K.box(f"{name}_frame", (0.05, -w * 0.18, 1.7), (0.08, w * 0.46, 2.2), K.plastic((0.08, 0.07, 0.06), 0.4), root)
    # awning
    aw = K.plastic(rng.choice(((0.75, 0.12, 0.12), (0.12, 0.45, 0.3), (0.15, 0.25, 0.65), (0.8, 0.55, 0.1))), 0.6)
    K.box(f"{name}_awn", (0.9, 0, 3.3), (1.8, w * 0.95, 0.12), aw, root, rot=(0, math.radians(-14), 0))
    # upper windows
    for k in range(int(h // 3.2) - 1):
        for j in range(3):
            lit = rng.random() < 0.55
            K.box(f"{name}_uw{k}{j}", (0.02, -w * 0.33 + j * w * 0.33, 4.8 + k * 3.2), (0.06, w * 0.18, 1.4),
                  K.emissive((1.0, 0.72, 0.42), 3.0, name=f"{name}_uwm") if lit else K.plastic((0.03, 0.035, 0.05), 0.1), root)
    neon(f"{name}_sign", sign, (0.3, 0, 4.0 + 0.0), 0.7, (1.0, 0.45, 0.25) if seed % 2 else (0.35, 0.8, 1.0),
         rot_z=math.radians(90), parent=root)
    res = {"root": root}
    if door:
        hinge = K.empty(f"{name}_hinge", (0.03, w * 0.22 + 0.6, 0), root, "set")
        K.box(f"{name}_door", (0, -0.6, 1.15), (0.1, 1.2, 2.3), K.plastic((0.35, 0.16, 0.08), 0.45), hinge, bevel=0.02)
        K.box(f"{name}_doorwin", (-0.06, -0.6, 1.6), (0.04, 0.7, 0.7), glass_lit, hinge)
        K.box(f"{name}_knob", (-0.1, -1.05, 1.1), (0.08, 0.08, 0.08), K.plastic((0.9, 0.75, 0.3), 0.2), hinge)
        # warm interior light spilling out when open
        L = K.light('AREA', (0, 0, 0), 300, (1.0, 0.75, 0.45), size=1.5, name=f"{name}_doorlight", volume=1.5)
        L.parent = root
        L.location = (-0.4, w * 0.22, 2.0)
        L.rotation_euler = (0, math.radians(90), 0)
        K.box(f"{name}_inside", (-1.38, w * 0.22, 1.15), (0.05, 1.2, 2.3), K.emissive((1.0, 0.7, 0.4), 6, name=f"{name}_inm"), root)
        res["hinge"] = hinge
        res["doorlight"] = L
    return res


def door_anim(hinge, keys):
    """keys: [(frame, angle_deg)] door swing; slams get an overshoot rebound."""
    for f, a in keys:
        hinge.rotation_euler = (0, 0, math.radians(a))
        hinge.keyframe_insert("rotation_euler", frame=f)


def vip_lounge(x, y):
    root = K.empty("vip", (x, y, 0), collection="set")
    gold = K.plastic((1.0, 0.72, 0.2), 0.18, coat=0.6)
    black = K.plastic((0.02, 0.02, 0.025), 0.15, coat=0.8)
    K.box("vip_blk", (6, 0, 7), (12, 16, 14), black, root, bevel=0.1)
    for k in range(7):
        K.box(f"vip_strip{k}", (-0.02, -6 + k * 2, 7), (0.1, 0.12, 13.5), K.emissive((1.0, 0.7, 0.25), 18, name="vipgold"), root)
    K.box("vip_doorway", (0.03, 0, 1.6), (0.08, 2.6, 3.2), K.emissive((1.0, 0.62, 0.3), 9, name="vipdoor"), root)
    neon("vip_sign", "VIP  5,000+", (-0.1, 0, 5.2), 1.0, (1.0, 0.72, 0.18), rot_z=math.radians(-90), strength=22, parent=root)
    K.box("vip_carpet", (-5, 0, 0.03), (10, 2.4, 0.04), K.plastic((0.55, 0.02, 0.04), 0.6), root)
    for i in range(6):
        for s in (-1, 1):
            K.cyl(f"vip_post{i}{s}", (-1 - i * 1.7, s * 1.7, 0.5), 0.07, 1.0, gold, root)
            K.sphere(f"vip_ball{i}{s}", (-1 - i * 1.7, s * 1.7, 1.02), 0.1, gold, root)
            if i < 5:
                K.box(f"vip_rope{i}{s}", (-1.85 - i * 1.7, s * 1.7, 0.85), (1.7, 0.06, 0.06), K.plastic((0.6, 0.02, 0.05), 0.4), root)
    L = K.light('AREA', (x - 3, y, 6), 2500, (1.0, 0.75, 0.4), size=6, name="vip_wash", target=(x - 4, y, 0), volume=0.6)
    return root


def spire(x, y, height=58, lean=0.0):
    """Leaning tower with a leaderboard screen. lean (deg) tilts toward -Y (the plaza)."""
    root = K.empty("spire", (x, y, 0), collection="set")
    root.rotation_euler = (math.radians(lean), 0, 0)
    conc = K.pbr("concrete", 0.3, tint=(0.55, 0.56, 0.6), name="spire_conc")
    K.box("spire_core", (0, 0, height / 2), (7, 7, height), conc, root, bevel=0.1)
    for k in range(int(height // 4)):
        K.box(f"spire_band{k}", (0, 0, 2 + k * 4), (7.3, 7.3, 0.25), K.emissive((0.4, 0.75, 1.0), 5, name="spireband"), root)
    scr = K.box("spire_screen", (0, -3.7, height * 0.62), (6.4, 0.2, 9), K.emissive((0.05, 0.08, 0.16), 2, name="screen_bg"), root)
    neon("spire_title", "TOP HELPERS", (0, -3.85, height * 0.62 + 3.5), 0.9, (1.0, 0.72, 0.18), parent=root, strength=16)
    for i, (nm, v) in enumerate((("1  LUXE", "9,882"), ("2  VANCE", "8,410"), ("3  MIRA", "7,965"), ("4  DEX", "6,120"))):
        neon(f"spire_r{i}", f"{nm}   {v}", (0, -3.85, height * 0.62 + 1.8 - i * 1.4), 0.62, (0.8, 0.95, 1.0), parent=root, strength=10)
    K.box("spire_beacon", (0, 0, height + 1), (1, 1, 1), K.emissive((1, 0.05, 0.03), 60, name="beacon"), root)
    return root


def canal(y=CANAL_Y, x0=-80, x1=80, width=8.0):
    stone = K.pbr("bricks", 0.35, tint=(0.45, 0.45, 0.5), name="canal_wall")
    for s in (-1, 1):
        K.box(f"canal_wall{s}", ((x0 + x1) / 2, y + s * (width / 2 + 0.3), -0.9), (x1 - x0, 0.6, 2.2), stone)
    water = bpy.data.materials.new("canal_water")
    nt, out = K._nodes(water)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.01, 0.02, 0.03, 1)
    b.inputs["Roughness"].default_value = 0.04
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.08
    nt.links.new(nz.outputs[0], bm.inputs["Height"])
    nt.links.new(bm.outputs[0], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs[0])
    K.box("canal_water", ((x0 + x1) / 2, y, -1.3), (x1 - x0, width, 0.1), water)


def bridge(x, y=CANAL_Y, length=10.0, broken=True):
    """Wooden footbridge across the canal; plank 'bridge_plank_gap' is the broken one."""
    wood = K.pbr("wood", 0.6, tint=(0.75, 0.55, 0.38), name="bridge_wood")
    dark = K.plastic((0.12, 0.08, 0.05), 0.6)
    root = K.empty("bridge", (x, y, 0), collection="set")
    for s in (-1, 1):
        K.box(f"br_beam{s}", (s * 1.25, 0, 0.3), (0.25, length, 0.35), dark, root)
        K.box(f"br_rail{s}", (s * 1.35, 0, 1.3), (0.12, length, 0.12), dark, root)
        for k in range(6):
            K.box(f"br_post{s}{k}", (s * 1.35, -length / 2 + k * length / 5, 0.85), (0.12, 0.12, 1.0), dark, root)
    planks = {}
    n = int(length / 0.42)
    for k in range(n):
        py = -length / 2 + 0.21 + k * 0.42
        nm = f"br_plank{k}"
        rot = (0, 0, 0)
        loc = (0, py, 0.52)
        if broken and k == n // 2 + 1:
            nm = "bridge_plank_gap"
            rot = (math.radians(28), math.radians(8), 0)
            loc = (0.35, py + 0.05, 0.36)
        planks[nm] = K.box(nm, loc, (2.4, 0.38, 0.08), wood, root, rot=rot, bevel=0.01)
    return root, planks


def ambulance(loc, rot_z, frame_range, name="amb"):
    root = K.empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    white = K.plastic((0.92, 0.92, 0.9), 0.3)
    K.box(f"{name}_box", (-0.6, 0, 1.4), (4.2, 2.2, 2.4), white, root, bevel=0.06)
    K.box(f"{name}_cab", (2.0, 0, 1.0), (1.6, 2.1, 1.6), white, root, bevel=0.06)
    K.box(f"{name}_stripe", (-0.6, 0, 1.2), (4.25, 2.25, 0.3), K.plastic((0.9, 0.1, 0.1), 0.4), root)
    tire = K.plastic((0.02, 0.02, 0.02), 0.7, coat=0)
    for i, (x, y) in enumerate(((1.8, 1.0), (1.8, -1.0), (-1.8, 1.0), (-1.8, -1.0))):
        K.cyl(f"{name}_w{i}", (x, y, 0.4), 0.4, 0.3, tire, root, rot=(math.pi / 2, 0, 0))
    f0, f1 = frame_range
    seq_r = [(f, (f // 4) % 2 == 0) for f in range(f0 - 1, f1 + 3, 4)]
    seq_b = [(f, (f // 4) % 2 == 1) for f in range(f0 - 1, f1 + 3, 4)]
    mr = K.anim_emissive(f"{name}_r", (1, 0.05, 0.03), seq_r, 45)
    mb = K.anim_emissive(f"{name}_b", (0.1, 0.3, 1), seq_b, 45)
    K.box(f"{name}_lr", (1.4, 0.6, 2.7), (0.3, 0.5, 0.18), mr, root)
    K.box(f"{name}_lb", (1.4, -0.6, 2.7), (0.3, 0.5, 0.18), mb, root)
    for col, seq, y in (((1, 0.05, 0.03), seq_r, 0.7), ((0.1, 0.3, 1), seq_b, -0.7)):
        L = K.light('POINT', (0, 0, 0), 0, col, 0.2, name=f"{name}_pl", volume=1.2)
        L.parent = root
        L.location = (1.4, y, 3.2)
        for fr, on in seq:
            L.data.energy = 1400 if on else 0
            L.data.keyframe_insert("energy", frame=fr)
        K._constant_all(L.data)
    return root


def billboard_number(name, loc, rot_z, value, color=(1.0, 0.72, 0.18), size=3.2, label="HELPED"):
    root = K.empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    K.box(f"{name}_bg", (0, 0.2, 0), (size * 4.2, 0.3, size * 2.2), K.emissive((0.02, 0.025, 0.05), 1, name="bb_bg"), root)
    neon(f"{name}_num", value, (0, 0, size * 0.15), size, color, parent=root, strength=14)
    neon(f"{name}_lab", label, (0, 0, -size * 0.65), size * 0.32, (0.85, 0.9, 1.0), parent=root, strength=8)
    return root


# --------------------------------------------------------------------- sky / world
def night_world(red=0.0, fog=0.0035):
    """Cool moonlit night; red>0 blends to the burning disaster sky (kept dark & contrasty:
    the red comes from the sky dome, fires and rim lights, not from flat fog)."""
    w = K.world("city_night", strength=0.22 + 0.06 * red, tint=(0.32 + 0.5 * red, 0.42 - 0.3 * red, 0.85 - 0.72 * red),
                fog=fog * (1 + red * 0.3), fog_color=(0.55 + 0.35 * red, 0.62 - 0.35 * red, 0.85 - 0.65 * red), aniso=0.6)
    return w


def red_sky_dome(f_range, red_keys=((1, 1.0),)):
    """Huge emissive gradient dome with streaking meteor trails across the sky."""
    m = bpy.data.materials.new("redsky")
    nt, out = K._nodes(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1.0, 0.22, 0.05, 1)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.12, 0.01, 0.02, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs[1].default_value = 0.0
    mr.inputs[2].default_value = 1.0
    nt.links.new(sep.outputs[2], mr.inputs[0])
    nt.links.new(mr.outputs[0], ramp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.5
    nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Factor"].default_value = 0.65
    nt.links.new(ramp.outputs[0], mix.inputs["A"])
    nt.links.new(nz.outputs["Color"], mix.inputs["B"])
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "Emission"
    em.inputs[1].default_value = 2.2
    nt.links.new(mix.outputs["Result"], em.inputs[0])
    nt.links.new(em.outputs[0], out.inputs[0])
    m.use_backface_culling = False
    dome = K.sphere("redsky_dome", (0, 0, 0), 1, m, collection="set")
    dome.scale = (1400, 1400, 900)
    for f, v in red_keys:
        em.inputs[1].default_value = 2.2 * v
        em.inputs[1].keyframe_insert("default_value", frame=f)
        dome.hide_render = v <= 0.01
        dome.keyframe_insert("hide_render", frame=f)
    K._constant_all(dome)
    return dome


def sky_streaks(f_range, n=10, seed=4):
    """Distant meteor streaks crossing the red sky (pure emission, cheap)."""
    rng = random.Random(seed)
    mat = K.emissive((1.0, 0.6, 0.25), 40, name="streak")
    f0, f1 = f_range
    for i in range(n):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(250, 500)
        start = Vector((math.cos(a) * r, math.sin(a) * r, rng.uniform(220, 340)))
        dirv = Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), -1)).normalized()
        o = K.box(f"streak{i}", tuple(start), (2.0, 2.0, 60), mat, collection="fx")
        o.rotation_euler = dirv.to_track_quat('Z', 'Y').to_euler()
        fs = rng.randint(f0 - 30, f1)
        o.keyframe_insert("location", frame=fs)
        o.location = start + dirv * 260
        o.keyframe_insert("location", frame=fs + 40)


# --------------------------------------------------------------------- disaster VFX
def _rock_mesh(name, r=1.0, seed=0):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
    rng = random.Random(seed)
    for v in bm.verts:
        v.co *= rng.uniform(0.75, 1.15)
    bm.to_mesh(me)
    bm.free()
    return me


def meteor(name, impact, f_impact, from_dir=(0.45, 0.25, 1.0), dist=260.0, size=3.0, travel=36, seed=0):
    """Glowing rock on a straight dive with a fire/smoke trail; returns the rock object."""
    d = Vector(from_dir).normalized()
    p1 = Vector(impact) + Vector((0, 0, size * 0.4))
    p0 = p1 + d * dist
    rock_mat = K.glow_crack_mat((0.05, 0.03, 0.03), (1.0, 0.35, 0.05), 40, name="meteor_rock", scale=0.8)
    rock = K.obj(name, _rock_mesh(name + "_me", size, seed), tuple(p0), mat=rock_mat, collection="fx")
    rock.keyframe_insert("location", frame=f_impact - travel)
    rock.location = p1
    rock.keyframe_insert("location", frame=f_impact)
    rock.rotation_euler = (0, 0, 0)
    rock.keyframe_insert("rotation_euler", frame=f_impact - travel)
    rock.rotation_euler = (3, 5, 2)
    rock.keyframe_insert("rotation_euler", frame=f_impact)
    rock.scale = (1, 1, 1)
    rock.keyframe_insert("scale", frame=f_impact)
    rock.scale = (0.0001,) * 3
    rock.keyframe_insert("scale", frame=f_impact + 1)
    for fc in K._fcurves(rock):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    # plasma sheath + trail: stretched glowing cones parented to the rock, pointing back up the path
    hot = K.emissive((1.0, 0.55, 0.15), 60, name="trail_hot")
    warm = K.emissive((1.0, 0.25, 0.05), 25, name="trail_warm")
    q = d.to_track_quat('Z', 'Y').to_euler()
    for k, (mat, ln, w) in enumerate(((hot, size * 7, size * 1.2), (warm, size * 16, size * 1.9))):
        c = K.obj(f"{name}_trail{k}", K._cyl_mesh(10), (0, 0, 0), (w, w, ln), q, mat, collection="fx")
        c.parent = rock
        c.matrix_parent_inverse = rock.matrix_world.inverted()
        c.location = p0 + d * ln * 0.5
        c.keyframe_insert("location", frame=f_impact - travel)
        c.location = p1 + d * ln * 0.5
        c.keyframe_insert("location", frame=f_impact)
        c.parent = None
        c.location = p0 + d * ln * 0.5
        c.keyframe_insert("location", frame=f_impact - travel)
        c.location = p1 + d * ln * 0.5
        c.keyframe_insert("location", frame=f_impact)
        c.scale = (w, w, ln)
        c.keyframe_insert("scale", frame=f_impact)
        c.scale = (0.0001,) * 3
        c.keyframe_insert("scale", frame=f_impact + 1)
        for fc in K._fcurves(c):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    smoke = K.volume_mat(0.25, (0.12, 0.1, 0.1), 0.2, name=f"{name}_smk")
    for k in range(7):
        t = (k + 1) / 8
        p = p0.lerp(p1, t)
        s = K.sphere(f"{name}_smk{k}", tuple(p + d * size * 6), size * 2.2, smoke, collection="fx")
        fk = int(f_impact - travel + travel * t)
        s.scale = (0.0001,) * 3
        s.keyframe_insert("scale", frame=fk)
        s.scale = (size * 2.2,) * 3
        s.keyframe_insert("scale", frame=fk + 2)
        s.scale = (size * 4.5,) * 3
        s.keyframe_insert("scale", frame=fk + 60)
    L = K.light('POINT', (0, 0, 0), 2.0e5 * size, (1.0, 0.5, 0.2), size=size, name=f"{name}_glow", volume=1.5)
    L.parent = rock
    L.data.use_shadow = False
    L.data.keyframe_insert("energy", frame=f_impact)
    L.data.energy = 0
    L.data.keyframe_insert("energy", frame=f_impact + 1)
    return rock


def shockwave(name, loc, f, radius=40.0, dur=18):
    """Expanding ground ring of light + a translucent distortion shell."""
    ring_m = K.emissive((1.0, 0.6, 0.3), 30, name=f"{name}_ringm")
    me = bpy.data.meshes.new(name + "_tor")
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, radius=1.0, segments=64)
    ret = bmesh.ops.extrude_edge_only(bm, edges=bm.edges[:])
    vs = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.scale(bm, vec=(0.9, 0.9, 1), verts=vs)
    bm.to_mesh(me)
    bm.free()
    ring = K.obj(name, me, (loc[0], loc[1], 0.15), mat=ring_m, collection="fx")
    ring.scale = (0.5, 0.5, 1)
    ring.keyframe_insert("scale", frame=f)
    ring.scale = (radius, radius, 1)
    ring.keyframe_insert("scale", frame=f + dur)
    em = ring_m.node_tree.nodes["Emission"].inputs[1]
    em.default_value = 60
    em.keyframe_insert("default_value", frame=f)
    em.default_value = 0
    em.keyframe_insert("default_value", frame=f + dur)
    shell_m = bpy.data.materials.new(name + "_shellm")
    nt, out = K._nodes(shell_m)
    g = nt.nodes.new("ShaderNodeBsdfGlass")
    g.inputs["IOR"].default_value = 1.06
    g.inputs["Roughness"].default_value = 0.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.5
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(g.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    try:
        shell_m.surface_render_method = 'BLENDED'
    except Exception:
        pass
    shell = K.sphere(name + "_shell", (loc[0], loc[1], 0), 1, shell_m, collection="fx")
    shell.scale = (0.5, 0.5, 0.2)
    shell.keyframe_insert("scale", frame=f)
    shell.scale = (radius * 0.8, radius * 0.8, radius * 0.18)
    shell.keyframe_insert("scale", frame=f + int(dur * 0.8))
    shell.scale = (0.0001,) * 3
    shell.keyframe_insert("scale", frame=f + int(dur * 0.8) + 1)
    return ring


def _rb_add(o, kind='ACTIVE', mass=1.0, shape='BOX', kinematic=False, friction=0.7, bounce=0.15):
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.rigidbody.object_add()
    rb = o.rigid_body
    rb.type = kind
    rb.mass = mass
    rb.collision_shape = shape
    rb.friction = friction
    rb.restitution = bounce
    rb.kinematic = kinematic
    o.select_set(False)
    return rb


def rigid_world(f0, f1):
    scn = bpy.context.scene
    if scn.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    rw = scn.rigidbody_world
    rw.point_cache.frame_start = f0
    rw.point_cache.frame_end = f1
    rw.substeps_per_frame = 10
    rw.solver_iterations = 12
    if not bpy.data.objects.get("rb_ground"):
        g = K.box("rb_ground", (0, 0, -0.5), (600, 600, 1.0), None, collection="fx")
        g.hide_render = True
        _rb_add(g, 'PASSIVE', shape='BOX')
    return rw


def debris_blast(name, loc, f, count=60, power=1.0, seed=0, radius=3.0, hot=0.15):
    """Rigid-body debris: chunks rest in a pile at the impact point, then an invisible
    kinematic pusher blooms out of the ground at frame f and blasts them outward."""
    rng = random.Random(seed)
    conc = K.pbr("concrete", 0.5, tint=(0.55, 0.55, 0.58), name="deb_conc")
    pave = _paving()
    hotm = K.emissive((1.0, 0.35, 0.08), 18, name="deb_hot")
    for i in range(count):
        s = rng.uniform(0.25, 0.9) * power
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0, radius)
        p = (loc[0] + math.cos(a) * r, loc[1] + math.sin(a) * r, 0.3 + rng.uniform(0, 1.6))
        o = K.box(f"{name}_c{i}", p, (s, s * rng.uniform(0.5, 1.4), s * rng.uniform(0.3, 0.9)),
                  hotm if rng.random() < hot else (pave if rng.random() < 0.5 else conc), collection="fx",
                  rot=(rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3)))
        o.scale = (0.0001,) * 3
        o.keyframe_insert("scale", frame=f - 1)
        o.scale = (s, s * rng.uniform(0.5, 1.4), s * rng.uniform(0.3, 0.9))
        o.keyframe_insert("scale", frame=f)
        _rb_add(o, 'ACTIVE', mass=s * s * s * 2, bounce=0.2)
        o.rigid_body.kinematic = True
        o.rigid_body.keyframe_insert("kinematic", frame=f)
        o.rigid_body.kinematic = False
        o.rigid_body.keyframe_insert("kinematic", frame=f + 1)
    pusher = K.sphere(f"{name}_push", (loc[0], loc[1], -3.0), 1.0, None, collection="fx")
    pusher.hide_render = True
    pusher.scale = (1.0, 1.0, 1.0)
    _rb_add(pusher, 'ACTIVE', shape='SPHERE', kinematic=True)
    pusher.keyframe_insert("location", frame=f)
    pusher.keyframe_insert("scale", frame=f)
    pusher.location = (loc[0], loc[1], 0.5)
    pusher.scale = (radius * 2.6 * power,) * 3
    pusher.keyframe_insert("location", frame=f + 2)
    pusher.keyframe_insert("scale", frame=f + 2)
    pusher.location = (loc[0], loc[1], -30)
    pusher.keyframe_insert("location", frame=f + 4)


def falling_sign(name, loc, size, f_release, color=(0.35, 0.8, 1.0), text="OPEN", rot_z=0.0):
    """Neon sign that tears free at f_release (rigid body: kinematic -> dynamic)."""
    o = K.box(name, loc, size, K.plastic((0.05, 0.05, 0.07), 0.4), collection="fx", rot=(0, 0, rot_z))
    m = MT._glow_mat(name + "_m", color, 16)
    t = MT.text_obj(name + "_txt", text, size[2] * 0.55, m, o)
    t.location = (0, -0.6, 0)
    t.scale = (1 / size[0], 1 / size[1], 1 / size[2])
    _rb_add(o, 'ACTIVE', mass=40, kinematic=True)
    o.rigid_body.keyframe_insert("kinematic", frame=f_release)
    o.rigid_body.kinematic = False
    o.rigid_body.keyframe_insert("kinematic", frame=f_release + 1)
    # sparks + flicker when it rips
    MT.spark_burst(None, f_release, 40, (1.0, 0.8, 0.4), name=name + "_spk", speed=5, seed=3)
    for o2 in bpy.data.objects:
        if o2.name.startswith(name + "_spk"):
            o2.location = Vector(o2.location) + Vector(loc)
    return o


def fire_volume(name, loc, size=(3, 3, 4), intensity=1.0, f_range=(1, 200), seed=0):
    """Volumetric fire: noise-driven blackbody emission inside a box + flickering light."""
    m = bpy.data.materials.new(name + "_vol")
    nt, out = K._nodes(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.2
    nz.inputs["Detail"].default_value = 5
    nz.inputs["Roughness"].default_value = 0.6
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    hgt = nt.nodes.new("ShaderNodeMapRange")       # fade toward the top
    hgt.inputs[1].default_value = -1.0
    hgt.inputs[2].default_value = 1.0
    hgt.inputs[3].default_value = 1.0
    hgt.inputs[4].default_value = 0.0
    nt.links.new(sep.outputs[2], hgt.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = 'MULTIPLY'
    nt.links.new(nz.outputs[0], mul.inputs[0])
    nt.links.new(hgt.outputs[0], mul.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(mul.outputs[0], ramp.inputs[0])
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = 0.0
    v.inputs["Temperature"].default_value = 1500
    st = nt.nodes.new("ShaderNodeMath")
    st.operation = 'MULTIPLY'
    st.inputs[1].default_value = 6.0 * intensity
    nt.links.new(ramp.outputs[0], st.inputs[0])
    nt.links.new(st.outputs[0], v.inputs["Blackbody Intensity"])
    dn = nt.nodes.new("ShaderNodeMath")
    dn.operation = 'MULTIPLY'
    dn.inputs[1].default_value = 1.5
    nt.links.new(ramp.outputs[0], dn.inputs[0])
    nt.links.new(dn.outputs[0], v.inputs["Density"])
    v.inputs["Color"].default_value = (0.05, 0.03, 0.02, 1)
    nt.links.new(v.outputs[0], out.inputs["Volume"])
    o = K.box(name, (loc[0], loc[1], loc[2] + size[2] / 2), size, m, collection="fx")
    # rising noise = flames licking upward
    f0, f1 = f_range
    mp.inputs["Location"].default_value = (0, 0, 0)
    mp.inputs["Location"].keyframe_insert("default_value", frame=f0)
    mp.inputs["Location"].default_value = (0, 0, -(f1 - f0) / 24 * 1.8)
    mp.inputs["Location"].keyframe_insert("default_value", frame=f1)
    for fc in K._fcurves(m.node_tree) if hasattr(m.node_tree, "animation_data") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    L = K.light('POINT', (loc[0], loc[1], loc[2] + size[2] * 0.4), 9000 * intensity * max(size) / 3,
                (1.0, 0.45, 0.12), size=max(size) * 0.4, name=f"{name}_firelight", volume=0.6)
    L.data.use_shadow = False
    K.flicker_light(L, f0, f1, seed=seed, lo=0.6, hi=1.25)
    return o


def smoke_column(name, loc, height=40, f_range=(1, 200), dark=0.12, density=0.25):
    m = K.volume_mat(density, (dark, dark * 0.95, dark * 0.9), 0.3, name=name + "_m")
    for k in range(6):
        z = 3 + k * height / 6
        s = K.sphere(f"{name}{k}", (loc[0] + k * 0.8, loc[1] + k * 0.4, z), 1, m, collection="fx")
        r = 3 + k * 1.6
        s.scale = (r, r, r * 1.3)
        s.keyframe_insert("location", frame=f_range[0])
        s.location = (loc[0] + k * 0.8 + 3, loc[1] + k * 0.4 + 1.5, z + 6)
        s.keyframe_insert("location", frame=f_range[1])


def crater(name, loc, r=4.0):
    m = K.glow_crack_mat((0.03, 0.025, 0.025), (1.0, 0.3, 0.05), 30, name="crater_m", scale=1.0)
    c = K.cyl(name, (loc[0], loc[1], 0.06), r, 0.12, m, collection="fx", verts=24)
    for i in range(10):
        a = i / 10 * math.tau
        K.box(f"{name}_lip{i}", (loc[0] + math.cos(a) * r, loc[1] + math.sin(a) * r, 0.3), (1.8, 1.0, 0.6),
              K.pbr("paving", 0.4, tint=(0.4, 0.4, 0.42), name="lip_m"), collection="fx",
              rot=(math.radians(20), 0, a + math.pi / 2))
    return c


def impact(name, loc, f, power=1.0, seed=0, debris=True, fire=True, f_range=(1, 200), crater_=True):
    """Full meteor hit at `loc` on frame f."""
    loc = Vector(loc)
    # flash (lightning-style) + hot glow that decays
    fl = K.light('POINT', (loc.x, loc.y, 4), 0, (1.0, 0.7, 0.4), size=4, name=f"{name}_flash", volume=2.0)
    fl.data.use_shadow = True
    fl.data.keyframe_insert("energy", frame=f - 1)
    for k, e in ((0, 4.0e6), (1, 2.6e6), (2, 1.6e6), (4, 4.0e5), (8, 1.2e5), (16, 5e4)):
        fl.data.energy = e * power
        fl.data.keyframe_insert("energy", frame=f + k)
    sky = K.light('SUN', (0, 0, 50), 0, (1.0, 0.75, 0.55), name=f"{name}_skyflash")
    sky.rotation_euler = (math.radians(30), 0, math.radians(40))
    sky.data.use_shadow = False
    sky.data.keyframe_insert("energy", frame=f - 1)
    sky.data.energy = 18 * power
    sky.data.keyframe_insert("energy", frame=f)
    sky.data.energy = 0
    sky.data.keyframe_insert("energy", frame=f + 3)
    shockwave(f"{name}_sw", loc, f, radius=45 * power)
    K.dust_cloud(f, tuple(loc), radius=10 * power, name=f"{name}_dust", duration=70, density=0.3)
    MT.spark_burst(None, f, int(90 * power), (1.0, 0.65, 0.25), name=f"{name}_spk", speed=14 * power, seed=seed,
                   life=34, gravity=9.0, size=0.08)
    for o in bpy.data.objects:
        if o.name.startswith(f"{name}_spk") and o.parent is None:
            for fc in K._fcurves(o):
                if fc.data_path == "location":
                    for kp in fc.keyframe_points:
                        kp.co.y += loc[fc.array_index] + (1.0 if fc.array_index == 2 else 0)
                    fc.update()
    if crater_:
        crater(f"{name}_crater", loc, 3.5 * power)
    if debris:
        debris_blast(f"{name}_deb", loc, f, count=int(55 * power), power=power, seed=seed)
    if fire:
        fire_volume(f"{name}_fire", (loc.x, loc.y, 0), (5 * power, 5 * power, 6 * power), 1.2, f_range, seed)
        smoke_column(f"{name}_smoke", (loc.x, loc.y, 0), 45, f_range)
        K.particles("embers", (loc.x, loc.y, 0), f_range, count=260, area=14, height=10, name=f"{name}_emb")
    return fl


# --------------------------------------------------------------------- crowd sim
def crowd_flee(n, center, radius, threat, f_start, f_end, seed=0, speed=(3.8, 6.4), avoid=(), exits=None,
               delay=(2, 16)):
    """Agents scatter away from `threat` with reaction delays, speed spread, separation
    steering and obstacle avoidance. Returns [{start, yaw, delay, traj:[[f,x,y]], stumble}]."""
    rng = random.Random(seed)
    ag = []
    for i in range(n):
        a = rng.uniform(0, math.tau)
        r = radius * math.sqrt(rng.uniform(0.05, 1))
        p = Vector((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r))
        ag.append({"p": p, "v": Vector((0, 0)), "max": rng.uniform(*speed), "delay": f_start + rng.randint(*delay),
                   "tr": [], "wob": rng.uniform(0, 6), "stumble": rng.random() < 0.18, "yaw": rng.uniform(0, 360)})
    T = Vector(threat[:2])
    for f in range(f_start, f_end + 1):
        for i, A in enumerate(ag):
            if f >= A["delay"]:
                away = (A["p"] - T)
                away = away.normalized() if away.length > 1e-3 else Vector((1, 0))
                if exits:
                    ex = min(exits, key=lambda e: (Vector(e) - A["p"]).length)
                    to = (Vector(ex) - A["p"])
                    away = (away * 0.6 + to.normalized() * 0.8).normalized()
                wob = Vector((math.cos(f * 0.15 + A["wob"]), math.sin(f * 0.13 + A["wob"]))) * 0.25
                desire = (away + wob).normalized() * A["max"]
                sep = Vector((0, 0))
                for j, B in enumerate(ag):
                    if i != j:
                        d = A["p"] - B["p"]
                        if 1e-4 < d.length < 1.4:
                            sep += d.normalized() * (1.4 - d.length) * 6
                for ox, oy, orad in avoid:
                    d = A["p"] - Vector((ox, oy))
                    if d.length < orad + 1.5:
                        sep += d.normalized() * (orad + 1.5 - d.length) * 8
                acc = (desire - A["v"]) * 0.18 + sep * 0.05
                A["v"] += acc
                if A["v"].length > A["max"]:
                    A["v"] = A["v"].normalized() * A["max"]
                A["p"] += A["v"] / 24.0
            if (f - f_start) % 2 == 0 or f == f_end:
                A["tr"].append([f, A["p"].x, A["p"].y])
    return [{"start": [a["tr"][0][1], a["tr"][0][2], 0.05], "traj": a["tr"], "delay": a["delay"],
             "stumble": a["stumble"], "yaw": a["yaw"]} for a in ag]


# --------------------------------------------------------------------- pets
def rare_pet(name, kind="dragon", color=(0.5, 0.2, 1.0)):
    """Small glowing blocky creature (carried). Returns root empty."""
    root = K.empty(name, (0, 0, 0), collection="chars")
    body = K.plastic(color, 0.25, coat=0.8)
    glow = K.emissive(tuple(min(1, c * 1.4 + 0.2) for c in color), 25, name=f"{name}_glow")
    K.box(f"{name}_body", (0, 0, 0), (0.42, 0.55, 0.36), body, root, bevel=0.06, collection="chars")
    K.box(f"{name}_head", (0, -0.36, 0.16), (0.34, 0.3, 0.3), body, root, bevel=0.05, collection="chars")
    for s in (-1, 1):
        K.box(f"{name}_eye{s}", (s * 0.08, -0.52, 0.2), (0.07, 0.02, 0.08), glow, root, collection="chars")
        if kind == "dragon":
            K.box(f"{name}_wing{s}", (s * 0.42, 0.05, 0.18), (0.5, 0.36, 0.04), glow, root,
                  rot=(0, math.radians(-25 * s), 0), collection="chars")
            K.box(f"{name}_horn{s}", (s * 0.1, -0.33, 0.37), (0.05, 0.05, 0.14), glow, root, collection="chars")
        else:
            K.box(f"{name}_ear{s}", (s * 0.11, -0.33, 0.38), (0.08, 0.06, 0.14), body, root, collection="chars")
    K.box(f"{name}_tail", (0, 0.42, 0.08), (0.08, 0.36, 0.08), glow, root, rot=(math.radians(20), 0, 0), collection="chars")
    L = K.light('POINT', (0, 0, 0), 60, color, 0.2, name=f"{name}_aura", volume=0.3)
    L.parent = root
    L.data.use_shadow = False
    return root


# --------------------------------------------------------------------- the set
def set_meter_city(seed=7, frame_range=(1, 120), sky="night", damage=0.0, spire_lean=None, door=None,
                   plank_fixed=None, fires=(), signs=(), **kw):
    f0, f1 = frame_range
    red = 1.0 if sky == "red" else 0.0
    night_world(red=red)
    K.ground(900, _wet_ground())
    pl = K.box("plaza_floor", (0, 2, 0.02), (52, 60, 0.04), _paving())
    K.city_grid(seed=seed, radius=300, block=34, street=16, min_h=24, max_h=120,
                keep_clear=[(0, 0, 70), (0, CANAL_Y, 40)], lit=0.42, boulevard=0)
    # west shop row (fronts face +X)
    shops = {}
    names = (("BREAD", (0.75, 0.55, 0.45)), ("TOYS", (0.55, 0.6, 0.75)), ("GEAR", (0.6, 0.5, 0.45)), ("PETS", (0.7, 0.62, 0.5)))
    for i, (sg, col) in enumerate(names):
        y = -18 + i * 12
        r = shop(f"shop{i}", -20, y, 11, 8, 10 + (i % 2) * 4, 0.0, col, sg, seed=i, door=(i == 1))
        shops[sg] = r
    hinge = shops["TOYS"]["hinge"]
    if door:
        door_anim(hinge, [(int(f), a) for f, a in door])
    # east: VIP lounge + a second row
    vip_lounge(21, 5)
    for i, (sg, col) in enumerate((("CAFE", (0.6, 0.45, 0.4)), ("ARCADE", (0.45, 0.45, 0.6)))):
        shop(f"eshop{i}", 22, -14 + i * 36, 10, 8, 12, math.pi, col, sg, seed=10 + i)
    # north: the Spire
    lean = SPIRE_LEAN if spire_lean is None else spire_lean
    sp = spire(0, 40, 58, lean=0.0)
    if isinstance(lean, (list, tuple)):
        for f, a in lean:
            sp.rotation_euler = (math.radians(a), 0, 0)
            sp.keyframe_insert("rotation_euler", frame=int(f))
    else:
        sp.rotation_euler = (math.radians(lean), 0, 0)
    # canal + bridge (south)
    canal()
    br, planks = bridge(-8, broken=True)
    gap = planks["bridge_plank_gap"]
    if plank_fixed is not None:
        fa_, fb_ = plank_fixed
        gap.keyframe_insert("location", frame=fa_)
        gap.keyframe_insert("rotation_euler", frame=fa_)
        gap.location = (0.25, gap.location.y, 0.7)
        gap.rotation_euler = (math.radians(10), 0, 0)
        gap.keyframe_insert("location", frame=int(fa_ + (fb_ - fa_) * 0.5))
        gap.keyframe_insert("rotation_euler", frame=int(fa_ + (fb_ - fa_) * 0.5))
        gap.location = (0, gap.location.y - 0.05, 0.52)
        gap.rotation_euler = (0, 0, 0)
        gap.keyframe_insert("location", frame=fb_)
        gap.keyframe_insert("rotation_euler", frame=fb_)
    # floodlights + streetlamps
    for i, (x, y) in enumerate(((-26, 26), (26, 26), (-26, -22), (26, -22))):
        K.floodlight_tower((x, y, 0), (0, 2, 0), height=16, energy=70000, name=f"flood{i}",
                           color=(0.8, 0.88, 1.0) if not red else (1.0, 0.75, 0.6))
    for i in range(10):
        a = i / 10 * math.tau
        K.streetlamp((math.cos(a) * 24, 2 + math.sin(a) * 28, 0), a + math.pi, name=f"lamp{i}", energy=1200)
    for x in (-18, 2, 22):
        K.streetlamp((x, CANAL_Y + 5.2, 0), -math.pi / 2, name=f"clamp{x}", energy=1600)
    K.bench((12, -25.2, 0), 0.0)
    K.streetlamp((13.9, -23.6, 0), math.radians(200), name="benchlamp", energy=2600)
    for k, yy in enumerate((-34.6, -25.4)):   # warm lanterns on the footbridge
        K.box(f"br_lantern{k}", (-9.35, yy, 1.55), (0.22, 0.22, 0.3), K.emissive((1.0, 0.7, 0.35), 25, name="lantern_m"))
        L = K.light('POINT', (-9.0, yy, 1.7), 220, (1.0, 0.68, 0.35), size=0.15, name=f"br_lanternL{k}", volume=1.0)
    K.light('SPOT', (-8.0, -30.0, 14.0), 3500, (0.55, 0.7, 1.0), size=1.2, spot=55, name="moon_bridge",
            target=(-8.0, -30.0, 0.5), volume=0.6)
    K.light('POINT', (-20.65, -3.58, 2.25), 160, (1.0, 0.72, 0.45), size=0.2, name="doorlight_bulb", volume=0.4)
    K.box("bench_back", (12, -24.75, 0.95), (2.2, 0.1, 0.6), K.plastic((0.3, 0.18, 0.1), 0.5))
    for i, (x, y) in enumerate(((-12, -14), (12, -14), (-12, 18), (12, 18))):
        K.tree((x, y, 0), 6.5, seed=i)
    # fountain with glowing basin
    K.cyl("fount_basin", (0, 6, 0.4), 3.2, 0.8, K.pbr("concrete", 0.4, tint=(0.6, 0.6, 0.65), name="fount_c"), verts=32)
    K.cyl("fount_water", (0, 6, 0.75), 2.9, 0.1, K.emissive((0.2, 0.55, 1.0), 3, name="fount_w"), verts=32)
    # giant VIP number billboards on towers
    billboard_number("bb1", (-34, 40, 26), math.radians(30), "9,882", label="LUXE · TOP HELPER")
    billboard_number("bb2", (36, -6, 22), math.radians(-90), "8,410", color=(0.6, 0.9, 1.0), label="VANCE · VIP")
    # emergency vehicles
    if red or kw.get("sirens"):
        K.police_car((30, -6, 0), math.radians(90), (f0 - 6, f1 + 6), seed=1, name="cop1")
        ambulance((-30, 10, 0), math.radians(-90), (f0 - 6, f1 + 6))
    # damage state (after the first impact)
    if damage > 0:
        crater("crater_main", MARKS["impact1"], 4.5)
        for i in range(int(18 * damage)):
            rng = random.Random(i * 13)
            K.box(f"rubble{i}", (rng.uniform(-14, 18), rng.uniform(-14, 30), 0.3), (rng.uniform(0.5, 1.6),) * 3,
                  K.pbr("concrete", 0.5, tint=(0.5, 0.5, 0.52), name="rubm"), rot=(rng.uniform(0, 3), rng.uniform(0, 3), 0))
        for i, (x, y) in enumerate(((8, 4), (-14, 22), (16, -10), (-20, -4))):
            fire_volume(f"bfire{i}", (x, y, 0), (4, 4, 5), 1.0, (f0 - 10, f1 + 10), seed=i)
        smoke_column("smokeA", (8, 4, 0), 50, (f0 - 10, f1 + 10))
        K.particles("embers", (0, 8, 0), (f0 - 10, f1 + 10), count=400, area=40, height=14, name="embers_all")
    if sky == "red":
        red_sky_dome((f0, f1))
        sky_streaks((f0, f1), n=8)
    # pinned zone rubble pile under the spire (always present once damage > 0.5)
    if damage >= 0.5:
        fire_volume("pinfire", (6.4, 35.0, 0), (3.0, 3.0, 4.0), 1.1, (f0 - 10, f1 + 10), seed=9)
        K.light('POINT', (4.2, 31.2, 1.4), 500, (1.0, 0.5, 0.22), size=0.5, name="pinglow", volume=0.3)
        pile = K.pbr("concrete", 0.4, tint=(0.5, 0.5, 0.53), name="pile_m")
        rng = random.Random(5)
        for i in range(16):
            K.box(f"pile{i}", (MARKS["pin"][0] + rng.uniform(-1.6, 2.2), MARKS["pin"][1] + rng.uniform(0.3, 2.6),
                               rng.uniform(0.2, 0.9)), (rng.uniform(0.6, 1.6), rng.uniform(0.6, 1.4), rng.uniform(0.3, 0.8)),
                  pile, rot=(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(0, 3)))
    marks = dict(MARKS)
    return marks


K.SETS["meter_city"] = set_meter_city
