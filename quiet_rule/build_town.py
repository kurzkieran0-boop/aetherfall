"""Build the low-poly town, interiors and blocky cast in Blender (bpy, headless). Saves build/town.blend."""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scene_lib import CAST, INT_KITCHEN, INT_HALL

FONT_PATH = os.path.join(HERE, "assets", "QRBlack.ttf")
FACES = os.path.join(HERE, "build", "faces")
rnd = random.Random(7)

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


def town():
    ground()
    k = 0
    # main street houses
    for x in range(-50, 51, 10):
        if x not in (-20, 30):
            house(f"house_n{k}", x + rnd.uniform(-0.6, 0.6), 14, -90, w=rnd.uniform(6.2, 7.6), d=7,
                  h=rnd.uniform(3.2, 4.2)); k += 1
        house(f"house_s{k}", x + rnd.uniform(-0.6, 0.6), -14, 90, w=rnd.uniform(6.2, 7.6), d=7,
              h=rnd.uniform(3.2, 4.2)); k += 1
    # bakery with striped awning + stall with sad bread
    aw = []
    for i in range(8):
        aw.append((0.6, 1.6, 0.12, -2.1 + i * 0.6, 4.3, 2.75, "#b74b3c" if i % 2 == 0 else "#e9dfc8"))
    house("bakery", -20, 14, -90, w=8, d=8, h=4.0, wall="#d6bf92", roof="#7d4734", sign="BAKERY", extra=aw)
    stall = [(3.2, 1.0, 0.1, -20, 7.3, 0.92, "#8c6a46")]
    for sx in (-1.45, 1.45):
        for sy in (6.9, 7.7):
            stall.append((0.12, 0.12, 0.9, -20 + sx, sy, 0.45, "#6a5038"))
    loaves = [(0.55, 0.32, 0.22, -20 + dx, 7.3 + dy, 1.08, "#b98a52", 0.2 * dx)
              for dx, dy in [(-1.0, -0.15), (-0.4, 0.2), (0.3, -0.1), (0.9, 0.18), (0.0, 0.05)]]
    multibox("stall", stall + loaves)
    # Mrs Pell + neighbour fence
    fence("pell_fence", (15, 6.0), (15, 10.2))
    fence("yard_n", (-56, 9.5), (-25, 9.5))
    fence("yard_n2", (35, 9.5), (56, 9.5))
    fence("yard_s", (-56, -9.2), (56, -9.2))
    # carrot street
    for i, yy in enumerate((22, 32, 42, 52)):
        house(f"carrot_w{i}", 22, yy, 0, w=6, d=6.5, h=rnd.uniform(3.0, 3.6))
        house(f"carrot_e{i}", 38, yy, 180, w=6, d=6.5, h=rnd.uniform(3.0, 3.6))
    house("eli_house", 30, 62, -90, w=6, d=6, h=3.3, wall="#8b9aa6", roof="#5e4c3e")
    fence("eli_fence_l", (25.5, 58.2), (28.4, 58.2))
    fence("eli_fence_r", (31.6, 58.2), (34.5, 58.2))
    cyl("carrot_sign_post", 0.08, 3.0, (34.2, 5.4, 0), "#4a3a2c", seg=6)
    multibox("carrot_sign_board", [(2.6, 0.12, 0.6, 34.2, 5.2, 2.75, "#4f6b4a")])
    text("carrot_sign_text", "CARROT ST", (34.2, 5.12, 2.75), 0, 0.36, "#f0e8d2")
    # town hall
    th = empty("town_hall", (82, 0, 0), rz(180))
    multibox("hall_body", [(16, 11, 7.5, 0, 0, 3.75, "#c9bfa8"), (17, 12, 0.5, 0, 0, 0.25, "#8f877a"),
                           (2.4, 0.2, 3.4, 0, 5.55, 1.7, "#4f3b2c"), (18, 13, 0.5, 0, 0, 7.7, "#8f877a"),
                           (12, 3, 0.3, 0, 7.0, 0.15, "#a39b8c"), (11, 2, 0.3, 0, 6.6, 0.45, "#a39b8c"),
                           (3.4, 0.2, 2.0, -5, 5.55, 4.2, "#4d5f6e"), (3.4, 0.2, 2.0, 5, 5.55, 4.2, "#4d5f6e"),
                           (6.0, 0.25, 1.1, 0, 7.1, 7.0, "#5a4636")]
             + [(0.7, 0.7, 6.8, cx, 6.6, 3.9, "#e2dccb") for cx in (-6, -3.6, 3.6, 6)], parent=th)
    poly("hall_pediment", [(-9, 6.5, 7.95), (9, 6.5, 7.95), (0, 6.5, 11), (-9, -6.5, 7.95), (9, -6.5, 7.95),
                           (0, -6.5, 11)], [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2)], "#6a5a4c", parent=th)
    text("hall_text", "TOWN HALL", (0, 7.27, 7.0), math.pi, 0.62, "#efe6d0", parent=th)
    cyl("flagpole", 0.08, 9, (70, 9, 0), "#3e3b38", seg=6)
    multibox("flag", [(0.05, 2.2, 1.3, 70, 10.15, 8.2, "#8a4a3a")])
    # podium on plaza
    multibox("podium", [(3.2, 3.6, 0.6, 66.6, 0, 0.3, "#7a5c40"), (0.7, 1.2, 1.15, 65.7, 0, 1.17, "#5e4430"),
                        (0.9, 1.4, 0.08, 65.65, 0, 1.78, "#4a3626"), (0.12, 2.2, 0.3, 64.9, 0, 0.75, "#a0453a")])
    # gate + perimeter fence
    multibox("gate", [(0.7, 0.7, 6.5, -70, -4.8, 3.25, "#6a4e36"), (0.7, 0.7, 6.5, -70, 4.8, 3.25, "#6a4e36"),
                      (0.6, 11.4, 0.7, -70, 0, 6.2, "#5e4430"), (0.5, 10.4, 0.35, -70, 0, 5.4, "#5e4430")])
    for side, sgn in (("l", -1), ("r", 1)):
        planks = [(0.12, 0.42, 4.2, 0, 0.22 + i * 0.47, 2.2, "#7b5d40") for i in range(9)]
        planks += [(0.16, 4.4, 0.3, 0, 2.2, 1.2, "#5f4630"), (0.16, 4.4, 0.3, 0, 2.2, 3.4, "#5f4630")]
        g = multibox(f"gate_door_{side}", planks, loc=(-70, sgn * 4.4, 0), rot_z=(math.radians(-90 - 60) if sgn < 0
                                                                                   else math.radians(-90 + 240)))
        g.rotation_euler.z = math.radians(-40) if sgn < 0 else math.radians(180 + 40)
    text("gate_sign", "TOWN", (-69.6, 0, 6.2), math.radians(90), 0.5, "#e8dcc0")
    fence("perim_l", (-70, -5.2), (-70, -40))
    fence("perim_r", (-70, 5.2), (-70, 40))
    # field with crop rows (merged)
    multibox("field_soil", [(36, 36, 0.05, -92, 0, 0.03, "#6e553e")])
    crops = []
    for r in range(-11, 12):
        yy = r * 1.55
        if abs(yy) < 0.9:
            continue
        crops.append((35, 0.55, 0.12, -92, yy, 0.08, "#5c4532"))
        for i in range(44):
            xx = -74.5 - i * 0.8
            crops.append((0.28, 0.28, 0.32 + 0.1 * ((i * 7 + r) % 3), xx, yy, 0.3, "#6d7a3c"))
            if (i + r) % 4 == 0:
                crops.append((0.16, 0.16, 0.14, xx, yy - 0.2, 0.17, "#c8743a"))
    multibox("crops", crops)
    fence("field_f1", (-74, -19), (-110, -19))
    fence("field_f2", (-74, 19), (-110, 19))
    # barrels, lamps, poles, wires
    for i, (x, y) in enumerate([(-25.5, 8.6), (-26.3, 9.3), (-63, 4.6), (-62.2, 5.5), (-59.2, 4.6), (72, -7),
                                (72.8, -7.7), (35.5, 7.5), (-4, 8.6), (16, -8.5), (5.6, -8.6)]):
        barrel(f"barrel{i}", x, y)
    for i, x in enumerate((-45, -30, -2, 40, 55, 62)):
        lamp(f"lamp{i}", x, 6.6)
    for i, x in enumerate((-60, -45, -30, -15, 0, 15, 30, 45, 60)):
        pole(f"pole{i}", x, -6.2)
    xs = (-60, -45, -30, -15, 0, 15, 30, 45, 60)
    for a, b in zip(xs, xs[1:]):
        for dy in (-0.9, 0.9):
            wire(f"wire_{a}_{dy}", (a, -6.2 + dy, 7.45), (b, -6.2 + dy, 7.45))
    trees()


