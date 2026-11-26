"""Low-poly building blocks shared by the town builder (boxes, houses, fences, poles, wires, text, world)."""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import FONT
FONT_PATH = str(FONT)

rnd = random.Random(7)
STYLE = "A"


def set_style(style, seed=7):
    """'A' = flat muted low-poly; 'B' = semi-realistic textured world (palette colours -> textures)."""
    global STYLE, rnd
    STYLE = style
    rnd = random.Random(seed)
    _mats.clear()


def _tex_mat(m, hexcol, kind, scale):
    import texmap as textures
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale, 1 / scale, 1 / scale)
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(str(textures.TEX / f"{kind}.png"), check_existing=True)
    img.projection = "BOX"
    img.projection_blend = 0.25
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    sock = lambda coll, name, typ: next(x for x in coll if x.name == name and x.type == typ)
    sock(mix.inputs, "Factor", "VALUE").default_value = 1.0
    tint = textures.B_TINT.get(hexcol, hexcol)
    sock(mix.inputs, "A", "RGBA").default_value = srgb(tint) + [1]
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
    nt.links.new(img.outputs["Color"], sock(mix.inputs, "B", "RGBA"))
    nt.links.new(sock(mix.outputs, "Result", "RGBA"), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85 if kind != "water" else 0.25

# ---------------------------------------------------------------- helpers
_mats = {}


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]


def mat(hexcol, cull=False, emit=0.0):
    key = (hexcol, cull, emit)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f"M_{hexcol}_{int(cull)}_{emit}")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    col = srgb(hexcol) + [1]
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    if emit:
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = emit
    m.use_backface_culling = cull
    m.diffuse_color = col
    if STYLE == "B" and not emit:
        import texmap as textures
        if hexcol in textures.TEXMAP:
            kind, scale = textures.TEXMAP[hexcol]
            _tex_mat(m, hexcol, kind, scale)
        elif hexcol in textures.B_TINT:
            bsdf.inputs["Base Color"].default_value = srgb(textures.B_TINT[hexcol]) + [1]
    _mats[key] = m
    return m


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def multibox(name, boxes, parent=None, loc=(0, 0, 0), rot_z=0.0):
    """boxes: list of (sx, sy, sz, cx, cy, cz, hexcol[, rz]) ; one mesh, multi-material."""
    bm = bmesh.new()
    cols = []
    for b in boxes:
        sx, sy, sz, cx, cy, cz, col = b[:7]
        rz = b[7] if len(b) > 7 else 0.0
        if col not in cols:
            cols.append(col)
        mi = cols.index(col)
        res = bmesh.ops.create_cube(bm, size=1.0)
        vs = res["verts"]
        M = Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Diagonal((sx, sy, sz, 1))
        bmesh.ops.transform(bm, matrix=M, verts=vs)
        for f in {f for v in vs for f in v.link_faces}:
            f.material_index = mi
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for c in cols:
        me.materials.append(mat(c))
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    link(ob)
    if parent:
        ob.parent = parent
    return ob


def poly(name, verts, faces, col, loc=(0, 0, 0), rot_z=0.0, parent=None, cull=False, uvs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if uvs:
        uv = me.uv_layers.new()
        for li, l in enumerate(me.loops):
            uv.data[li].uv = uvs[l.vertex_index]
    me.update()
    me.materials.append(col if isinstance(col, bpy.types.Material) else mat(col, cull))
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    link(ob)
    if parent:
        ob.parent = parent
    return ob


def cyl(name, r, h, loc, col, seg=8, r2=None, parent=None, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bmesh.ops.translate(bm, vec=(0, 0, h / 2), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat(col))
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    link(ob)
    if parent:
        ob.parent = parent
    return ob


def empty(name, loc=(0, 0, 0), rot_z=0.0, parent=None):
    ob = bpy.data.objects.new(name, None)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    link(ob)
    if parent:
        ob.parent = parent
    return ob


_font = None


def text(name, body, loc, rot_z, size, col, parent=None, extrude=0.04):
    global _font
    if _font is None:
        _font = bpy.data.fonts.load(FONT_PATH)
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.font = _font
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extrude
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat(col))
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, rot_z)
    link(ob)
    if parent:
        ob.parent = parent
    return ob


def rz(deg):
    return math.radians(deg - 90)  # local +Y faces `deg`


