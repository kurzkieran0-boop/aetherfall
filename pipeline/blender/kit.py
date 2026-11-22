"""Reusable 3D kit for the brick-city monster films (runs inside Blender / bpy).

Contents
  * materials   – toy plastic, emissive, lit-window skyscraper shader, wet PBR road
  * world       – HDRI + night tint + volumetric fog (god rays come from spot lights)
  * props       – police car (flashing bar + real red/blue lights), sedan, barrier,
                  floodlight tower, fence, crane, pylon, streetlamp, water tank ...
  * sets        – city_block, plaza, rooftop, subway, school, forest, lab, bunker
  * characters  – blocky rigged figures (pivot hierarchy) + expression controls
  * actions     – idle, walk, run, panic, look_up, point, fall, hide, grab, climb,
                  turn, gasp, talk  (anticipation / overshoot / follow-through)
  * monsters    – procedural original giants with a signature walk, roar, impacts
  * fx          – rain, embers, dust motes, leaves, debris bursts, dust clouds,
                  lightning, ground shake
All geometry is procedural; textures come from ./assets (CC0) when present.
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import assets as A  # noqa: E402

# --------------------------------------------------------------------------- utils

_MESH_CACHE = {}
_MAT_CACHE = {}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MESH_CACHE.clear()
    _MAT_CACHE.clear()


def coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _box_mesh(bevel=0.0, key=None):
    """Unit cube (-0.5..0.5) mesh, optionally bevelled; shared between objects."""
    k = key or ("box", round(bevel, 3))
    if k in _MESH_CACHE:
        return _MESH_CACHE[k]
    me = bpy.data.meshes.new(f"box_{bevel}")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2,
                        affect='EDGES', profile=0.5)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = bevel > 0
    _MESH_CACHE[k] = me
    return me


def _cyl_mesh(verts=12):
    k = ("cyl", verts)
    if k in _MESH_CACHE:
        return _MESH_CACHE[k]
    me = bpy.data.meshes.new("cyl")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=0.5,
                          radius2=0.5, depth=1.0)
    bm.to_mesh(me)
    bm.free()
    _MESH_CACHE[k] = me
    return me


def _sphere_mesh(seg=12):
    k = ("sph", seg)
    if k in _MESH_CACHE:
        return _MESH_CACHE[k]
    me = bpy.data.meshes.new("sph")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.5)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    _MESH_CACHE[k] = me
    return me


def obj(name, mesh, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), mat=None,
        parent=None, collection="set"):
    o = bpy.data.objects.new(name, mesh)
    coll(collection).objects.link(o)
    o.location = loc
    o.scale = scale
    o.rotation_euler = rot
    if mat is not None and mesh is not None:
        if len(mesh.materials) == 0:
            mesh.materials.append(None)
        o.material_slots[0].link = 'OBJECT'
        o.material_slots[0].material = mat
    if parent is not None:
        o.parent = parent
    return o


def box(name, loc, size, mat=None, parent=None, bevel=0.0, rot=(0, 0, 0),
        collection="set"):
    return obj(name, _box_mesh(bevel), loc, size, rot, mat, parent, collection)


def cyl(name, loc, radius, depth, mat=None, parent=None, rot=(0, 0, 0),
        collection="set", verts=12):
    return obj(name, _cyl_mesh(verts), loc, (radius * 2, radius * 2, depth), rot,
               mat, parent, collection)


def sphere(name, loc, radius, mat=None, parent=None, collection="set"):
    return obj(name, _sphere_mesh(), loc, (radius * 2,) * 3, (0, 0, 0), mat,
               parent, collection)


def empty(name, loc=(0, 0, 0), parent=None, collection="rig"):
    e = bpy.data.objects.new(name, None)
    coll(collection).objects.link(e)
    e.empty_display_size = 0.2
    e.location = loc
    if parent is not None:
        e.parent = parent
    return e


def key(o, path, frame, value=None, interp=None):
    if value is not None:
        setattr(o, path, value) if not isinstance(value, (list, tuple)) else \
            setattr(o, path, value)
    o.keyframe_insert(data_path=path, frame=frame)
    if interp:
        _set_interp(o, path, frame, interp)


def _set_interp(o, path, frame, interp):
    ad = o.animation_data
    if not ad or not ad.action:
        return
    for fc in _fcurves(o):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                if abs(kp.co.x - frame) < 0.01:
                    kp.interpolation = interp


def _fcurves(o):
    """Blender 4.4+ layered actions: walk channelbags; fall back to legacy."""
    ad = o.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return list(act.fcurves)
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
    except AttributeError:
        pass
    return out


def set_rot(o, frame, x=None, y=None, z=None):
    r = list(o.rotation_euler)
    for i, v in enumerate((x, y, z)):
        if v is not None:
            r[i] = math.radians(v)
    o.rotation_euler = r
    o.keyframe_insert("rotation_euler", frame=frame)


def set_loc(o, frame, loc):
    o.location = loc
    o.keyframe_insert("location", frame=frame)


# ----------------------------------------------------------------------- materials

def _nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return nt, out


def plastic(color, rough=0.32, name=None, coat=0.35, emit=None, emit_strength=0.0):
    k = ("plastic", tuple(round(c, 3) for c in color), rough, emit, emit_strength)
    if k in _MAT_CACHE:
        return _MAT_CACHE[k]
    m = bpy.data.materials.new(name or f"plastic_{len(_MAT_CACHE)}")
    nt, out = _nodes(m)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.15
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    nt.links.new(b.outputs[0], out.inputs[0])
    m.diffuse_color = (*color, 1)
    _MAT_CACHE[k] = m
    return m


def emissive(color, strength=8.0, name=None):
    k = ("emit", tuple(round(c, 3) for c in color), strength, name)
    if k in _MAT_CACHE:
        return _MAT_CACHE[k]
    m = bpy.data.materials.new(name or "emit")
    nt, out = _nodes(m)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    _MAT_CACHE[k] = m
    return m


def anim_emissive(name, color, frames_on_off, strength=12.0):
    """Unique emissive material whose strength is keyed (flashers, screens)."""
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    nt.links.new(e.outputs[0], out.inputs[0])
    for f, on in frames_on_off:
        e.inputs[1].default_value = strength if on else 0.05
        e.inputs[1].keyframe_insert("default_value", frame=f)
    for fc in (m.node_tree.animation_data.action.fcurves
               if hasattr(m.node_tree.animation_data.action, "fcurves") and
               len(m.node_tree.animation_data.action.fcurves) else []):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'
    _constant_all(m.node_tree)
    return m


def _constant_all(idblock):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return
    act = ad.action
    curves = []
    if hasattr(act, "fcurves"):
        try:
            curves = list(act.fcurves)
        except Exception:
            curves = []
    if not curves:
        try:
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        curves.extend(bag.fcurves)
        except AttributeError:
            pass
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'


def _img(nt, path, non_color=False, proj_vec=None):
    t = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    t.image = img
    t.projection = 'BOX'
    t.projection_blend = 0.2
    if proj_vec is not None:
        nt.links.new(proj_vec, t.inputs["Vector"])
    return t


def pbr(tex_key, scale=0.25, tint=(1, 1, 1), rough_mul=1.0, wet=0.0, name=None,
        fallback=(0.3, 0.3, 0.32), bump=0.4):
    """World-space box-projected PBR material from a cached ambientCG set.

    wet > 0 darkens albedo and drops roughness with a puddle noise mask so the
    Eevee ray-traced reflections pick up the neon/flashing lights.
    """
    k = ("pbr", tex_key, scale, tint, rough_mul, wet)
    if k in _MAT_CACHE:
        return _MAT_CACHE[k]
    maps = A.texture_maps(tex_key)
    m = bpy.data.materials.new(name or f"pbr_{tex_key}")
    nt, out = _nodes(m)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(geo.outputs["Position"], mp.inputs["Vector"])
    vec = mp.outputs[0]
    col_out = None
    if "color" in maps:
        c = _img(nt, maps["color"], proj_vec=vec)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(c.outputs[0], mix.inputs["A"])
        mix.inputs["B"].default_value = (*tint, 1)
        col_out = mix.outputs["Result"]
    else:
        b.inputs["Base Color"].default_value = (*[f * t for f, t in zip(fallback, tint)], 1)
    rough_out = None
    if "rough" in maps:
        r = _img(nt, maps["rough"], non_color=True, proj_vec=vec)
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = rough_mul
        nt.links.new(r.outputs[0], mul.inputs[0])
        rough_out = mul.outputs[0]
    else:
        b.inputs["Roughness"].default_value = 0.6 * rough_mul
    if "normal" in maps:
        n = _img(nt, maps["normal"], non_color=True, proj_vec=vec)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = bump
        nt.links.new(n.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    if wet > 0:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.08
        noise.inputs["Detail"].default_value = 3
        nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.45
        ramp.color_ramp.elements[1].position = 0.6
        nt.links.new(noise.outputs[0], ramp.inputs[0])
        # roughness: mix(texture rough, 0.03, puddle*wet)
        rm = nt.nodes.new("ShaderNodeMix")
        rm.data_type = 'FLOAT'
        fac = nt.nodes.new("ShaderNodeMath")
        fac.operation = 'MULTIPLY'
        fac.inputs[1].default_value = wet
        nt.links.new(ramp.outputs[0], fac.inputs[0])
        nt.links.new(fac.outputs[0], rm.inputs["Factor"])
        if rough_out is not None:
            nt.links.new(rough_out, rm.inputs["A"])
        else:
            rm.inputs["A"].default_value = 0.6
        rm.inputs["B"].default_value = 0.03
        rough_out = rm.outputs["Result"]
        if col_out is not None:
            dk = nt.nodes.new("ShaderNodeMix")
            dk.data_type = 'RGBA'
            dk.blend_type = 'MULTIPLY'
            nt.links.new(fac.outputs[0], dk.inputs["Factor"])
            nt.links.new(col_out, dk.inputs["A"])
            dk.inputs["B"].default_value = (0.35, 0.37, 0.42, 1)
            col_out = dk.outputs["Result"]
    if col_out is not None:
        nt.links.new(col_out, b.inputs["Base Color"])
    if rough_out is not None:
        nt.links.new(rough_out, b.inputs["Roughness"])
    _MAT_CACHE[k] = m
    return m


def building_mat(base=(0.08, 0.09, 0.12), lit=0.4, warm=(1.0, 0.62, 0.3),
                 cool=(0.55, 0.75, 1.0), strength=3.0, name="tower", floors=3.4,
                 bay=2.6, seed=0.0):
    """Skyscraper facade: procedural window grid, random lit windows (warm/cool),
    concrete PBR between windows. Works on any axis-aligned scaled box."""
    k = ("bld", base, lit, warm, cool, strength, floors, bay, seed)
    if k in _MAT_CACHE:
        return _MAT_CACHE[k]
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    N = nt.nodes
    L = nt.links.new
    geo = N.new("ShaderNodeNewGeometry")
    sep = N.new("ShaderNodeSeparateXYZ"); L(geo.outputs["Position"], sep.inputs[0])
    nsep = N.new("ShaderNodeSeparateXYZ"); L(geo.outputs["Normal"], nsep.inputs[0])

    def math(op, a=None, b=None, va=None, vb=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        if a is not None: L(a, n.inputs[0])
        elif va is not None: n.inputs[0].default_value = va
        if b is not None: L(b, n.inputs[1])
        elif vb is not None: n.inputs[1].default_value = vb
        return n.outputs[0]

    # horizontal coordinate: use y on X-facing faces, x on Y-facing faces
    ax = math('ABSOLUTE', nsep.outputs[0])
    hsel = math('GREATER_THAN', ax, vb=0.5)
    mixh = N.new("ShaderNodeMix"); mixh.data_type = 'FLOAT'
    L(hsel, mixh.inputs["Factor"]); L(sep.outputs[0], mixh.inputs["A"]); L(sep.outputs[1], mixh.inputs["B"])
    h = mixh.outputs["Result"]
    z = sep.outputs[2]
    hu = math('DIVIDE', h, vb=bay)
    zv = math('DIVIDE', z, vb=floors)
    fu = math('FRACT', hu)
    fv = math('FRACT', zv)
    # window rectangle mask
    m1 = math('GREATER_THAN', fu, vb=0.18)
    m2 = math('LESS_THAN', fu, vb=0.82)
    m3 = math('GREATER_THAN', fv, vb=0.22)
    m4 = math('LESS_THAN', fv, vb=0.78)
    win = math('MULTIPLY', math('MULTIPLY', m1, m2), math('MULTIPLY', m3, m4))
    # not on roofs / floors
    az = math('ABSOLUTE', nsep.outputs[2])
    side = math('LESS_THAN', az, vb=0.5)
    win = math('MULTIPLY', win, side)
    # cell id -> random
    cu = math('FLOOR', hu); cv = math('FLOOR', zv)
    comb = N.new("ShaderNodeCombineXYZ")
    L(cu, comb.inputs[0]); L(cv, comb.inputs[1])
    oi = N.new("ShaderNodeObjectInfo")
    rnd_obj = math('ADD', oi.outputs["Random"], vb=seed)
    L(math('MULTIPLY', rnd_obj, vb=97.0), comb.inputs[2])
    wn = N.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = '3D'
    L(comb.outputs[0], wn.inputs["Vector"])
    litmask = math('LESS_THAN', wn.outputs["Value"], vb=lit)
    on = math('MULTIPLY', win, litmask)
    # warm / cool tint per window + brightness variation
    sepc = N.new("ShaderNodeSeparateColor"); L(wn.outputs["Color"], sepc.inputs[0])
    tint = N.new("ShaderNodeMix"); tint.data_type = 'RGBA'
    L(math('GREATER_THAN', sepc.outputs[0], vb=0.78), tint.inputs["Factor"])
    tint.inputs["A"].default_value = (*warm, 1); tint.inputs["B"].default_value = (*cool, 1)
    bright = math('MULTIPLY', math('ADD', sepc.outputs[1], vb=0.35), vb=strength)
    pw = N.new("ShaderNodeValue"); pw.name = "POWER"; pw.label = "POWER"; pw.outputs[0].default_value = 1.0
    estr = math('MULTIPLY', math('MULTIPLY', on, bright), pw.outputs[0])
    # facade base: concrete texture or flat
    b = N.new("ShaderNodeBsdfPrincipled")
    maps = A.texture_maps("concrete")
    if "color" in maps:
        mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.12,) * 3
        L(geo.outputs["Position"], mp.inputs[0])
        c = _img(nt, maps["color"], proj_vec=mp.outputs[0])
        mul = N.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs["Factor"].default_value = 1.0
        L(c.outputs[0], mul.inputs["A"]); mul.inputs["B"].default_value = (*[x * 2.2 for x in base], 1)
        basecol = mul.outputs["Result"]
    else:
        rgb = N.new("ShaderNodeRGB"); rgb.outputs[0].default_value = (*base, 1)
        basecol = rgb.outputs[0]
    # windows: dark glass when unlit
    glass = N.new("ShaderNodeMix"); glass.data_type = 'RGBA'
    L(win, glass.inputs["Factor"]); L(basecol, glass.inputs["A"])
    glass.inputs["B"].default_value = (0.02, 0.025, 0.035, 1)
    L(glass.outputs["Result"], b.inputs["Base Color"])
    rmix = N.new("ShaderNodeMix"); rmix.data_type = 'FLOAT'
    L(win, rmix.inputs["Factor"]); rmix.inputs["A"].default_value = 0.8; rmix.inputs["B"].default_value = 0.08
    L(rmix.outputs["Result"], b.inputs["Roughness"])
    L(tint.outputs["Result"], b.inputs["Emission Color"])
    L(estr, b.inputs["Emission Strength"])
    L(b.outputs[0], out.inputs[0])
    _MAT_CACHE[k] = m
    return m


def glow_crack_mat(base=(0.035, 0.03, 0.045), glow=(1.0, 0.25, 0.05), strength=10.0,
                   name="monster_skin", scale=0.5):
    """Monster skin: near-black rough stone with sparse glowing fissures (masked by noise
    so only some cracks burn) + a faint subsurface-like glow in the deepest cracks."""
    k = ("crack", base, glow, strength, scale, name)
    if k in _MAT_CACHE:
        return _MAT_CACHE[k]
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    N = nt.nodes; L = nt.links.new
    tc = N.new("ShaderNodeTexCoord")
    v = N.new("ShaderNodeTexVoronoi"); v.feature = 'DISTANCE_TO_EDGE'
    v.inputs["Scale"].default_value = scale * 3.0
    L(tc.outputs["Object"], v.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = 0.025
    ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    L(v.outputs["Distance"], ramp.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.2; nz.inputs["Detail"].default_value = 2
    L(tc.outputs["Object"], nz.inputs["Vector"])
    nr = N.new("ShaderNodeValToRGB")
    nr.color_ramp.elements[0].position = 0.45; nr.color_ramp.elements[1].position = 0.62
    L(nz.outputs[0], nr.inputs[0])
    mask = N.new("ShaderNodeMath"); mask.operation = 'MULTIPLY'
    L(ramp.outputs[0], mask.inputs[0]); L(nr.outputs[0], mask.inputs[1])
    b = N.new("ShaderNodeBsdfPrincipled")
    maps = A.texture_maps("rock")
    if "color" in maps:
        mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.35,) * 3
        L(tc.outputs["Object"], mp.inputs[0])
        c = _img(nt, maps["color"], proj_vec=mp.outputs[0])
        mul = N.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs["Factor"].default_value = 1.0
        L(c.outputs[0], mul.inputs["A"]); mul.inputs["B"].default_value = (*[x * 1.6 for x in base], 1)
        L(mul.outputs["Result"], b.inputs["Base Color"])
        if "normal" in maps:
            n = _img(nt, maps["normal"], non_color=True, proj_vec=mp.outputs[0])
            nm = N.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = 0.8
            L(n.outputs[0], nm.inputs["Color"]); L(nm.outputs[0], b.inputs["Normal"])
    else:
        b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Emission Color"].default_value = (*glow, 1)
    s = N.new("ShaderNodeMath"); s.operation = 'MULTIPLY'; s.inputs[1].default_value = strength
    L(mask.outputs[0], s.inputs[0])
    L(s.outputs[0], b.inputs["Emission Strength"])
    L(b.outputs[0], out.inputs[0])
    _MAT_CACHE[k] = m
    return m


def volume_mat(density=0.05, color=(0.6, 0.65, 0.75), aniso=0.3, name="vol"):
    m = bpy.data.materials.new(name)
    nt, out = _nodes(m)
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = density
    v.inputs["Color"].default_value = (*color, 1)
    v.inputs["Anisotropy"].default_value = aniso
    nt.links.new(v.outputs[0], out.inputs["Volume"])
    return m


# --------------------------------------------------------------------------- world

def world(hdri_key="city_night", strength=0.25, tint=(0.35, 0.45, 0.8),
          fog=0.006, fog_color=(0.55, 0.62, 0.8), aniso=0.55):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs[1].default_value = strength
    path = A.hdri_path(hdri_key)
    if path:
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(path, check_existing=True)
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs["Factor"].default_value = 1.0
        nt.links.new(env.outputs[0], mul.inputs["A"])
        mul.inputs["B"].default_value = (*tint, 1)
        nt.links.new(mul.outputs["Result"], bg.inputs[0])
    else:
        bg.inputs[0].default_value = (0.01, 0.015, 0.04, 1)
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if fog > 0:
        v = nt.nodes.new("ShaderNodeVolumePrincipled")
        v.inputs["Density"].default_value = fog
        v.inputs["Color"].default_value = (*fog_color, 1)
        v.inputs["Anisotropy"].default_value = aniso
        nt.links.new(v.outputs[0], out.inputs["Volume"])
    w["bg_node"] = bg.name
    return w


def lightning(frames, peak=4.0):
    """Key world background strength spikes (lightning flashes)."""
    w = bpy.context.scene.world
    bg = w.node_tree.nodes[w["bg_node"]]
    base = bg.inputs[1].default_value
    for f in frames:
        for df, val in ((-1, base), (0, peak), (1, base * 2), (2, peak * 0.7), (4, base)):
            bg.inputs[1].default_value = val
            bg.inputs[1].keyframe_insert("default_value", frame=f + df)
    bg.inputs[1].default_value = base


# --------------------------------------------------------------------------- lights

def light(kind, loc, energy, color=(1, 1, 1), size=0.5, rot=(0, 0, 0), spot=45,
          blend=0.3, name="L", target=None, shadow=True, volume=1.0):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    ld.use_shadow = shadow
    if hasattr(ld, "volume_factor"):
        ld.volume_factor = volume
    if kind in ('POINT', 'SPOT'):
        ld.shadow_soft_size = size
    if kind == 'AREA':
        ld.size = size
    if kind == 'SPOT':
        ld.spot_size = math.radians(spot)
        ld.spot_blend = blend
    o = bpy.data.objects.new(name, ld)
    coll("lights").objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    if target is not None:
        aim(o, target)
    return o


def aim(o, target):
    d = Vector(target) - Vector(o.location)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


# ---------------------------------------------------------------------------- props

PAL = {
    "asphalt": (0.05, 0.05, 0.06), "white": (0.85, 0.86, 0.88),
    "black": (0.015, 0.015, 0.02), "police": (0.03, 0.05, 0.12),
    "red": (0.8, 0.05, 0.04), "blue": (0.05, 0.2, 0.9), "yellow": (0.95, 0.7, 0.05),
    "orange": (0.95, 0.35, 0.05), "grey": (0.25, 0.26, 0.28), "steel": (0.4, 0.42, 0.45),
}


def police_car(loc, rot_z=0.0, frame_range=(1, 200), seed=0, lights=True, name="cop"):
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    body = plastic(PAL["police"], 0.25)
    white = plastic(PAL["white"], 0.3)
    glass = plastic((0.02, 0.03, 0.05), 0.05)
    tire = plastic(PAL["black"], 0.7, coat=0)
    box(f"{name}_body", (0, 0, 0.55), (4.4, 1.9, 0.7), body, root, bevel=0.06)
    box(f"{name}_door", (0, 0, 0.6), (2.0, 1.92, 0.5), white, root, bevel=0.04)
    box(f"{name}_cab", (-0.2, 0, 1.15), (2.3, 1.7, 0.6), glass, root, bevel=0.06)
    for i, (x, y) in enumerate(((1.4, 0.95), (1.4, -0.95), (-1.4, 0.95), (-1.4, -0.95))):
        cyl(f"{name}_w{i}", (x, y, 0.38), 0.38, 0.3, tire, root, rot=(math.pi / 2, 0, 0))
    # light bar with alternating flashers
    f0, f1 = frame_range
    rng = random.Random(seed)
    ph = rng.randint(0, 5)
    seq_r, seq_b = [], []
    f = f0 - 1
    i = ph
    while f <= f1 + 2:
        seq_r.append((f, i % 2 == 0)); seq_b.append((f, i % 2 == 1))
        f += 3; i += 1
    mr = anim_emissive(f"{name}_red", (1, 0.04, 0.02), seq_r, 40)
    mb = anim_emissive(f"{name}_blue", (0.05, 0.25, 1), seq_b, 40)
    box(f"{name}_barR", (-0.2, 0.42, 1.52), (0.35, 0.7, 0.16), mr, root)
    box(f"{name}_barB", (-0.2, -0.42, 1.52), (0.35, 0.7, 0.16), mb, root)
    box(f"{name}_head", (2.21, 0, 0.6), (0.05, 1.5, 0.15), emissive((1, 0.95, 0.85), 20), root)
    box(f"{name}_tail", (-2.21, 0, 0.65), (0.05, 1.5, 0.12), emissive((1, 0.05, 0.02), 8), root)
    if lights:
        for col, seq, y in (((1, 0.05, 0.03), seq_r, 0.5), ((0.1, 0.3, 1), seq_b, -0.5)):
            L = light('POINT', (0, 0, 0), 0, col, 0.2, name=f"{name}_pl")
            L.parent = root
            L.location = (-0.2, y, 2.0)
            for fr, on in seq:
                L.data.energy = 900 if on else 0
                L.data.keyframe_insert("energy", frame=fr)
            _constant_all(L.data)
        hl = light('SPOT', (0, 0, 0), 600, (1, 0.95, 0.85), 0.2, spot=50, name=f"{name}_hl")
        hl.parent = root
        hl.location = (2.4, 0, 0.7)
        hl.rotation_euler = (0, math.radians(-95), 0)
    return root


def sedan(loc, rot_z=0.0, color=(0.5, 0.1, 0.1), name="car", lit=True):
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    box(f"{name}_b", (0, 0, 0.55), (4.2, 1.85, 0.65), plastic(color, 0.25), root, bevel=0.06)
    box(f"{name}_c", (-0.3, 0, 1.1), (2.2, 1.65, 0.55), plastic((0.03, 0.04, 0.06), 0.05), root, bevel=0.06)
    tire = plastic(PAL["black"], 0.7, coat=0)
    for i, (x, y) in enumerate(((1.35, 0.93), (1.35, -0.93), (-1.35, 0.93), (-1.35, -0.93))):
        cyl(f"{name}_w{i}", (x, y, 0.36), 0.36, 0.28, tire, root, rot=(math.pi / 2, 0, 0))
    if lit:
        box(f"{name}_hl", (2.11, 0, 0.62), (0.04, 1.4, 0.12), emissive((1, 0.95, 0.8), 15), root)
        box(f"{name}_tl", (-2.11, 0, 0.62), (0.04, 1.4, 0.1), emissive((1, 0.05, 0.02), 6), root)
    return root


def barrier(loc, rot_z=0.0, name="barrier"):
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    for i in range(4):
        col = PAL["orange"] if i % 2 == 0 else PAL["white"]
        box(f"{name}_s{i}", (-1.2 + i * 0.8, 0, 0.9), (0.8, 0.12, 0.3), plastic(col, 0.4), root)
    for x in (-1.3, 1.3):
        box(f"{name}_l{x}", (x, 0, 0.45), (0.12, 0.6, 0.9), plastic(PAL["grey"]), root)
    return root


def floodlight_tower(loc, aim_at, height=14.0, energy=60000, name="flood", color=(0.95, 0.97, 1.0),
                     spot=28):
    steel = plastic(PAL["steel"], 0.5, coat=0)
    root = empty(name, loc, collection="set")
    for dx, dy in ((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)):
        box(f"{name}_leg", (dx * 0.6, dy * 0.6, height / 2), (0.15, 0.15, height), steel, root)
    for z in range(2, int(height), 3):
        box(f"{name}_x{z}", (0, 0, z), (1.0, 1.0, 0.1), steel, root)
    head = empty(f"{name}_head", (0, 0, height + 0.8), root, collection="set")
    box(f"{name}_frame", (0, 0, 0), (2.6, 0.3, 1.6), steel, head)
    panel = emissive(color, 120, name=f"{name}_panel")
    for i in range(3):
        for j in range(2):
            box(f"{name}_p{i}{j}", (-0.85 + i * 0.85, 0.17, -0.4 + j * 0.8), (0.7, 0.05, 0.6), panel, head)
    world_head = Vector(loc) + Vector((0, 0, height + 0.8))
    d = Vector(aim_at) - world_head
    head.rotation_euler = (0, 0, math.atan2(d.y, d.x) - math.pi / 2)
    L = light('SPOT', world_head + d.normalized() * 1.0, energy, color, 0.6, spot=spot, blend=0.25,
              name=f"{name}_spot", target=aim_at, volume=2.5)
    return root, L


def fence(start, end, height=2.2, name="fence"):
    s, e = Vector(start), Vector(end)
    d = e - s
    n = max(2, int(d.length / 2.5))
    mat = plastic(PAL["steel"], 0.5, coat=0)
    ang = math.atan2(d.y, d.x)
    for i in range(n + 1):
        p = s + d * (i / n)
        box(f"{name}_post", (p.x, p.y, height / 2), (0.1, 0.1, height), mat)
    mid = (s + e) / 2
    for z in (0.3, height * 0.55, height - 0.05):
        box(f"{name}_rail", (mid.x, mid.y, z), (d.length, 0.06, 0.06), mat, rot=(0, 0, ang))
    # mesh panel (thin wire look)
    box(f"{name}_mesh", (mid.x, mid.y, height / 2), (d.length, 0.02, height * 0.95),
        plastic((0.3, 0.32, 0.35), 0.6, coat=0), rot=(0, 0, ang))


def crane(loc, height=70, jib=50, rot_z=0.3, name="crane"):
    mat = plastic((0.75, 0.5, 0.05), 0.5, coat=0)
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    box(f"{name}_mast", (0, 0, height / 2), (2, 2, height), mat, root)
    box(f"{name}_jib", (jib * 0.35, 0, height + 1), (jib, 1.2, 1.2), mat, root)
    box(f"{name}_cj", (-10, 0, height + 1), (14, 1.2, 1.2), mat, root)
    box(f"{name}_cw", (-15, 0, height - 0.5), (4, 2.5, 3), plastic(PAL["grey"]), root)
    box(f"{name}_cable", (jib * 0.6, 0, height - 12), (0.1, 0.1, 26), plastic(PAL["black"]), root)
    box(f"{name}_tip", (jib * 0.85, 0, height + 2), (0.4, 0.4, 0.4), emissive((1, 0.1, 0.05), 60), root)
    return root


def pylon(loc, height=45, rot_z=0.0, name="pylon"):
    mat = plastic((0.3, 0.32, 0.35), 0.6, coat=0)
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    for dx in (-2, 2):
        for dy in (-2, 2):
            box(f"{name}_leg", (dx * 0.6, dy * 0.6, height / 2), (0.4, 0.4, height), mat, root,
                rot=(math.radians(-dy), math.radians(dx), 0))
    for z, w in ((height * 0.6, 14), (height * 0.8, 10), (height, 6)):
        box(f"{name}_arm", (0, 0, z), (w, 0.5, 0.5), mat, root)
    box(f"{name}_beacon", (0, 0, height + 1), (0.5, 0.5, 0.5), emissive((1, 0.08, 0.04), 50), root)
    return root


def streetlamp(loc, rot_z=0.0, name="lamp", color=(1.0, 0.7, 0.4), energy=1500):
    mat = plastic(PAL["grey"], 0.5, coat=0)
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    box(f"{name}_pole", (0, 0, 3.5), (0.18, 0.18, 7), mat, root)
    box(f"{name}_arm", (0.8, 0, 7), (1.8, 0.15, 0.15), mat, root)
    box(f"{name}_bulb", (1.6, 0, 6.85), (0.6, 0.3, 0.12), emissive(color, 40), root)
    L = light('SPOT', (0, 0, 0), energy, color, 0.3, spot=80, blend=0.6, name=f"{name}_L", volume=1.5)
    L.parent = root
    L.location = (1.6, 0, 6.7)
    return root


def water_tank(loc, name="tank"):
    wood = pbr("wood", 0.6, tint=(0.6, 0.45, 0.35))
    root = empty(name, loc, collection="set")
    cyl(f"{name}_t", (0, 0, 4), 2, 3.5, wood, root, verts=16)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        box(f"{name}_leg", (dx, dy, 1.1), (0.15, 0.15, 2.2), plastic(PAL["steel"]), root)
    return root


def ac_unit(loc, name="ac"):
    box(name, (loc[0], loc[1], loc[2] + 0.6), (2.0, 1.4, 1.2), plastic((0.55, 0.57, 0.6), 0.5))
    box(name + "_fan", (loc[0], loc[1], loc[2] + 1.22), (1.2, 1.0, 0.05), plastic(PAL["black"]))


def crate(loc, size=1.2, rot_z=0.0, name="crate"):
    return box(name, (loc[0], loc[1], loc[2] + size / 2), (size,) * 3,
               pbr("wood", 0.9, tint=(0.8, 0.65, 0.45)), rot=(0, 0, rot_z), bevel=0.03)


def tree(loc, height=6, seed=0, name="tree", autumn=False):
    rng = random.Random(seed)
    trunk = plastic((0.18, 0.1, 0.05), 0.7, coat=0)
    pal = [(0.05, 0.18, 0.06), (0.04, 0.14, 0.05), (0.07, 0.22, 0.08)]
    if autumn:
        pal = [(0.5, 0.15, 0.03), (0.6, 0.3, 0.04), (0.35, 0.1, 0.03)]
    box(f"{name}_tr", (loc[0], loc[1], loc[2] + height * 0.3), (0.6, 0.6, height * 0.6), trunk)
    for i in range(3):
        s = (3.2 - i * 0.8) * height / 6
        box(f"{name}_c{i}", (loc[0] + rng.uniform(-.2, .2), loc[1] + rng.uniform(-.2, .2),
                             loc[2] + height * (0.55 + i * 0.17)),
            (s, s, s * 0.6), plastic(pal[i % 3], 0.6, coat=0.1), rot=(0, 0, rng.uniform(0, 1.5)), bevel=0.05)


# ----------------------------------------------------------------------------- sets

def ground(size=600, mat=None, z=0.0, name="ground"):
    return box(name, (0, 0, z - 0.5), (size, size, 1.0), mat or pbr("asphalt", 0.2, wet=0.9))


def tower(name, x, y, w, d, h, mat, crown=True):
    box(name, (x, y, h / 2), (w, d, h), mat)
    if crown and h > 40:
        box(name + "_crown", (x, y, h + 1.5), (w * 0.6, d * 0.6, 3), plastic(PAL["grey"], 0.6))
        box(name + "_beacon", (x, y, h + 3.3), (0.6, 0.6, 0.6), emissive((1, 0.06, 0.04), 60))


def city_grid(seed=1, radius=260, block=34, street=16, min_h=18, max_h=110, keep_clear=(),
              lit=0.38, skyline=True, boulevard=26):
    """Street grid of lit skyscrapers. keep_clear = [(x, y, r)] circles left open."""
    rng = random.Random(seed)
    mats = [building_mat(base=b, lit=lit, seed=i * 0.13, floors=f, bay=bw, name=f"tower{i}")
            for i, (b, f, bw) in enumerate((((0.07, 0.08, 0.1), 3.4, 2.6), ((0.1, 0.09, 0.08), 3.0, 2.2),
                                            ((0.06, 0.07, 0.09), 3.8, 3.0), ((0.09, 0.1, 0.12), 3.2, 1.8)))]
    pitch = block + street
    n = int(radius / pitch) + 1
    sidewalk = pbr("paving", 0.5, tint=(0.6, 0.6, 0.65), wet=0.6)
    count = 0
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            cx, cy = (i + 0.5) * pitch, (j + 0.5) * pitch
            if abs(cx) < boulevard + block / 2:
                cx += math.copysign(boulevard, cx)
            if math.hypot(cx, cy) > radius:
                continue
            if any(math.hypot(cx - kx, cy - ky) < kr for kx, ky, kr in keep_clear):
                continue
            box(f"walk_{i}_{j}", (cx, cy, 0.12), (block + 3, block + 3, 0.24), sidewalk)
            # 1-4 towers per block
            sub = rng.choice((1, 2, 2, 4))
            dist = math.hypot(cx, cy)
            hscale = 0.6 + 0.8 * min(1.0, dist / radius) if dist < 60 else 1.0
            for k in range(sub):
                if sub == 1:
                    bx, by, bw, bd = cx, cy, block - 2, block - 2
                elif sub == 2:
                    off = (block / 4) * (1 if k else -1)
                    bx, by, bw, bd = cx + off, cy, block / 2 - 1.5, block - 2
                else:
                    bx = cx + (block / 4) * (1 if k % 2 else -1)
                    by = cy + (block / 4) * (1 if k // 2 else -1)
                    bw = bd = block / 2 - 1.5
                h = rng.uniform(min_h, max_h) * hscale
                tower(f"bld_{i}_{j}_{k}", bx, by, bw, bd, h, rng.choice(mats))
                count += 1
    if skyline:
        far = building_mat(base=(0.04, 0.05, 0.07), lit=0.35, seed=7.7, name="far", strength=5)
        for k in range(70):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(radius + 40, radius + 260)
            w = rng.uniform(15, 40)
            tower(f"far_{k}", math.cos(a) * r, math.sin(a) * r, w, w, rng.uniform(40, 180), far)
    return count


def road_markings(extent=240, pitch=50):
    paint = emissive((0.9, 0.8, 0.4), 0.5, name="paint")
    white = emissive((0.8, 0.8, 0.85), 0.3, name="paintw")
    for k in range(-int(extent / 6), int(extent / 6)):
        box("mk", (0, k * 6, 0.02), (0.25, 2.5, 0.02), paint)            # boulevard centre
        for x in (-13, 13):
            box("mk", (x, k * 6, 0.02), (0.2, 1.5, 0.02), white)         # lane lines
    for i in range(-int(extent / pitch), int(extent / pitch) + 1):
        for k in range(-int(extent / 6), int(extent / 6)):
            if abs(k * 6) > 30:
                box("mk", (k * 6, i * pitch, 0.02), (2.5, 0.25, 0.02), paint)
    for i in range(-6, 7):  # zebra crossing at the hero's intersection
        box("zebra", (i * 2.2, -8, 0.02), (1.1, 4.5, 0.02), white)


def set_city_block(seed=3, frame_range=(1, 120), clear_radius=30):
    world("city_night", 0.35, (0.3, 0.42, 0.85), fog=0.0055)
    ground()
    city_grid(seed, keep_clear=[(0, 0, clear_radius)])
    road_markings()
    rng = random.Random(seed)
    for k in range(10):
        x = rng.choice((-25, 25)) if k % 2 else rng.uniform(-60, 60)
        y = rng.uniform(-60, 60) if k % 2 else rng.choice((-25, 25))
        streetlamp((x, y, 0.24), rot_z=rng.choice((0, math.pi)), name=f"lamp{k}")
    return {"hero": (0, 0, 0), "monster": (0, 70, 0), "street_n": (0, 40, 0), "street_s": (0, -40, 0),
            "alley": (-20, 8, 0), "car": (6, -6, 0)}


def set_plaza(seed=5, frame_range=(1, 120), water=True):
    world("street_night", 0.32, (0.3, 0.42, 0.85), fog=0.007)
    ground(mat=pbr("paving", 0.35, tint=(0.55, 0.55, 0.6), wet=0.8))
    city_grid(seed, radius=230, keep_clear=[(0, 0, 70)], max_h=120)
    marks = {"hero": (0, -12, 0), "monster": (0, 80, 0), "fountain": (0, 0, 0), "barricade": (0, -30, 0)}
    if water:
        # canal / ring of water across the plaza (used by "can't cross water" stories)
        water_m = bpy.data.materials.new("water")
        nt, out = _nodes(water_m)
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        b.inputs["Base Color"].default_value = (0.01, 0.02, 0.035, 1)
        b.inputs["Roughness"].default_value = 0.02
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.5
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.08
        nt.links.new(nz.outputs[0], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        nt.links.new(b.outputs[0], out.inputs[0])
        box("canal", (0, 20, -0.3), (220, 14, 0.6), water_m)
        box("canal_edge1", (0, 12.6, 0.15), (220, 0.8, 0.3), plastic(PAL["grey"], 0.6))
        box("canal_edge2", (0, 27.4, 0.15), (220, 0.8, 0.3), plastic(PAL["grey"], 0.6))
        box("bridge", (0, 20, 0.4), (6, 16, 0.5), plastic((0.3, 0.3, 0.32), 0.6))
        marks.update({"canal": (0, 20, 0), "bridge": (0, 20, 0.6), "far_bank": (0, 34, 0)})
    for k, (x, y) in enumerate(((-30, -20), (30, -20), (-40, 45), (40, 45))):
        floodlight_tower((x, y, 0), (x * 0.2, y * 0.3 + 10, 0), name=f"flood{k}")
    return marks


def set_rooftop(seed=7, height=80, frame_range=(1, 120)):
    world("sky_night", 0.4, (0.35, 0.45, 0.9), fog=0.004)
    ground(z=0)
    city_grid(seed, keep_clear=[(0, 0, 25)], max_h=120)
    roof = pbr("concrete", 0.3, tint=(0.6, 0.6, 0.62), wet=0.7)
    box("roof_bld", (0, 0, height / 2), (40, 40, height), building_mat(name="roofbld", seed=0.5))
    box("roof", (0, 0, height + 0.15), (40.4, 40.4, 0.3), roof)
    for x, y, w, d in ((0, 20, 40.4, 0.6), (0, -20, 40.4, 0.6), (20, 0, 0.6, 40.4), (-20, 0, 0.6, 40.4)):
        box("parapet", (x, y, height + 0.8), (w, d, 1.0), roof)
    rng = random.Random(seed)
    for k in range(5):
        ac_unit((rng.uniform(-14, 14), rng.uniform(-14, 14), height + 0.3), f"ac{k}")
    water_tank((12, 12, height + 0.3))
    box("antenna", (-14, 14, height + 8), (0.3, 0.3, 16), plastic(PAL["steel"]))
    box("antenna_l", (-14, 14, height + 16.2), (0.5, 0.5, 0.5), emissive((1, 0.05, 0.03), 80))
    box("door_hut", (-12, -12, height + 1.8), (5, 4, 3.3), roof)
    box("door", (-12, -9.95, height + 1.4), (1.4, 0.1, 2.4), emissive((1, 0.75, 0.45), 6))
    light('SPOT', (-12, -9.2, height + 3.4), 800, (1, 0.7, 0.4), spot=90, name="doorlight",
          target=(-12, -4, height))
    z = height + 0.3
    return {"hero": (0, -6, z), "edge": (0, -19, z), "monster": (0, 75, 0), "door": (-12, -9, z),
            "tank": (12, 12, z), "roof_z": (0, 0, z)}


def set_subway(seed=9, frame_range=(1, 120)):
    world("metro", 0.15, (0.6, 0.65, 0.8), fog=0.012, fog_color=(0.7, 0.75, 0.8))
    tile = pbr("tiles", 0.5, tint=(0.75, 0.8, 0.78))
    con = pbr("concrete", 0.3, tint=(0.45, 0.45, 0.48), wet=0.4)
    L = 140
    box("platform", (0, 0, 0.5), (L, 10, 1.0), con)
    box("trackbed", (0, 10, -0.5), (L, 10, 1.0), pbr("rock", 0.5, tint=(0.4, 0.4, 0.4)))
    for y in (8, 12):
        box("rail", (0, y, 0.08), (L, 0.15, 0.15), plastic(PAL["steel"], 0.2))
    box("wall_back", (0, -5.5, 4), (L, 1, 8), tile)
    box("wall_far", (0, 15.5, 4), (L, 1, 8), tile)
    box("ceiling", (0, 5, 8.5), (L, 22, 1), con)
    box("edge_line", (0, 4.7, 1.01), (L, 0.4, 0.02), emissive((0.95, 0.75, 0.05), 2))
    for k in range(-6, 7):
        x = k * 11
        box(f"col{k}", (x, 3.5, 4.5), (0.8, 0.8, 7), tile)
        box(f"tube{k}", (x + 5, 0, 7.9), (4, 0.3, 0.12), emissive((0.85, 0.95, 1.0), 30))
        light('AREA', (x + 5, 0, 7.7), 250, (0.85, 0.95, 1.0), size=3, rot=(0, 0, 0), name=f"tl{k}")
    box("sign", (0, -4.9, 5.5), (6, 0.1, 1.0), emissive((0.1, 0.4, 1.0), 6))
    box("tunnel_mouth", (L / 2 + 1, 10, 4), (2, 12, 8), plastic(PAL["black"], 0.9, coat=0))
    return {"hero": (0, 0, 1.0), "tunnel": (L / 2, 10, 0), "monster": (60, 10, 0), "track": (0, 10, 0),
            "bench": (-10, -3, 1.0)}


def set_school(seed=11, frame_range=(1, 120)):
    world("moonless", 0.1, (0.4, 0.5, 0.9), fog=0.008)
    floor = pbr("tiles", 0.4, tint=(0.7, 0.7, 0.65), wet=0.2)
    wall = plastic((0.55, 0.6, 0.5), 0.7, coat=0)
    L = 80
    box("floor", (0, 0, -0.1), (L, 8, 0.2), floor)
    box("wall_l", (0, -4.2, 2.2), (L, 0.4, 4.4), wall)
    box("ceil", (0, 0, 4.5), (L, 9, 0.2), plastic((0.7, 0.7, 0.68), 0.8))
    rng = random.Random(seed)
    for k in range(-12, 13):
        x = k * 3
        col = rng.choice(((0.1, 0.3, 0.6), (0.6, 0.1, 0.1), (0.1, 0.45, 0.25)))
        box(f"locker{k}", (x, -3.7, 1.0), (0.95, 0.6, 2.0), plastic(col, 0.4), bevel=0.02)
        if k % 2 == 0:
            box(f"window{k}", (x, 4.2, 2.4), (2.4, 0.2, 2.2), plastic((0.02, 0.03, 0.06), 0.03))
            box(f"wframe{k}", (x, 4.3, 2.4), (2.6, 0.3, 2.4), wall)
        if k % 3 == 0:
            box(f"lamp{k}", (x, 0, 4.38), (1.6, 0.4, 0.05), emissive((0.9, 0.95, 1), 15))
            light('AREA', (x, 0, 4.3), 120, (0.9, 0.95, 1), size=1.5, name=f"sl{k}")
    box("exit_sign", (L / 2 - 2, 0, 4.1), (1.2, 0.1, 0.4), emissive((0.1, 1, 0.2), 10))
    box("wall_r_low", (0, 4.4, 0.6), (L, 0.4, 1.2), wall)
    # moonlight through windows
    light('SUN', (0, 30, 40), 0.6, (0.6, 0.7, 1.0), rot=(math.radians(-60), 0, math.radians(180)), name="moon")
    return {"hero": (0, 0, 0), "end": (L / 2 - 3, 0, 0), "monster": (0, 40, 0), "locker": (3, -3.2, 0)}


def set_forest(seed=13, frame_range=(1, 120), autumn=True):
    world("moonless", 0.25, (0.35, 0.45, 0.8), fog=0.02, fog_color=(0.6, 0.65, 0.8))
    ground(mat=pbr("ground", 0.3, tint=(0.4, 0.35, 0.3)))
    rng = random.Random(seed)
    for k in range(140):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(8, 110)
        tree((math.cos(a) * r, math.sin(a) * r, 0), rng.uniform(5, 12), seed + k, f"t{k}", autumn)
    light('SUN', (0, 0, 50), 0.5, (0.6, 0.7, 1.0), rot=(math.radians(35), 0, math.radians(30)), name="moon")
    return {"hero": (0, 0, 0), "clearing": (0, 0, 0), "monster": (0, 60, 0), "path": (0, -30, 0)}


def set_lab(seed=15, frame_range=(1, 120)):
    world("metro", 0.08, (0.5, 0.6, 0.8), fog=0.01)
    box("floor", (0, 0, -0.1), (40, 30, 0.2), pbr("metal_plate", 0.4, tint=(0.5, 0.5, 0.55), wet=0.3))
    wall = plastic((0.15, 0.17, 0.2), 0.5)
    box("wall_b", (0, 15, 4), (40, 0.4, 8), wall)
    box("wall_l", (-20, 0, 4), (0.4, 30, 8), wall)
    box("ceil", (0, 0, 8.1), (40, 30, 0.2), wall)
    rng = random.Random(seed)
    for k in range(6):
        x = -15 + k * 6
        box(f"desk{k}", (x, 8, 0.5), (4, 1.6, 1.0), plastic(PAL["grey"], 0.4))
        box(f"screen{k}", (x, 8.5, 1.6), (2.2, 0.1, 1.3), emissive(rng.choice(((0.1, 0.8, 1), (0.2, 1, 0.4))), 8))
    tank_glass = plastic((0.1, 0.6, 0.5), 0.05)
    for k, x in enumerate((-8, 8)):
        cyl(f"tank{k}", (x, 2, 3), 2, 6, emissive((0.1, 0.9, 0.6), 4), verts=20)
        light('POINT', (x, 0, 3), 400, (0.1, 1, 0.6), 1.0, name=f"tankL{k}")
    for k in range(4):
        box(f"strip{k}", (-15 + k * 10, 0, 7.95), (6, 0.4, 0.05), emissive((0.85, 0.95, 1), 12))
        light('AREA', (-15 + k * 10, 0, 7.8), 150, (0.85, 0.95, 1), size=3, name=f"ll{k}")
    box("door", (0, -14.8, 2.5), (5, 0.4, 5), pbr("metal", 0.4))
    return {"hero": (0, 0, 0), "console": (0, 7, 0), "door": (0, -13, 0), "monster": (0, -40, 0), "tank": (-8, 2, 0)}


def set_bunker(seed=17, frame_range=(1, 120)):
    world("metro", 0.05, (0.5, 0.5, 0.6), fog=0.015, fog_color=(0.75, 0.7, 0.6))
    con = pbr("concrete", 0.25, tint=(0.5, 0.5, 0.5), wet=0.3)
    box("floor", (0, 0, -0.1), (30, 14, 0.2), con)
    box("wall_l", (0, -7, 3), (30, 0.6, 6), con)
    box("wall_r", (0, 7, 3), (30, 0.6, 6), con)
    box("ceil", (0, 0, 6), (30, 14, 0.4), con)
    box("blast_door", (14.8, 0, 2.5), (0.6, 6, 5), pbr("metal_plate", 0.5, tint=(0.4, 0.4, 0.35)))
    box("door_wheel", (14.4, 0, 2.5), (0.2, 1.4, 1.4), plastic(PAL["yellow"], 0.4))
    rng = random.Random(seed)
    for k in range(8):
        crate((rng.uniform(-12, 10), rng.choice((-5.5, 5.5)), 0), rng.uniform(0.9, 1.6), rng.uniform(0, 1), f"cr{k}")
    for k in range(3):
        x = -10 + k * 10
        fr = frame_range
        seq = [(f, (f // 6) % 2 == 0) for f in range(fr[0] - 1, fr[1] + 6, 6)]
        box(f"warn{k}", (x, 0, 5.75), (0.6, 0.6, 0.3), anim_emissive(f"warn{k}", (1, 0.15, 0.02), seq, 30))
        L = light('POINT', (x, 0, 5.3), 0, (1, 0.2, 0.03), 0.3, name=f"warnL{k}")
        for f, on in seq:
            L.data.energy = 500 if on else 40
            L.data.keyframe_insert("energy", frame=f)
        _constant_all(L.data)
    return {"hero": (0, 0, 0), "door": (13, 0, 0), "monster": (40, 0, 0), "corner": (-12, -5, 0)}


SETS = {"city_block": set_city_block, "plaza": set_plaza, "rooftop": set_rooftop,
        "subway": set_subway, "school": set_school, "forest": set_forest,
        "lab": set_lab, "bunker": set_bunker}


# ----------------------------------------------------------------------- characters

class Rig:
    """Blocky figure built from pivot empties.

    root ─ hips ─ torso ─ neck ─ head(+face)
                       ├─ shoulder_L ─ arm_L ;  shoulder_R ─ arm_R
            ├─ leg_L ;  leg_R
    Units: ~2.1 tall. Faces are expression-controlled boxes (brows, eyes, mouth).
    """

    def __init__(self, name, palette, accessory="none", scale=1.0, skin=(0.95, 0.78, 0.3)):
        self.name = name
        self.s = scale
        p = palette
        shirt = plastic(p.get("shirt", (0.8, 0.15, 0.1)))
        pants = plastic(p.get("pants", (0.1, 0.15, 0.4)))
        skinm = plastic(skin, 0.35)
        dark = plastic((0.02, 0.02, 0.025), 0.3)
        white = plastic((0.95, 0.95, 0.95), 0.2)
        self.root = empty(f"{name}_root", collection="chars")
        self.root.scale = (scale,) * 3
        self.hips = empty(f"{name}_hips", (0, 0, 0.85), self.root, "chars")
        self.torso = empty(f"{name}_torso", (0, 0, 0), self.hips, "chars")
        C = "chars"
        box(f"{name}_body", (0, 0, 0.42), (0.75, 0.42, 0.8), shirt, self.torso, bevel=0.05, collection=C)
        box(f"{name}_belt", (0, 0, 0.04), (0.77, 0.44, 0.1), pants, self.torso, bevel=0.02, collection=C)
        if "stripe" in p:
            box(f"{name}_stripe", (0, -0.215, 0.5), (0.76, 0.02, 0.14), plastic(p["stripe"]), self.torso, collection=C)
        self.neck = empty(f"{name}_neck", (0, 0, 0.85), self.torso, C)
        self.head = empty(f"{name}_head", (0, 0, 0), self.neck, C)
        box(f"{name}_skull", (0, 0, 0.3), (0.62, 0.56, 0.58), skinm, self.head, bevel=0.08, collection=C)
        # face (front = -Y)
        self.eyes, self.pupils, self.brows = [], [], []
        for sx in (-1, 1):
            e = box(f"{name}_eye{sx}", (0.13 * sx, -0.282, 0.34), (0.15, 0.02, 0.16), white, self.head, collection=C)
            pu = box(f"{name}_pupil{sx}", (0.13 * sx, -0.295, 0.33), (0.08, 0.02, 0.1), dark, self.head, collection=C)
            b = box(f"{name}_brow{sx}", (0.13 * sx, -0.29, 0.47), (0.18, 0.03, 0.045), dark, self.head, collection=C)
            self.eyes.append(e); self.pupils.append(pu); self.brows.append(b)
        self.mouth = box(f"{name}_mouth", (0, -0.29, 0.15), (0.2, 0.02, 0.04), dark, self.head, collection=C)
        # accessories (secondary-motion pieces hang off a lag pivot)
        self.acc = None
        hair = plastic(p.get("hair", (0.15, 0.08, 0.04)), 0.5)
        if accessory == "cap":
            self.acc = empty(f"{name}_accp", (0, 0, 0.6), self.head, C)
            box(f"{name}_cap", (0, 0, 0.05), (0.66, 0.6, 0.14), plastic(p.get("hat", (0.1, 0.2, 0.7))), self.acc, bevel=0.03, collection=C)
            box(f"{name}_brim", (0, -0.38, 0.0), (0.5, 0.25, 0.04), plastic(p.get("hat", (0.1, 0.2, 0.7))), self.acc, collection=C)
        elif accessory == "hair":
            self.acc = empty(f"{name}_accp", (0, 0, 0.6), self.head, C)
            box(f"{name}_hair", (0, 0.05, 0.02), (0.68, 0.62, 0.16), hair, self.acc, bevel=0.04, collection=C)
            box(f"{name}_hairback", (0, 0.3, -0.2), (0.66, 0.1, 0.5), hair, self.acc, bevel=0.03, collection=C)
        elif accessory == "ponytail":
            self.acc = empty(f"{name}_accp", (0, 0.3, 0.45), self.head, C)
            box(f"{name}_hair", (0, -0.3, 0.17), (0.68, 0.62, 0.14), hair, self.acc, bevel=0.04, collection=C)
            box(f"{name}_tail", (0, 0.08, -0.25), (0.18, 0.16, 0.5), hair, self.acc, bevel=0.05, collection=C)
        elif accessory == "helmet":
            self.acc = empty(f"{name}_accp", (0, 0, 0.6), self.head, C)
            box(f"{name}_helm", (0, 0, 0.02), (0.7, 0.64, 0.22), plastic(p.get("hat", (0.95, 0.75, 0.05))), self.acc, bevel=0.06, collection=C)
            box(f"{name}_lamp", (0, -0.33, 0.02), (0.14, 0.04, 0.1), emissive((1, 0.95, 0.8), 30), self.acc, collection=C)
        elif accessory == "glasses":
            for sx in (-1, 1):
                box(f"{name}_gl{sx}", (0.13 * sx, -0.3, 0.34), (0.2, 0.02, 0.2), plastic((0.05, 0.05, 0.05), 0.2), self.head, collection=C)
            box(f"{name}_hair", (0, 0.05, 0.62), (0.66, 0.6, 0.1), hair, self.head, bevel=0.03, collection=C)
        # arms
        self.sh = {}
        self.arm = {}
        for side, sx in (("L", 1), ("R", -1)):
            sh = empty(f"{name}_sh{side}", (0.5 * sx, 0, 0.72), self.torso, C)
            box(f"{name}_arm{side}", (0, 0, -0.32), (0.24, 0.3, 0.7), shirt, sh, bevel=0.05, collection=C)
            box(f"{name}_hand{side}", (0, 0, -0.74), (0.22, 0.26, 0.18), skinm, sh, bevel=0.05, collection=C)
            self.sh[side] = sh
        self.leg = {}
        for side, sx in (("L", 1), ("R", -1)):
            lg = empty(f"{name}_leg{side}", (0.19 * sx, 0, 0.0), self.hips, C)
            box(f"{name}_thigh{side}", (0, 0, -0.4), (0.34, 0.4, 0.8), pants, lg, bevel=0.04, collection=C)
            box(f"{name}_shoe{side}", (0, -0.06, -0.8), (0.36, 0.52, 0.12), dark, lg, bevel=0.03, collection=C)
            self.leg[side] = lg
        self.parts = [o for o in bpy.data.objects if o.name.startswith(name + "_")]
        self.facing = 0.0

    # --- placement
    def place(self, frame, loc, facing_deg=None):
        set_loc(self.root, frame, loc)
        if facing_deg is not None:
            self.facing = facing_deg
            set_rot(self.root, frame, 0, 0, facing_deg)

    def face_point(self, frame, target):
        d = Vector(target) - self.root.location
        ang = math.degrees(math.atan2(d.y, d.x)) + 90  # front is -Y
        self.place(frame, tuple(self.root.location), ang)

    # --- expressions: neutral, fear, shock, determined, angry, happy, sad, sly
    EXPR = {
        "neutral": dict(brow=(0, 0.47, 0), mouth=(0.2, 0.04), pupil=1.0),
        "fear": dict(brow=(18, 0.5, 1), mouth=(0.16, 0.12), pupil=0.7),
        "shock": dict(brow=(0, 0.53, 0), mouth=(0.18, 0.18), pupil=0.55),
        "determined": dict(brow=(-16, 0.45, 0), mouth=(0.22, 0.03), pupil=1.0),
        "angry": dict(brow=(-26, 0.44, 0), mouth=(0.24, 0.06), pupil=0.9),
        "happy": dict(brow=(8, 0.49, 0), mouth=(0.26, 0.07), pupil=1.0),
        "sad": dict(brow=(22, 0.46, 0), mouth=(0.14, 0.03), pupil=1.0),
        "sly": dict(brow=(-10, 0.46, 0), mouth=(0.22, 0.05), pupil=1.0),
        "scream": dict(brow=(20, 0.52, 1), mouth=(0.2, 0.22), pupil=0.5),
    }

    def expr(self, frame, name, blend=3):
        e = self.EXPR.get(name, self.EXPR["neutral"])
        ang, z, _ = e["brow"]
        for i, b in enumerate(self.brows):
            sx = -1 if i == 0 else 1
            b.location.z = z
            b.rotation_euler = (0, math.radians(ang * sx), 0)
            b.keyframe_insert("location", frame=frame)
            b.keyframe_insert("rotation_euler", frame=frame)
        w, h = e["mouth"]
        self.mouth.scale = (w, 0.02, h)
        self.mouth.keyframe_insert("scale", frame=frame)
        for p in self.pupils:
            p.scale = (0.08 * e["pupil"], 0.02, 0.1 * e["pupil"])
            p.keyframe_insert("scale", frame=frame)

    def blink(self, frame):
        for e in self.eyes + self.pupils:
            sz = e.scale.z
            e.keyframe_insert("scale", frame=frame - 1)
            e.scale.z = sz * 0.1
            e.keyframe_insert("scale", frame=frame + 1)
            e.scale.z = sz
            e.keyframe_insert("scale", frame=frame + 3)

    def talk(self, f0, f1, base="neutral"):
        """Mouth flaps for dialogue (driven from line timing)."""
        e = self.EXPR.get(base, self.EXPR["neutral"])
        w, h = e["mouth"]
        rng = random.Random(f0)
        f = f0
        while f < f1:
            self.mouth.scale = (w, 0.02, h + rng.uniform(0.05, 0.12))
            self.mouth.keyframe_insert("scale", frame=f)
            self.mouth.scale = (w, 0.02, h)
            self.mouth.keyframe_insert("scale", frame=f + 2)
            f += rng.choice((3, 4, 5))

    def head_head_turn(self, frame, yaw=0, pitch=0, roll=0):
        set_rot(self.neck, frame, pitch, roll, yaw)

    def secondary(self, f0, f1):
        """Follow-through on the accessory: copy head motion, lagged & damped."""
        if not self.acc:
            return
        rng = random.Random(f0 + 7)
        for f in range(f0, f1 + 1, 3):
            set_rot(self.acc, f, rng.uniform(-6, 6), rng.uniform(-4, 4), 0)

    def pose(self, f, hips_z=0.85, torso=(0, 0, 0), neck=(0, 0, 0), shL=(0, 0, 0), shR=(0, 0, 0),
             legL=(0, 0, 0), legR=(0, 0, 0)):
        self.hips.location.z = hips_z
        self.hips.keyframe_insert("location", frame=f)
        set_rot(self.torso, f, *torso)
        set_rot(self.neck, f, *neck)
        set_rot(self.sh["L"], f, *shL)
        set_rot(self.sh["R"], f, *shR)
        set_rot(self.leg["L"], f, *legL)
        set_rot(self.leg["R"], f, *legR)

    def bounds_points(self):
        """Head box corners (world) for caption-safe-area tests."""
        return [o for o in self.parts if o.name.endswith("_skull")]


# ------------------------------------------------------------------- action library

def _path_point(path, t):
    a, b = Vector(path[0]), Vector(path[-1])
    return a.lerp(b, t)


def act(rig, action, f0, f1, **kw):
    """Apply a library action between f0..f1. kw: path=[(x,y,z),(x,y,z)], target=(x,y,z),
    expr=..., facing=deg. Uses anticipation/overshoot/follow-through where it reads."""
    f0, f1 = int(f0), int(f1)
    dur = max(2, f1 - f0)
    face = kw.get("facing")
    path = kw.get("path")
    target = kw.get("target")
    if path:
        p0, p1 = Vector(path[0]), Vector(path[-1])
        if face is None and (p1 - p0).length > 0.01:
            d = p1 - p0
            face = math.degrees(math.atan2(d.y, d.x)) + 90
        rig.place(f0, tuple(p0), face)
    elif "at" in kw:
        rig.place(f0, tuple(kw["at"]), face)
    elif face is not None:
        rig.place(f0, tuple(rig.root.location), face)
    if target is not None and not path:
        rig.face_point(f0, target)
    if kw.get("expr"):
        rig.expr(f0, kw["expr"])
    rng = random.Random(f0 * 31 + len(action))

    if action in ("idle", "talk", "listen"):
        for f in range(f0, f1 + 1, 12):
            k = (f - f0) / 12
            s = math.sin(k * 1.3)
            rig.pose(f, 0.85 + 0.01 * s, torso=(2 * s, 0, s * 1.5), neck=(0, 0, s * 4),
                     shL=(0, 4 + s * 2, 0), shR=(0, -4 - s * 2, 0))
        if action == "talk":
            rig.talk(f0 + 2, f1 - 2, kw.get("expr", "neutral"))
            for f in range(f0, f1, 14):  # gesture
                set_rot(rig.sh["R"], f + 6, -35 + rng.uniform(-10, 10), -10, 0)
                set_rot(rig.sh["R"], f + 13, -8, -4, 0)
        rig.blink(f0 + min(dur - 3, 9))
    elif action in ("walk", "run", "panic_run", "sneak"):
        speed = {"walk": 1.4, "run": 5.5, "panic_run": 6.0, "sneak": 0.8}[action]
        cyc = {"walk": 14, "run": 8, "panic_run": 7, "sneak": 20}[action]
        swing = {"walk": 28, "run": 55, "panic_run": 60, "sneak": 18}[action]
        lean = {"walk": 3, "run": 14, "panic_run": 10, "sneak": 18}[action]
        if path:
            p0, p1 = Vector(path[0]), Vector(path[-1])
        else:
            yaw = math.radians((face or rig.facing) - 90)
            p0 = rig.root.location.copy()
            p1 = p0 + Vector((math.cos(yaw), math.sin(yaw), 0)) * speed * dur / 24
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / dur
            ph = (f - f0) / cyc * math.tau
            s = math.sin(ph)
            set_loc(rig.root, f, tuple(p0.lerp(p1, t)))
            bob = abs(math.cos(ph)) * (0.08 if action != "walk" else 0.04)
            hipz = 0.85 + bob - (0.15 if action == "sneak" else 0)
            if action == "panic_run":
                arms = (-150 + 30 * math.sin(ph * 2), 20, 0)
                rig.pose(f, hipz, torso=(lean, 0, s * 6), neck=(-10, 0, s * 15),
                         shL=(arms[0], arms[1], 0), shR=(arms[0] + 20 * s, -arms[1], 0),
                         legL=(swing * s, 0, 0), legR=(-swing * s, 0, 0))
            else:
                rig.pose(f, hipz, torso=(lean, 0, s * 5), neck=(-lean * 0.5, 0, -s * 3),
                         shL=(-swing * s, 6, 0), shR=(swing * s, -6, 0),
                         legL=(swing * s * 0.9, 0, 0), legR=(-swing * s * 0.9, 0, 0))
        rig.secondary(f0, f1)
    elif action == "panic":
        for f in range(f0, f1 + 1, 3):
            j = rng.uniform(-1, 1)
            rig.pose(f, 0.83, torso=(-5, j * 4, j * 10), neck=(-15 + j * 10, 0, rng.uniform(-35, 35)),
                     shL=(-160 + j * 25, 25, 0), shR=(-150 - j * 25, -25, 0),
                     legL=(j * 8, 0, 0), legR=(-j * 8, 0, 0))
        rig.expr(f0, kw.get("expr", "scream"))
    elif action == "look_up":
        # anticipation dip, then lean back with overshoot, hold
        rig.pose(f0, 0.85)
        rig.pose(f0 + 3, 0.8, torso=(4, 0, 0), neck=(6, 0, 0))
        a = min(f0 + 10, f1)
        rig.pose(a, 0.86, torso=(-14, 0, 0), neck=(-42, 0, 0), shL=(0, 14, 0), shR=(0, -14, 0))
        rig.pose(min(a + 4, f1), 0.85, torso=(-11, 0, 0), neck=(-36, 0, 0), shL=(0, 10, 0), shR=(0, -10, 0))
        rig.pose(f1, 0.85, torso=(-12, 0, 0), neck=(-38, 0, 1), shL=(0, 11, 0), shR=(0, -11, 0))
        rig.expr(f0 + 3, kw.get("expr", "shock"))
        rig.blink(f0 + 2)
    elif action == "point":
        rig.pose(f0, 0.85)
        rig.pose(f0 + 3, 0.84, shR=(10, -5, 0))  # anticipation back
        a = min(f0 + 8, f1)
        rig.pose(a, 0.85, torso=(0, 0, -10), neck=(-5, 0, -8), shR=(-100, -5, 0))
        rig.pose(min(a + 3, f1), 0.85, torso=(0, 0, -8), neck=(-5, 0, -8), shR=(-88, -5, 0))
        rig.pose(f1, 0.85, torso=(0, 0, -8), neck=(-5, 0, -8), shR=(-90, -4, 0))
    elif action == "fall":
        rig.pose(f0, 0.85, torso=(10, 0, 0))
        m = f0 + max(3, dur // 3)
        rig.pose(m, 0.6, torso=(45, 0, 0), shL=(-120, 20, 0), shR=(-120, -20, 0), legL=(-20, 0, 0), legR=(30, 0, 0))
        rig.pose(min(m + 5, f1), 0.32, torso=(85, 0, 0), neck=(-50, 0, 0), shL=(-170, 30, 0), shR=(-160, -30, 0),
                 legL=(-5, 0, 0), legR=(10, 0, 0))
        rig.pose(min(m + 8, f1), 0.36, torso=(80, 0, 0), neck=(-45, 0, 0), shL=(-165, 30, 0), shR=(-160, -30, 0))
        rig.pose(f1, 0.34, torso=(82, 0, 0), neck=(-48, 0, 0), shL=(-168, 30, 0), shR=(-160, -30, 0))
        rig.expr(f0, "shock")
    elif action == "hide":
        rig.pose(f0, 0.85)
        a = min(f0 + 6, f1)
        rig.pose(a, 0.42, torso=(35, 0, 0), neck=(-25, 0, 0), shL=(-60, 30, 0), shR=(-60, -30, 0),
                 legL=(-80, 0, 0), legR=(-80, 0, 0))
        for f in range(a + 4, f1 + 1, 6):
            j = rng.uniform(-1, 1)
            rig.pose(f, 0.42 + 0.01 * j, torso=(36 + j, 0, 0), neck=(-25, 0, j * 4), shL=(-60, 30, 0),
                     shR=(-60, -30, 0), legL=(-80, 0, 0), legR=(-80, 0, 0))
        rig.expr(f0, kw.get("expr", "fear"))
    elif action == "grab":
        rig.pose(f0, 0.85)
        rig.pose(f0 + 4, 0.8, torso=(10, 0, 0), shL=(-30, 0, 0), shR=(-30, 0, 0))
        a = min(f0 + 9, f1)
        rig.pose(a, 0.82, torso=(18, 0, 0), shL=(-85, 0, 0), shR=(-85, 0, 0))
        rig.pose(f1, 0.85, torso=(-4, 0, 0), shL=(-55, 10, 0), shR=(-55, -10, 0))
        rig.expr(f0, kw.get("expr", "determined"))
    elif action == "climb":
        if path:
            p0, p1 = Vector(path[0]), Vector(path[-1])
        else:
            p0 = rig.root.location.copy(); p1 = p0 + Vector((0, 0, dur / 24 * 1.2))
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / dur
            s = math.sin((f - f0) / 10 * math.tau)
            set_loc(rig.root, f, tuple(p0.lerp(p1, t)))
            rig.pose(f, 0.85, torso=(-5, 0, 0), neck=(-20, 0, 0), shL=(-160 + 25 * s, 10, 0),
                     shR=(-160 - 25 * s, -10, 0), legL=(-40 - 30 * s, 0, 0), legR=(-40 + 30 * s, 0, 0))
        rig.expr(f0, kw.get("expr", "determined"))
    elif action == "turn":
        start = rig.facing
        end = kw.get("to", start + 180)
        rig.place(f0, tuple(rig.root.location), start)
        rig.head_head_turn(f0, 0)
        rig.head_head_turn(f0 + 3, 0, 0, (end - start) * 0.35)  # head leads
        m = min(f0 + 8, f1)
        rig.place(m, tuple(rig.root.location), end + (end - start) * 0.06)  # overshoot
        rig.head_head_turn(m, 0)
        rig.place(min(m + 4, f1), tuple(rig.root.location), end)
        rig.pose(f0, 0.85); rig.pose(m, 0.83); rig.pose(f1, 0.85)
    elif action in ("gasp", "react"):
        rig.pose(f0, 0.85)
        rig.pose(f0 + 3, 0.8, torso=(8, 0, 0), neck=(8, 0, 0))  # anticipation
        a = min(f0 + 7, f1)
        rig.pose(a, 0.88, torso=(-12, 0, 0), neck=(-14, 0, 0), shL=(-40, 30, 0), shR=(-40, -30, 0))
        rig.pose(min(a + 4, f1), 0.85, torso=(-8, 0, 0), neck=(-10, 0, 0), shL=(-30, 25, 0), shR=(-30, -25, 0))
        rig.pose(f1, 0.85, torso=(-7, 0, 0), neck=(-9, 0, 0), shL=(-28, 24, 0), shR=(-28, -24, 0))
        rig.expr(f0 + 3, kw.get("expr", "shock"))
    elif action == "freeze":
        rig.pose(f0, 0.85, torso=(2, 0, 0), shL=(0, 6, 0), shR=(0, -6, 0))
        rig.pose(f1, 0.85, torso=(2, 0, 0), shL=(0, 6, 0), shR=(0, -6, 0))
        rig.expr(f0, kw.get("expr", "fear"))
    elif action == "shush":
        rig.pose(f0, 0.85)
        a = min(f0 + 6, f1)
        rig.pose(a, 0.85, neck=(5, 0, 0), shR=(-120, 30, 25))
        rig.pose(f1, 0.85, neck=(5, 0, 0), shR=(-122, 30, 25))
        rig.expr(f0, kw.get("expr", "determined"))
    elif action == "cheer":
        for f in range(f0, f1 + 1, 4):
            k = ((f - f0) // 4) % 2
            rig.pose(f, 0.95 if k else 0.85, torso=(-6, 0, 0), neck=(-10, 0, 0),
                     shL=(-170, 15, 0), shR=(-170, -15, 0))
        rig.expr(f0, "happy")
    elif action == "kneel":
        rig.pose(f0, 0.85)
        a = min(f0 + 8, f1)
        rig.pose(a, 0.55, torso=(15, 0, 0), neck=(10, 0, 0), legL=(-90, 0, 0), legR=(0, 0, 0),
                 shL=(-20, 0, 0), shR=(-20, 0, 0))
        rig.pose(f1, 0.55, torso=(15, 0, 0), neck=(10, 0, 0), legL=(-90, 0, 0), legR=(0, 0, 0),
                 shL=(-20, 0, 0), shR=(-20, 0, 0))
    else:  # unknown -> idle
        act(rig, "idle", f0, f1)
    if kw.get("look_at") is not None:
        d = Vector(kw["look_at"]) - rig.root.location
        dist = d.length
        pitch = -math.degrees(math.atan2(d.z - 2, max(0.1, Vector((d.x, d.y)).length)))
        set_rot(rig.neck, f1, max(-45, min(20, pitch)), 0, 0)


# ----------------------------------------------------------------------- monsters

class Monster:
    """Procedural original giant. spec keys: kind (colossus|stalker|warden), height,
    glow colour, seed, eyes(n), spikes(bool), arm_len. Built from blocks so it
    shares the toy-brick language but at kaiju scale."""

    def __init__(self, spec, name="monster"):
        self.name = name
        self.spec = spec
        H = spec.get("height", 50)
        self.H = H
        kind = spec.get("kind", "colossus")
        glow = tuple(spec.get("glow", (1.0, 0.25, 0.05)))
        rng = random.Random(spec.get("seed", 1))
        skin = glow_crack_mat(tuple(spec.get("base", (0.035, 0.03, 0.045))), glow,
                              spec.get("glow_strength", 10), name=f"{name}_skin", scale=0.5)
        self.skin = skin
        eye = emissive(glow, 30, name=f"{name}_eye")
        self.eye_mat = eye
        dark = plastic((0.02, 0.02, 0.025), 0.6, coat=0)
        C = "monster"
        u = H / 50.0  # unit scale; designed at 50 tall
        self.u = u
        self.root = empty(f"{name}_root", collection=C)
        self.hips = empty(f"{name}_hips", (0, 0, 20 * u), self.root, C)
        self.torso = empty(f"{name}_torso", (0, 0, 0), self.hips, C)
        if kind == "stalker":
            # long low torso, 4 long legs, neck reaching forward
            box(f"{name}_body", (0, 0, 2 * u), (14 * u, 26 * u, 9 * u), skin, self.torso, bevel=0.3 * u, collection=C)
            self.neck = empty(f"{name}_neck", (0, -13 * u, 4 * u), self.torso, C)
            box(f"{name}_neckb", (0, -5 * u, 2 * u), (6 * u, 12 * u, 6 * u), skin, self.neck, collection=C,
                rot=(math.radians(20), 0, 0))
            self.head = empty(f"{name}_head", (0, -11 * u, 5 * u), self.neck, C)
        elif kind == "warden":
            # tall thin statue-like figure: long body, small head, very long arms
            box(f"{name}_body", (0, 0, 9 * u), (10 * u, 6 * u, 20 * u), skin, self.torso, bevel=0.3 * u, collection=C)
            box(f"{name}_chest", (0, -0.5 * u, 16 * u), (14 * u, 7 * u, 6 * u), skin, self.torso, bevel=0.3 * u, collection=C)
            self.neck = empty(f"{name}_neck", (0, 0, 19.5 * u), self.torso, C)
            self.head = empty(f"{name}_head", (0, 0, 0), self.neck, C)
        else:
            # colossus: massive hunched biped
            box(f"{name}_body", (0, 0, 7 * u), (18 * u, 11 * u, 16 * u), skin, self.torso, bevel=0.4 * u, collection=C)
            box(f"{name}_chest", (0, -1.5 * u, 14 * u), (22 * u, 12 * u, 9 * u), skin, self.torso, bevel=0.4 * u, collection=C)
            self.neck = empty(f"{name}_neck", (0, -2 * u, 18 * u), self.torso, C)
            self.head = empty(f"{name}_head", (0, 0, 0), self.neck, C)
        hw = {"stalker": 7, "warden": 5, "colossus": 9}[kind] * u
        box(f"{name}_skull", (0, -1 * u, 3 * u), (hw, hw * 1.1, hw * 0.8), skin, self.head, bevel=0.3 * u, collection=C)
        self.jaw = empty(f"{name}_jawp", (0, 1 * u, 0.4 * u), self.head, C)
        box(f"{name}_jaw", (0, -2.2 * u, -0.6 * u), (hw * 0.9, hw, hw * 0.28), skin, self.jaw, bevel=0.2 * u, collection=C)
        box(f"{name}_maw", (0, -1.6 * u, 0.9 * u), (hw * 0.75, hw * 0.8, 0.5 * u), emissive(glow, 6, name=f"{name}_maw"), self.head, collection=C)
        n_eyes = spec.get("eyes", 2)
        self.eyes = []
        for i in range(n_eyes):
            x = (i - (n_eyes - 1) / 2) * hw * 0.32
            zz = 3.6 * u + (0.8 * u if n_eyes > 2 and i % 2 else 0)
            self.eyes.append(box(f"{name}_eye{i}", (x, -1 * u - hw * 0.56, zz), (hw * 0.16, 0.3 * u, hw * 0.1), eye,
                                 self.head, collection=C))
        if spec.get("spikes", True):
            for i in range(7):
                z = (3 + i * 2.2) * u if kind != "stalker" else 6.5 * u
                y = 5.5 * u if kind != "stalker" else (-10 + i * 3.4) * u
                s = (2.5 + rng.uniform(0, 2.5)) * u
                box(f"{name}_spike{i}", (0, y, z), (s * 0.5, s * 0.5, s * 1.6), dark, self.torso,
                    rot=(math.radians(-30), math.radians(45), 0), collection=C)
                box(f"{name}_sglow{i}", (0, y + 0.3 * u, z), (s * 0.15, s * 0.52, s * 1.2), eye, self.torso,
                    rot=(math.radians(-30), math.radians(45), 0), collection=C)
        # arms
        arm_len = spec.get("arm_len", 1.0) * (26 if kind == "warden" else 20) * u
        self.sh, self.leg = {}, {}
        if kind != "stalker":
            for side, sx in (("L", 1), ("R", -1)):
                shz = 16 * u if kind == "colossus" else 17 * u
                shx = (12 if kind == "colossus" else 8) * u
                sh = empty(f"{name}_sh{side}", (shx * sx, -1 * u, shz), self.torso, C)
                box(f"{name}_arm{side}", (0, 0, -arm_len * 0.5), (5 * u, 5 * u, arm_len), skin, sh, bevel=0.3 * u, collection=C)
                box(f"{name}_fist{side}", (0, 0, -arm_len - 1.5 * u), (6.5 * u, 6.5 * u, 4 * u), skin, sh, bevel=0.3 * u, collection=C)
                for c in range(3):
                    box(f"{name}_claw{side}{c}", ((c - 1) * 2 * u, -2.5 * u, -arm_len - 4.5 * u), (0.9 * u, 0.9 * u, 3 * u),
                        dark, sh, collection=C)
                self.sh[side] = sh
            for side, sx in (("L", 1), ("R", -1)):
                lg = empty(f"{name}_leg{side}", (5 * u * sx, 0, 0), self.hips, C)
                box(f"{name}_thigh{side}", (0, 0, -10 * u), (7 * u, 8 * u, 20 * u), skin, lg, bevel=0.3 * u, collection=C)
                box(f"{name}_foot{side}", (0, -2 * u, -19.5 * u), (8.5 * u, 12 * u, 2 * u), skin, lg, bevel=0.2 * u, collection=C)
                self.leg[side] = lg
        else:
            self.hips.location.z = 22 * u
            for i, (lx, ly) in enumerate(((7, -10), (-7, -10), (7, 10), (-7, 10))):
                side = ("FL", "FR", "BL", "BR")[i]
                lg = empty(f"{name}_leg{side}", (lx * u, ly * u, 0), self.hips, C)
                box(f"{name}_thigh{side}", (lx * 0.4 * u, 0, -11 * u), (4 * u, 4 * u, 23 * u), skin, lg, bevel=0.2 * u, collection=C,
                    rot=(0, math.radians(-12 if lx > 0 else 12), 0))
                box(f"{name}_foot{side}", (lx * 0.6 * u, 0, -22 * u), (5 * u, 6 * u, 1.5 * u), skin, lg, collection=C)
                self.leg[side] = lg
        # eye light (so the monster lights fog/street in its glow colour)
        self.eye_light = light('SPOT', (0, 0, 0), 9000 * u * u, glow, 1.0, spot=40, blend=0.5,
                               name=f"{name}_eyeL", volume=0.5)
        self.eye_light.parent = self.head
        self.eye_light.location = (0, -hw * 0.9, 3.5 * u)
        self.eye_light.rotation_euler = (math.radians(100), 0, 0)
        self.glow_light = light('POINT', (0, 0, 0), 6000 * u * u, glow, 4 * u, name=f"{name}_glowL", volume=1.5)
        self.glow_light.parent = self.torso
        self.glow_light.location = (0, -10 * u, 12 * u)
        self.parts = [o for o in bpy.data.objects if o.name.startswith(name + "_") and o.type == 'MESH']
        self.kind = kind
        self.impacts = []  # (frame, world location) footfalls for shake/dust/audio

    def place(self, frame, loc, facing_deg=0):
        set_loc(self.root, frame, loc)
        set_rot(self.root, frame, 0, 0, facing_deg)

    def glow(self, frame, level):
        """0..1 multiplier on eye/crack glow (dims in light for 'dark-only' rules etc.)."""
        for m in (self.eye_mat,):
            n = m.node_tree.nodes.get("Emission")
            if n:
                n.inputs[1].default_value = 30 * level
                n.inputs[1].keyframe_insert("default_value", frame=frame)
        self.eye_light.data.energy = 9000 * self.u ** 2 * level
        self.eye_light.data.keyframe_insert("energy", frame=frame)

    def head_aim(self, frame, pitch=0, yaw=0):
        set_rot(self.neck, frame, pitch, 0, yaw)

    def _limb(self, side):
        """Arms for bipeds; front legs double as arms for four-legged monsters."""
        if side in self.sh:
            return self.sh[side]
        return self.leg.get("F" + side) or self.leg.get(side) or next(iter(self.leg.values()))

    def action(self, name, f0, f1, **kw):
        f0, f1 = int(f0), int(f1)
        dur = max(2, f1 - f0)
        u = self.u
        if "at" in kw:
            self.place(f0, kw["at"], kw.get("facing", 0))
        if name == "walk":
            path = kw.get("path")
            p0 = Vector(path[0]) if path else self.root.location.copy()
            p1 = Vector(path[-1]) if path else p0
            face = kw.get("facing")
            if face is None and (p1 - p0).length > 0.1:
                d = p1 - p0
                face = math.degrees(math.atan2(d.y, d.x)) + 90
            face = face or 0
            cyc = kw.get("cycle", 30)  # frames per step pair: slow & heavy
            for f in range(f0, f1 + 1, 2):
                t = (f - f0) / dur
                ph = (f - f0) / cyc * math.tau
                s = math.sin(ph)
                set_loc(self.root, f, tuple(p0.lerp(p1, t)))
                set_rot(self.root, f, 0, 0, face)
                if self.kind == "stalker":
                    for i, sd in enumerate(("FL", "BR", "FR", "BL")):
                        sg = s if i < 2 else -s
                        set_rot(self.leg[sd], f, 20 * sg, 0, 0)
                    set_rot(self.torso, f, 2 * s, 3 * s, 0)
                    self.hips.location.z = 22 * u + abs(s) * 0.8 * u
                else:
                    set_rot(self.leg["L"], f, 22 * s, 0, 0)
                    set_rot(self.leg["R"], f, -22 * s, 0, 0)
                    set_rot(self.sh["L"], f, -18 * s, 4, 0)
                    set_rot(self.sh["R"], f, 18 * s, -4, 0)
                    set_rot(self.torso, f, 8 + 2 * abs(s), 4 * s, 6 * s)
                    self.hips.location.z = 20 * u - abs(math.sin(ph)) * 1.2 * u
                self.hips.keyframe_insert("location", frame=f)
                set_rot(self.neck, f, -6 + 3 * math.sin(ph * 2), 0, 3 * s)
            # footfalls at every half-cycle
            f = f0 + cyc // 4
            while f <= f1:
                t = (f - f0) / dur
                self.impacts.append((f, tuple(p0.lerp(p1, t))))
                f += cyc // 2
        elif name == "roar":
            # anticipation (rear back), big open, shake, settle
            a = f0 + max(3, dur // 5)
            b = f0 + max(6, dur // 2)
            set_rot(self.torso, f0, 6, 0, 0); set_rot(self.neck, f0, 0, 0, 0)
            set_rot(self.jaw, f0, 0, 0, 0)
            set_rot(self.torso, a, -6, 0, 0); set_rot(self.neck, a, 18, 0, 0)
            set_rot(self.torso, b, 16, 0, 0); set_rot(self.neck, b, -32, 0, 0); set_rot(self.jaw, b, 38, 0, 0)
            if self.sh:
                set_rot(self.sh["L"], f0, 0, 5, 0); set_rot(self.sh["R"], f0, 0, -5, 0)
                set_rot(self.sh["L"], b, -40, 60, 0); set_rot(self.sh["R"], b, -40, -60, 0)
            for f in range(b + 2, f1 - 2, 2):
                j = random.Random(f).uniform(-1, 1)
                set_rot(self.neck, f, -32 + j * 3, j * 2, j * 3)
                set_rot(self.jaw, f, 36 + j * 4, 0, 0)
            set_rot(self.jaw, f1, 10, 0, 0); set_rot(self.neck, f1, -10, 0, 0)
            self.glow(f0, 0.8); self.glow(b, 1.6); self.glow(f1, 1.0)
            self.roar_frame = b
            self.impacts.append((b, tuple(self.root.location)))
        elif name == "stomp":
            m = f0 + max(4, dur // 2)
            lg = self._limb(kw.get("side", "R")) if self.kind == "stalker" else self.leg[kw.get("side", "R")]
            set_rot(lg, f0, 0, 0, 0)
            set_rot(lg, m - 3, -35, 0, 0)
            set_rot(lg, m, 5, 0, 0)
            set_rot(lg, f1, 0, 0, 0)
            self.impacts.append((m, tuple(self.root.location)))
        elif name == "swipe" or name == "reach":
            side = kw.get("side", "R")
            a = f0 + max(3, dur // 3)
            lm = self._limb(side)
            big = 1.0 if self.sh else 0.5
            set_rot(lm, f0, 0, 0, 0)
            set_rot(lm, a, 40 * big, -20 if side == "R" else 20, 0)  # wind-up
            set_rot(lm, min(a + 5, f1), -110 * big, 10, 0)
            set_rot(lm, f1, -95 * big, 8, 0)
            set_rot(self.torso, a, 4, 0, 10 if side == "R" else -10)
            set_rot(self.torso, min(a + 5, f1), 20, 0, -18 if side == "R" else 18)
            if name == "swipe":
                self.impacts.append((min(a + 5, f1), tuple(self.root.location)))
        elif name == "freeze":
            # hold exactly: keys the current pose at f0 and f1 (constant)
            for o in [self.root, self.torso, self.neck, self.jaw] + list(self.sh.values()) + list(self.leg.values()):
                o.keyframe_insert("rotation_euler", frame=f0)
                o.keyframe_insert("rotation_euler", frame=f1)
            self.root.keyframe_insert("location", frame=f0)
            self.root.keyframe_insert("location", frame=f1)
        elif name == "lurk":
            for f in range(f0, f1 + 1, 8):
                s = math.sin((f - f0) / 24 * 2)
                set_rot(self.torso, f, 10 + s * 2, 0, s * 3)
                set_rot(self.neck, f, -10 + s * 4, 0, s * 8)
        elif name == "collapse":
            set_rot(self.torso, f0, 8, 0, 0)
            m = f0 + dur // 2
            set_rot(self.torso, m, 40, 0, 8)
            set_rot(self.root, f1, math.degrees(0), 0, self.root.rotation_euler.z * 57.3)
            self.hips.location.z = 20 * u; self.hips.keyframe_insert("location", frame=f0)
            self.hips.location.z = 4 * u; self.hips.keyframe_insert("location", frame=f1)
            set_rot(self.torso, f1, 80, 0, 10)
            self.glow(f0, 1.0); self.glow(f1, 0.0)
            self.impacts.append((f1, tuple(self.root.location)))
        elif name == "dissolve":
            self.glow(f0, 1.2); self.glow(f1, 0.0)
            for o in self.parts:
                o.keyframe_insert("scale", frame=f0)
            for o in self.parts:
                s = o.scale.copy()
                o.scale = (s.x * 0.01, s.y * 0.01, s.z * 0.01)
                o.keyframe_insert("scale", frame=f1)
                o.scale = s
        elif name == "idle":
            self.action("lurk", f0, f1)
        if kw.get("look_at") is not None:
            d = Vector(kw["look_at"]) - (self.root.location + Vector((0, 0, self.H * 0.85)))
            pitch = math.degrees(math.atan2(-d.z, max(1, Vector((d.x, d.y)).length)))
            set_rot(self.neck, f1, max(-10, min(55, pitch)), 0, 0)

    def head_world(self):
        bpy.context.view_layer.update()
        return self.head.matrix_world.translation.copy()


# ------------------------------------------------------------------------------- fx

def rain(center, frame_range, count=3500, area=40, height=22, name="rain"):
    """Particle rain: stretched thin streaks around the camera area (motion-blur friendly)."""
    drop_mat = emissive((0.7, 0.8, 1.0), 0.8, name="raindrop")
    drop = box("raindrop_src", (0, 0, -500), (0.015, 0.015, 0.7), drop_mat, collection="fx")
    emitter = box(f"{name}_emit", (center[0], center[1], center[2] + height), (area, area, 0.1),
                  None, collection="fx")
    emitter.hide_render = False
    emitter.display_type = 'WIRE'
    ps_mod = emitter.modifiers.new(name, 'PARTICLE_SYSTEM')
    ps = ps_mod.particle_system.settings
    ps.count = count
    ps.frame_start = frame_range[0] - 30
    ps.frame_end = frame_range[1]
    ps.lifetime = 30
    ps.emit_from = 'FACE'
    ps.normal_factor = 0
    ps.object_align_factor = (0, 0, -28)
    ps.effector_weights.gravity = 0
    ps.render_type = 'OBJECT'
    ps.instance_object = drop
    ps.particle_size = 1.0
    ps.use_rotation_instance = False
    ps.physics_type = 'NEWTON'
    emitter.show_instancer_for_render = False
    # rain also wets everything: drop roughness in pbr(wet) mats already
    return emitter


def particles(kind, center, frame_range, count=300, area=30, height=10, name=None):
    """embers (rising glow), dust (floating motes), leaves (falling, tumbling), ash, sparks."""
    name = name or kind
    cfg = {
        "embers": dict(mat=emissive((1, 0.45, 0.1), 30, name="ember"), size=(0.06, 0.06, 0.06), vel=(0, 0, 2.5), grav=-0.05, life=80, z=-height / 2),
        "dust": dict(mat=emissive((0.9, 0.9, 1.0), 2.0, name="mote"), size=(0.03, 0.03, 0.03), vel=(0.2, 0.1, 0.1), grav=0, life=200, z=0),
        "leaves": dict(mat=plastic((0.7, 0.3, 0.05), 0.6), size=(0.25, 0.2, 0.02), vel=(0.6, 0.2, -1.5), grav=0.02, life=150, z=height / 2),
        "ash": dict(mat=plastic((0.3, 0.3, 0.3), 0.8), size=(0.06, 0.06, 0.01), vel=(0.3, 0, -0.6), grav=0.0, life=200, z=height / 2),
        "sparks": dict(mat=emissive((1, 0.8, 0.3), 60, name="spark"), size=(0.03, 0.03, 0.2), vel=(0, 0, 6), grav=1.0, life=25, z=-height / 2),
    }[kind]
    src = box(f"{name}_src", (0, 0, -600), cfg["size"], cfg["mat"], collection="fx", bevel=0)
    em = box(f"{name}_emit", (center[0], center[1], center[2] + height / 2 + cfg["z"]), (area, area, height),
             None, collection="fx")
    em.display_type = 'WIRE'
    m = em.modifiers.new(name, 'PARTICLE_SYSTEM')
    ps = m.particle_system.settings
    ps.count = count
    ps.frame_start = frame_range[0] - cfg["life"]
    ps.frame_end = frame_range[1]
    ps.lifetime = cfg["life"]
    ps.emit_from = 'VOLUME'
    ps.normal_factor = 0
    ps.object_align_factor = cfg["vel"]
    ps.factor_random = 0.6
    ps.effector_weights.gravity = cfg["grav"]
    ps.render_type = 'OBJECT'
    ps.instance_object = src
    ps.use_rotations = True
    ps.rotation_factor_random = 1.0
    ps.angular_velocity_mode = 'RAND'
    ps.angular_velocity_factor = 3.0
    ps.size_random = 0.5
    em.show_instancer_for_render = False
    return em


def debris_burst(frame, loc, count=40, power=1.0, seed=0, size=0.8, rng_area=6):
    """Ballistic chunks of concrete/brick keyed by hand (no sim bake needed)."""
    rng = random.Random(seed + frame)
    mat = pbr("concrete", 0.5, tint=(0.6, 0.6, 0.6))
    hot = emissive((1, 0.4, 0.1), 15, name="hotdebris")
    for i in range(count):
        s = size * rng.uniform(0.3, 1.2) * power
        o = box(f"deb{frame}_{i}", loc, (s, s * rng.uniform(0.6, 1.4), s * rng.uniform(0.5, 1.2)),
                hot if rng.random() < 0.12 else mat, collection="fx", bevel=0)
        p0 = Vector(loc) + Vector((rng.uniform(-rng_area, rng_area), rng.uniform(-rng_area, rng_area), 0.5))
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.8, 2.0))) * 14 * power
        o.location = p0
        o.scale = (0.001,) * 3
        o.keyframe_insert("scale", frame=frame - 1)
        o.scale = (s, s, s)
        o.keyframe_insert("scale", frame=frame)
        for k in range(0, 40, 2):
            t = k / 24.0
            p = p0 + v * t + Vector((0, 0, -0.5 * 30 * t * t))
            if p.z < 0.2:
                p.z = 0.2
            o.location = p
            o.rotation_euler = (rng.uniform(0, 6) * t * 3, rng.uniform(0, 6) * t * 3, 0)
            o.keyframe_insert("location", frame=frame + k)
            o.keyframe_insert("rotation_euler", frame=frame + k)


def dust_cloud(frame, loc, radius=12, name="dust", duration=60, density=0.25):
    """Expanding volumetric dust ring at impacts."""
    m = volume_mat(density, (0.6, 0.58, 0.55), 0.2, name=f"{name}_vm{frame}")
    for i in range(3):
        a = i / 3 * math.tau
        o = sphere(f"{name}{frame}_{i}", (loc[0] + math.cos(a) * 3, loc[1] + math.sin(a) * 3, 2), 1, m, collection="fx")
        o.scale = (0.1,) * 3
        o.keyframe_insert("scale", frame=frame)
        o.scale = (radius, radius, radius * 0.35)
        o.keyframe_insert("scale", frame=frame + duration // 2)
        o.scale = (radius * 1.3, radius * 1.3, radius * 0.5)
        o.keyframe_insert("scale", frame=frame + duration)
    v = m.node_tree.nodes["Principled Volume"]
    v.inputs["Density"].default_value = 0.0
    v.inputs["Density"].keyframe_insert("default_value", frame=frame - 1)
    v.inputs["Density"].default_value = density
    v.inputs["Density"].keyframe_insert("default_value", frame=frame + 3)
    v.inputs["Density"].default_value = 0.0
    v.inputs["Density"].keyframe_insert("default_value", frame=frame + duration)


def fog_bank(loc, size, density=0.03, color=(0.6, 0.65, 0.8), name="fogbank"):
    return box(name, loc, size, volume_mat(density, color, 0.4, name=name), collection="fx")


def flicker_light(o, f0, f1, seed=0, lo=0.0, hi=None):
    """Random flicker (power cut / failing lights)."""
    rng = random.Random(seed)
    hi = hi if hi is not None else o.data.energy
    f = f0
    while f <= f1:
        o.data.energy = hi if rng.random() > 0.4 else lo
        o.data.keyframe_insert("energy", frame=f)
        f += rng.choice((1, 2, 3, 5))
    _constant_all(o.data)


def blackout(frame, keep=(), fade=2):
    """Kill every light (except names in keep) at frame -> for 'moves only in the dark'."""
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and not any(k in o.name for k in keep):
            o.data.keyframe_insert("energy", frame=frame - fade)
            e = o.data.energy
            o.data.energy = 0
            o.data.keyframe_insert("energy", frame=frame)
            o.data.energy = e


def lights_on(frame, names=(), energy=None):
    for o in bpy.data.objects:
        if o.type == 'LIGHT' and any(k in o.name for k in names):
            o.data.keyframe_insert("energy", frame=frame - 1)
            if energy:
                o.data.energy = energy
            o.data.keyframe_insert("energy", frame=frame)


# ----------------------------------------------------------- extra story props / fx

def city_power(keys):
    """keys: [(frame, level 0..1)] — dims every lit window in the city (blackouts)."""
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        n = m.node_tree.nodes.get("POWER")
        if n is None:
            continue
        for f, lv in keys:
            n.outputs[0].default_value = lv
            n.outputs[0].keyframe_insert("default_value", frame=f)
        _constant_all(m.node_tree) if len(keys) > 1 and keys[1][0] - keys[0][0] <= 2 else None


def fire_truck(loc, rot_z=0.0, frame_range=(1, 200), name="firetruck"):
    root = empty(name, loc, collection="set")
    root.rotation_euler = (0, 0, rot_z)
    red = plastic((0.7, 0.04, 0.03), 0.3)
    box(f"{name}_body", (0, 0, 1.3), (8.5, 2.5, 1.9), red, root, bevel=0.06)
    box(f"{name}_cab", (3.4, 0, 2.5), (1.8, 2.4, 1.2), plastic((0.03, 0.04, 0.06), 0.05), root, bevel=0.05)
    box(f"{name}_stripe", (0, 0, 1.0), (8.52, 2.52, 0.18), plastic((0.95, 0.85, 0.2), 0.3), root)
    box(f"{name}_ladder", (-0.8, 0, 2.55), (7.0, 0.9, 0.25), plastic((0.75, 0.76, 0.8), 0.3), root)
    tire = plastic(PAL["black"], 0.7, coat=0)
    for i, x in enumerate((2.9, -1.0, -3.0)):
        for y in (1.25, -1.25):
            cyl(f"{name}_w{i}{y}", (x, y, 0.5), 0.5, 0.4, tire, root, rot=(math.pi / 2, 0, 0))
    seq = [(f, (f // 3) % 2 == 0) for f in range(frame_range[0] - 1, frame_range[1] + 3, 3)]
    m = anim_emissive(f"{name}_bar", (1, 0.06, 0.03), seq, 40)
    box(f"{name}_bar", (3.4, 0, 3.2), (0.4, 2.0, 0.18), m, root)
    L = light('POINT', (0, 0, 0), 0, (1, 0.08, 0.04), 0.3, name=f"{name}_pl")
    L.parent = root; L.location = (3.4, 0, 3.8)
    for f, on in seq:
        L.data.energy = 1500 if on else 0
        L.data.keyframe_insert("energy", frame=f)
    _constant_all(L.data)
    return root


def rubble(start, end, width=8, height=3, seed=0, name="rubble", count=60):
    rng = random.Random(seed)
    s, e = Vector(start), Vector(end)
    mat = pbr("concrete", 0.4, tint=(0.55, 0.55, 0.55))
    dark = building_mat(name="rubble_bld", seed=0.9)
    for i in range(count):
        t = rng.random()
        p = s.lerp(e, t)
        d = (e - s).normalized()
        side = Vector((-d.y, d.x, 0))
        p += side * rng.uniform(-width / 2, width / 2)
        sz = rng.uniform(1.0, 4.0)
        box(f"{name}{i}", (p.x, p.y, rng.uniform(-0.5, height)), (sz, sz * rng.uniform(0.6, 1.6), sz * rng.uniform(0.5, 1.2)),
            mat if rng.random() < 0.7 else dark, rot=(rng.uniform(0, .6), rng.uniform(0, .6), rng.uniform(0, 3)))


def flood(level_keys, size=400, name="flood"):
    """Rising flood water plane: level_keys [(frame, z)]."""
    m = bpy.data.materials.new("floodwater")
    nt, out = _nodes(m)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.01, 0.02, 0.03, 1)
    b.inputs["Roughness"].default_value = 0.03
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.0
    bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.1
    nt.links.new(nz.outputs[0], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs[0])
    o = box(name, (0, 0, -1), (size, size, 0.2), m, collection="fx")
    for f, z in level_keys:
        o.location.z = z
        o.keyframe_insert("location", frame=f)
    return o


def steam(loc, frame, duration=40, radius=4, name="steam"):
    m = volume_mat(0.35, (0.9, 0.9, 0.95), 0.3, name=f"{name}{frame}")
    o = sphere(f"{name}{frame}", (loc[0], loc[1], loc[2] + 1), 1, m, collection="fx")
    o.scale = (0.2,) * 3
    o.keyframe_insert("scale", frame=frame)
    o.scale = (radius, radius, radius * 1.6)
    o.location.z = loc[2] + radius
    o.keyframe_insert("scale", frame=frame + duration)
    o.keyframe_insert("location", frame=frame + duration)
    return o


def spray(loc, frame_range, count=400, name="spray", height=8):
    """Hydrant / water-cannon spray: bright droplets shot upward under gravity."""
    drop = box(f"{name}_src", (0, 0, -600), (0.14, 0.14, 0.35), emissive((0.75, 0.85, 1.0), 6, name="spraydrop"),
               collection="fx")
    em = box(f"{name}_emit", tuple(loc), (0.4, 0.4, 0.2), None, collection="fx")
    em.display_type = 'WIRE'
    m = em.modifiers.new(name, 'PARTICLE_SYSTEM')
    ps = m.particle_system.settings
    ps.count = count
    ps.frame_start, ps.frame_end = frame_range[0] - 30, frame_range[1]
    ps.lifetime = 40
    ps.emit_from = 'FACE'
    ps.normal_factor = 0
    ps.object_align_factor = (0, 0, math.sqrt(2 * 9.8 * height))
    ps.factor_random = 2.0
    ps.effector_weights.gravity = 1.0
    ps.render_type = 'OBJECT'
    ps.instance_object = drop
    em.show_instancer_for_render = False
    return em