def interior_room(name, cx, cy, floor_col, wall_col, door=False):
    """Room 10x10, planes facing inward with backface culling so cameras can sit outside."""
    H = 3.4
    x0, x1, y0, y1 = cx - 5, cx + 5, cy - 5, cy + 5
    multibox(name + "_floor", [(10, 10, 0.1, cx, cy, 0.05, floor_col)])
    wm = mat(wall_col, cull=True)
    poly(name + "_wall_back", [(x0, y1, 0), (x0, y1, H), (x1, y1, H), (x1, y1, 0)], [(0, 1, 2, 3)], wm)
    poly(name + "_wall_l", [(x0, y0, 0), (x0, y0, H), (x0, y1, H), (x0, y1, 0)], [(3, 2, 1, 0)], wm)
    poly(name + "_wall_r", [(x1, y0, 0), (x1, y0, H), (x1, y1, H), (x1, y1, 0)], [(0, 1, 2, 3)], wm)
    if door:
        dl, dr, dh = cx - 0.8, cx + 0.8, 2.4
        poly(name + "_wall_f", [(x0, y0, 0), (dl, y0, 0), (dl, y0, H), (x0, y0, H),
                                (dr, y0, 0), (x1, y0, 0), (x1, y0, H), (dr, y0, H),
                                (dl, y0, dh), (dr, y0, dh)],
             [(3, 2, 1, 0), (7, 6, 5, 4), (2, 7, 9, 8)], wm)
    else:
        poly(name + "_wall_f", [(x0, y0, 0), (x0, y0, H), (x1, y0, H), (x1, y0, 0)], [(3, 2, 1, 0)], wm)
    # skirting
    multibox(name + "_skirt", [(10, 0.08, 0.25, cx, y1 - 0.04, 0.12, "#5a4632"),
                               (0.08, 10, 0.25, x0 + 0.04, cy, 0.12, "#5a4632"),
                               (0.08, 10, 0.25, x1 - 0.04, cy, 0.12, "#5a4632")])