# ---------------------------------------------------------------- town pieces
WALLS = ["#c8b08a", "#b9a07c", "#a88f72", "#cdbb98", "#9fa38a", "#b59a86", "#8fa0a8", "#c2a88a"]
ROOFS = ["#7a4a36", "#6a5040", "#5d4a3c", "#80563c", "#5a5f62", "#6e4434"]


def house(name, x, y, face_deg, w=7, d=7, h=3.6, wall=None, roof=None, door="#5b4030", sign=None, extra=None):
    root = empty(name, (x, y, 0), rz(face_deg))
    wall = wall or rnd.choice(WALLS)
    roof = roof or rnd.choice(ROOFS)
    boxes = [(w, d, h, 0, 0, h / 2, wall),
             (w + 0.3, d + 0.3, 0.3, 0, 0, 0.15, "#6d6252"),          # base
             (1.2, 0.2, 2.1, 0, d / 2 + 0.05, 1.05, door),             # door
             (1.5, 0.12, 0.2, 0, d / 2 + 0.08, 2.15, "#4a3a2c"),       # lintel
             (0.5, 0.5, 1.6, w * 0.3, -d * 0.2, h + 1.8, "#6e5e52")]   # chimney
    for sx in (-1, 1):  # windows
        boxes.append((1.1, 0.14, 1.0, sx * w * 0.3, d / 2 + 0.06, h * 0.55, "#4d5f6e"))
        boxes.append((1.3, 0.1, 0.12, sx * w * 0.3, d / 2 + 0.08, h * 0.55 - 0.56, "#e8e0cc"))
        boxes.append((0.1, 0.16, 1.0, sx * w * 0.3, d / 2 + 0.08, h * 0.55, "#e8e0cc"))
    for sy in (-1, 1):  # side windows
        boxes.append((0.14, 1.0, 0.9, sy * (w / 2 + 0.05), 0, h * 0.55, "#4d5f6e"))
    if extra:
        boxes += extra
    multibox(name + "_body", boxes, parent=root)
    # gable roof along local X
    o = 0.45
    rh = w * 0.42
    hw, hd = w / 2 + o, d / 2 + o
    vs = [(-hw, -hd, h - 0.05), (hw, -hd, h - 0.05), (hw, hd, h - 0.05), (-hw, hd, h - 0.05),
          (-hw, 0, h + rh), (hw, 0, h + rh)]
    # roof as 2 slabs: faces
    fs = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
    poly(name + "_roof", vs, fs, roof, parent=root)
    # gable infill (wall colour) to close triangles
    gv = [(-w / 2, -d / 2, h), (-w / 2, d / 2, h), (-w / 2, 0, h + rh - 0.4), (w / 2, -d / 2, h),
          (w / 2, d / 2, h), (w / 2, 0, h + rh - 0.4)]
    poly(name + "_gable", gv, [(0, 1, 2), (3, 5, 4)], wall, parent=root)
    if sign:
        multibox(name + "_signboard", [(3.6, 0.15, 0.9, 0, d / 2 + 0.12, h - 0.55, "#4f3a2a")], parent=root)
        text(name + "_signtext", sign, (0, d / 2 + 0.22, h - 0.55), math.pi, 0.55, "#efe6d0", parent=root)
    return root


def fence(name, p0, p1, col="#7d6448", h=1.1):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    ang = math.atan2(p1.y - p0.y, p1.x - p0.x)
    n = max(1, int(L / 1.6))
    boxes = []
    for i in range(n + 1):
        boxes.append((0.16, 0.16, h + 0.15, i * L / n, 0, (h + 0.15) / 2, col))
    for zz in (h * 0.4, h * 0.85):
        boxes.append((L, 0.08, 0.14, L / 2, 0, zz, "#8a7052"))
    multibox(name, boxes, loc=(p0.x, p0.y, 0), rot_z=ang)


def barrel(name, x, y):
    cyl(name, 0.45, 1.0, (x, y, 0), "#7a5636", seg=10)
    cyl(name + "_hoop", 0.47, 0.08, (x, y, 0.2), "#3f3a34", seg=10)
    cyl(name + "_hoop2", 0.47, 0.08, (x, y, 0.75), "#3f3a34", seg=10)