def interiors():
    cx, cy = INT_KITCHEN
    interior_room("kitchen", cx, cy, "#8a6a4a", "#c9b48e", door=True)
    k = [(2.6, 1.5, 0.12, cx, cy + 2, 0.9, "#7a5534")]
    for sx in (-1.15, 1.15):
        for sy in (-0.6, 0.6):
            k.append((0.12, 0.12, 0.86, cx + sx, cy + 2 + sy, 0.43, "#5e4028"))
    # dad's chair
    k += [(0.8, 0.8, 0.1, cx, cy + 3.3, 0.5, "#6a4a30"), (0.8, 0.1, 1.0, cx, cy + 3.72, 1.0, "#6a4a30")]
    k += [(0.08, 0.08, 0.5, cx + dx, cy + 3.3 + dy, 0.25, "#5e4028") for dx in (-0.35, 0.35) for dy in (-0.35, 0.35)]
    # empty chair (eli's)
    k += [(0.8, 0.8, 0.1, cx - 2.1, cy + 2, 0.5, "#6a4a30"), (0.1, 0.8, 1.0, cx - 2.5, cy + 2, 1.0, "#6a4a30")]
    # counter, cupboard, fridge, window, shelf
    k += [(5.0, 0.9, 1.0, cx + 2.2, cy + 4.5, 0.5, "#9a7a58"), (5.0, 1.0, 0.08, cx + 2.2, cy + 4.5, 1.04, "#d7cdb8"),
          (3.0, 0.6, 1.0, cx + 2.6, cy + 4.7, 2.4, "#8a6a4a"), (1.1, 0.9, 2.1, cx - 4.2, cy + 4.4, 1.05, "#d9d3c4"),
          (1.6, 0.06, 1.1, cx - 1.6, cy + 4.95, 1.9, "#8fb0c4"), (1.8, 0.08, 0.1, cx - 1.6, cy + 4.93, 1.32, "#e8e0cc"),
          (3.0, 2.0, 0.02, cx, cy - 0.2, 0.11, "#7d4b40"),  # rug
          (0.35, 0.35, 0.3, cx + 0.6, cy + 1.9, 1.11, "#c8b07a"),  # bread box on table
          (0.3, 0.3, 0.12, cx - 0.5, cy + 2.2, 1.02, "#e2d8c0")]  # plate
    multibox("kitchen_props", k)
    for i, dx in enumerate((1.8, 2.3, 2.8, 3.3)):
        cyl(f"jar{i}", 0.13, 0.35, (cx + dx, cy + 4.6, 1.08), rnd.choice(["#b9874a", "#8a9a6a", "#c86a4a"]), seg=8)
    # the bag under the table
    cyl("bag", 0.34, 0.5, (cx + 0.45, cy + 1.9, 0.1), "#8f7350", seg=7, r2=0.22)
    cyl("bag_neck", 0.12, 0.16, (cx + 0.45, cy + 1.9, 0.6), "#7e6444", seg=6, r2=0.18)
    multibox("bag_tie", [(0.3, 0.3, 0.05, cx + 0.45, cy + 1.9, 0.58, "#4a3a28")])
    # door (hinged)
    hinge = empty("door_hinge", (cx - 0.8, cy - 5, 0))
    multibox("door_panel", [(1.6, 0.1, 2.38, 0.8, 0, 1.19, "#6a4a30"), (0.12, 0.14, 0.12, 1.4, 0.08, 1.1, "#c8a85a"),
                            (1.2, 0.12, 0.8, 0.8, 0, 1.7, "#5a3e28")], parent=hinge)
    multibox("door_frame", [(0.15, 0.2, 2.5, cx - 0.88, cy - 5, 1.25, "#4f3a28"),
                            (0.15, 0.2, 2.5, cx + 0.88, cy - 5, 1.25, "#4f3a28"),
                            (1.9, 0.2, 0.15, cx, cy - 5, 2.45, "#4f3a28")])
    # houses outside the kitchen door (so the open door shows a street)
    house("k_out1", cx - 9, cy - 18, 90, w=7, d=7, h=3.6)
    house("k_out2", cx + 6, cy - 19, 90, w=7, d=7, h=3.8)
    multibox("k_street", [(60, 8, 0.04, cx, cy - 10, 0.02, "#a68a66")])
    pole("k_pole", cx + 4, cy - 7)
    lamp("k_lamp", cx - 4, cy - 7)
    k_l = bpy.data.lights.new("kitchen_lamp", "POINT")
    k_l.energy = 110
    k_l.color = (1.0, 0.82, 0.6)
    k_l.shadow_soft_size = 0.05
    lo = bpy.data.objects.new("kitchen_lamp", k_l)
    lo.location = (cx, cy + 2, 3.0)
    link(lo)
    multibox("kitchen_lampshade", [(0.6, 0.6, 0.25, cx, cy + 2, 3.2, "#3e3b38")])

    # town hall office with the safe
    hx, hy = INT_HALL
    interior_room("hall", hx, hy, "#7c7a74", "#b8ad96")
    s = [(1.5, 1.1, 1.7, hx, hy + 4.4, 0.85, "#5d6660"), (1.25, 0.1, 1.45, hx, hy + 3.86, 0.85, "#221e1b"),
         (1.2, 0.12, 0.06, hx, hy + 3.79, 0.55, "#8a8078"), (1.2, 0.12, 0.06, hx, hy + 3.79, 1.1, "#8a8078"),
         (1.6, 0.05, 0.1, hx, hy + 3.85, 1.72, "#c9b16a")]
    multibox("safe", s)
    sh = empty("safe_door_hinge", (hx - 0.75, hy + 3.85, 0))
    multibox("safe_door", [(1.45, 0.14, 1.6, 0.72, -0.07, 0.85, "#66706a"),
                           (0.36, 0.06, 0.36, 0.72, -0.17, 0.95, "#c9b16a"), (1.45, 0.16, 0.1, 0.72, -0.07, 0.1, "#2f3432"),
                           (0.1, 0.05, 0.5, 1.2, -0.17, 0.85, "#8f8f8f")], parent=sh)
    sh.rotation_euler.z = math.radians(-115)
    multibox("hall_props", [(3.0, 1.4, 0.1, hx - 2.8, hy + 1.5, 0.9, "#6a4a30"),
                            (0.1, 1.4, 0.9, hx - 4.25, hy + 1.5, 0.45, "#5a3e28"),
                            (0.1, 1.4, 0.9, hx - 1.35, hy + 1.5, 0.45, "#5a3e28"),
                            (1.4, 0.06, 1.0, hx + 3, hy + 4.95, 2.1, "#6a5a42"),
                            (1.1, 0.04, 0.75, hx + 3, hy + 4.92, 2.1, "#8a9a8a"),
                            (0.6, 0.4, 0.04, hx - 2.4, hy + 1.4, 0.97, "#efe6d0"),
                            (2.2, 1.6, 0.02, hx, hy + 1.0, 0.11, "#6e3c36")])
    cyl("hall_flag", 0.05, 2.6, (hx - 4.3, hy + 4.4, 0), "#3e3b38", seg=6)
    multibox("hall_flag_cloth", [(0.04, 0.9, 0.6, hx - 4.3, hy + 3.9, 2.2, "#8a4a3a")])
    hl = bpy.data.lights.new("hall_lamp", "POINT")
    hl.energy = 220
    hl.color = (1.0, 0.86, 0.7)
    ho = bpy.data.objects.new("hall_lamp", hl)
    ho.location = (hx, hy + 1, 3.0)
    link(ho)