def lamp(name, x, y):
    cyl(name, 0.09, 4.2, (x, y, 0), "#3e3b38", seg=6)
    multibox(name + "_head", [(0.45, 0.45, 0.55, 0, 0, 4.4, "#3e3b38")], loc=(x, y, 0))
    multibox(name + "_glow", [(0.32, 0.32, 0.36, 0, 0, 4.38, "#f3dc9a")], loc=(x, y, 0.001))


def pole(name, x, y):
    cyl(name, 0.14, 8.0, (x, y, 0), "#5e4a38", seg=6)
    multibox(name + "_bar", [(0.15, 2.0, 0.15, 0, 0, 7.4, "#5e4a38")], loc=(x, y, 0))


def wire(name, a, b, sag=0.6):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.025
    cu.bevel_resolution = 0
    sp = cu.splines.new("POLY")
    n = 10
    sp.points.add(n)
    a, b = Vector(a), Vector(b)
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t)
        p.z -= sag * 4 * t * (1 - t)
        sp.points[i].co = (p.x, p.y, p.z, 1)
    ob = bpy.data.objects.new(name, cu)
    ob.data.materials.append(mat("#24201c"))
    link(ob)


def ground():
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "ground"
    g.data.materials.append(mat("#8c8a5c"))
    # dirt streets (slightly raised to avoid z-fighting)
    multibox("main_street", [(152, 8, 0.04, 0, 0, 0.02, "#a68a66")])
    multibox("carrot_street", [(6, 60, 0.04, 30, 34, 0.025, "#a68a66")])
    multibox("plaza", [(26, 26, 0.04, 66, 0, 0.03, "#b8a282")])
    # tracks in dirt
    multibox("ruts", [(150, 0.25, 0.01, 0, sy, 0.045, "#8f7656") for sy in (-1.4, 1.4)])
    # grass tufts / rocks scattered (merged)
    tufts = []
    for i in range(500):
        x, y = rnd.uniform(-120, 110), rnd.uniform(-90, 90)
        if abs(y) < 5 or (26 < x < 34 and y > 3) or (52 < x < 80 and abs(y) < 14) or x < -73:
            continue
        s = rnd.uniform(0.2, 0.5)
        tufts.append((s, s, s * 0.6, x, y, s * 0.3, rnd.choice(["#76784a", "#6b7044", "#858456"])))
    multibox("tufts", tufts)


def trees():
    pts = [(-60, -30), (-45, 28), (-8, -30), (12, 30), (42, -28), (55, 26), (-28, 32), (60, -22),
           (-55, 22), (18, -30), (45, 40), (15, 46), (48, 52), (12, 60), (-35, -28), (85, 20), (85, -20)]
    for i, (x, y) in enumerate(pts):
        h = rnd.uniform(2.2, 3.2)
        cyl(f"tree{i}", 0.3, h, (x, y, 0), "#5c4634", seg=6)
        multibox(f"tree{i}_top", [(2.8, 2.8, 2.4, 0, 0, h + 1.0, rnd.choice(["#5f6b3e", "#6a7244", "#56603a"])),
                                   (2.0, 2.0, 1.4, 0, 0, h + 2.6, "#6f7a48")], loc=(x, y, 0),
                 rot_z=rnd.uniform(0, 1))


# ---------------------------------------------------------------- world, lights, camera, render
def set_eevee(sc, samples=1):
    """Eevee across Blender versions (engine id is BLENDER_EEVEE in 5.x, BLENDER_EEVEE_NEXT in 4.2-4.5)."""
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    for k, v in (("taa_render_samples", samples), ("use_shadows", True), ("shadow_ray_count", 1), ("shadow_step_count", 1),
                 ("use_fast_gi", False), ("shadow_resolution_scale", 0.5)):
        try:
            setattr(sc.eevee, k, v)
        except (AttributeError, TypeError):
            pass


def world_and_render():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.name = "SKYRAMP"
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.name = "SKYBG"
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements.new(0.05)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.angle = math.radians(0.6)
    so = bpy.data.objects.new("sun", sun)
    link(so)
    cam = bpy.data.cameras.new("cam")
    cam.sensor_fit = "VERTICAL"
    cam.sensor_height = 24
    cam.clip_start = 0.05
    cam.clip_end = 700
    co = bpy.data.objects.new("cam", cam)
    link(co)
    sc.camera = co
    set_eevee(sc)
    sc.render.filter_size = 1.2
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.resolution_x = 540
    sc.render.resolution_y = 960
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.fps = 30