# ---------------------------------------------------------------- characters
def face_plane(name, parent, img_path):
    s = 0.29
    verts = [(s, 0, -s), (-s, 0, -s), (-s, 0, s), (s, 0, s)]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = "FACE"
    tex.interpolation = "Closest"
    tex.image = bpy.data.images.load(img_path, check_existing=True)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    ob = poly(name, verts, [(0, 1, 2, 3)], m, parent=parent, uvs=uvs)
    ob.location = (0, 0.312, 0.33)
    return ob


def character(name, spec):
    sk = {"eli": "#e2be96", "baker": "#d6ac84", "mayor": "#e8c8a8", "dad": "#c49670", "pell": "#eccdb2",
          "t1": "#aa7a58", "t2": "#deb890", "t3": "#96684a", "t4": "#e6c4a0", "t5": "#cca078", "t6": "#b88864"}[name]
    shirt, pants, hair = spec["shirt"], spec["pants"], spec["hair"]
    kind = spec["kind"]
    root = empty(name + "_root", (0, 0, -200))
    root.scale = (spec["scale"],) * 3
    torso = [(0.92, 0.46, 0.9, 0, 0, 1.35, shirt)]
    if kind == "mayor":
        torso += [(0.3, 0.05, 0.62, 0, 0.235, 1.48, "#e8e4da"), (0.1, 0.06, 0.5, 0, 0.245, 1.45, "#7a2e2e"),
                  (0.96, 0.5, 0.12, 0, 0, 0.95, "#2f3034")]
    if kind == "baker":
        torso += [(0.78, 0.05, 1.2, 0, 0.235, 1.2, "#f6f2ea")]
    if kind == "mail":
        torso += [(0.12, 0.5, 0.95, 0.35, 0.02, 1.4, "#5a4430", 0.6), (0.45, 0.25, 0.4, 0.5, 0.0, 1.0, "#6a4e36")]
    if kind == "pell":
        torso += [(1.0, 0.6, 0.65, 0, 0, 0.62, pants)]
    if kind == "kid":
        torso += [(0.6, 0.05, 0.08, 0, 0.235, 1.6, "#e8e0cc")]
    multibox(name + "_torso", torso, parent=root)
    for side, sx in (("L", -1), ("R", 1)):
        leg = multibox(name + "_leg" + side, [(0.4, 0.42, 0.78, 0, 0, -0.39, pants),
                                              (0.42, 0.5, 0.14, 0, 0.04, -0.83, "#2e2722")], parent=root)
        leg.location = (sx * 0.23, 0, 0.9)
        arm = multibox(name + "_arm" + side, [(0.3, 0.32, 0.56, 0, 0, -0.26, shirt),
                                              (0.27, 0.29, 0.3, 0, 0, -0.69, sk)], parent=root)
        arm.location = (sx * 0.62, 0, 1.76)
    head = multibox(name + "_head", [(0.62, 0.62, 0.62, 0, 0, 0.33, sk)], parent=root)
    head.location = (0, 0, 1.8)
    face_plane(name + "_face", head, os.path.join(FACES, f"{name}_neutral.png"))
    hb = [(0.68, 0.68, 0.16, 0, -0.02, 0.69, hair), (0.68, 0.16, 0.5, 0, -0.27, 0.45, hair),
          (0.1, 0.5, 0.36, -0.33, -0.05, 0.5, hair), (0.1, 0.5, 0.36, 0.33, -0.05, 0.5, hair)]
    if kind == "kid":
        hb += [(0.2, 0.2, 0.14, 0.12, 0.12, 0.82, hair, 0.5), (0.7, 0.12, 0.1, 0, 0.3, 0.63, hair)]
    if kind == "mayor":
        hb = [(0.9, 0.9, 0.06, 0, 0, 0.72, "#55585c"), (0.6, 0.6, 0.62, 0, 0, 1.04, "#6b6e72"),
              (0.62, 0.62, 0.1, 0, 0, 0.8, "#2f3034"), (0.1, 0.5, 0.25, -0.33, -0.05, 0.55, hair),
              (0.1, 0.5, 0.25, 0.33, -0.05, 0.55, hair)]
    if kind == "pell":
        hb += [(0.32, 0.32, 0.3, 0, -0.18, 0.85, hair)]
    if kind == "mail":
        hb = [(0.7, 0.7, 0.18, 0, 0, 0.72, "#3f5470"), (0.6, 0.3, 0.05, 0, 0.42, 0.66, "#2f3f52")]
    if kind == "dad":
        hb += [(0.26, 0.04, 0.05, 0, 0.318, 0.27, "#3a2a1e")]
    multibox(name + "_hair", hb, parent=head)
    if kind == "baker":
        cyl(name + "_hat", 0.3, 0.36, (0, 0, 0.66), "#f6f2ea", seg=10, parent=head)
        cyl(name + "_hat_top", 0.42, 0.3, (0, 0, 0.98), "#ffffff", seg=10, r2=0.36, parent=head)
    return root


# ---------------------------------------------------------------- world, lights, camera, render
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
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 1
    sc.eevee.use_shadows = True
    sc.eevee.shadow_ray_count = 1
    sc.eevee.shadow_step_count = 1
    sc.render.filter_size = 1.2
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.resolution_x = 540
    sc.render.resolution_y = 960
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.fps = 30


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    world_and_render()
    town()
    interiors()
    for n, spec in CAST.items():
        character(n, spec)
    out = os.path.join(HERE, "build", "town.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("saved", out, "objects:", len(bpy.data.objects))


if __name__ == "__main__":
    main()
