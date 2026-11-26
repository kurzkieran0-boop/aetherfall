"""Shared town kit: standard town layout, landmarks, lake set, interiors (bpy). Used by every video's scene.py."""
import bpy, math, os, random
from mathutils import Vector
import blocks as K
from blocks import mat, multibox, poly, cyl, empty, text, rz, house, fence, barrel, lamp, pole, wire, link, srgb

rnd = random.Random(11)
CREAM, SEAL = "#efe5c8", "#a3302a"
WALLS = ["#c8b08a", "#b9a07c", "#a88f72", "#cdbb98", "#9fa38a", "#b59a86", "#8fa0a8", "#c2a88a"]


# ------------------------------------------------------------------ ground + roads
def ground(roads=(), plazas=(), keep_clear=()):
    """roads/plazas: (cx, cy, w, h). keep_clear: (x0, x1, y0, y1) boxes without grass tufts."""
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "ground"
    g.data.materials.append(mat("#8c8a5c"))
    multibox("roads", [(w, h, 0.04, cx, cy, 0.02, "#a68a66") for (cx, cy, w, h) in roads])
    if plazas:
        multibox("plazas", [(w, h, 0.04, cx, cy, 0.03, "#b8a282") for (cx, cy, w, h) in plazas])
    ruts = [(w - 2, 0.25, 0.01, cx, cy + sy, 0.045, "#8f7656") for (cx, cy, w, h) in roads if w > h for sy in (-1.4, 1.4)]
    if ruts:
        multibox("ruts", ruts)
    tufts = []
    for i in range(700):
        x, y = rnd.uniform(-120, 110), rnd.uniform(-90, 90)
        bad = any(abs(x - cx) < w / 2 + 1 and abs(y - cy) < h / 2 + 1 for (cx, cy, w, h) in list(roads) + list(plazas))
        bad = bad or any(a <= x <= b and c <= y <= d for (a, b, c, d) in keep_clear)
        if bad:
            continue
        s = rnd.uniform(0.2, 0.5)
        tufts.append((s, s, s * 0.6, x, y, s * 0.3, rnd.choice(["#76784a", "#6b7044", "#858456"])))
    multibox("tufts", tufts)


def houses(north=(), south=(), yn=14, ys=-14):
    k = 0
    for x in north:
        house(f"house_n{k}", x + rnd.uniform(-0.5, 0.5), yn, -90, w=rnd.uniform(6.2, 7.4), d=7, h=rnd.uniform(3.2, 4.2)); k += 1
    for x in south:
        house(f"house_s{k}", x + rnd.uniform(-0.5, 0.5), ys, 90, w=rnd.uniform(6.2, 7.4), d=7, h=rnd.uniform(3.2, 4.2)); k += 1
    return k


def bakery(x=-20, y=14, face=-90):
    aw = [(0.6, 1.6, 0.12, -2.1 + i * 0.6, 4.3, 2.75, "#b74b3c" if i % 2 == 0 else "#e9dfc8") for i in range(8)]
    # shop window full of loaves
    win = [(3.0, 0.1, 1.2, 0, 4.06, 1.5, "#3d4a55")]
    win += [(0.5, 0.3, 0.22, -1.1 + i * 0.55, 4.2, 1.05 + 0.3 * (i % 2), "#c08a4a", 0.2 * i) for i in range(5)]
    house("bakery", x, y, face, w=8, d=8, h=4.0, wall="#d6bf92", roof="#7d4734", sign="BAKERY", extra=aw + win)
    sx, sy = x, y - 6.7 if face == -90 else y + 6.7
    stall = [(3.2, 1.0, 0.1, sx, sy, 0.92, "#8c6a46")]
    stall += [(0.12, 0.12, 0.9, sx + dx, sy + dy, 0.45, "#6a5038") for dx in (-1.45, 1.45) for dy in (-0.4, 0.4)]
    stall += [(0.55, 0.32, 0.22, sx + dx, sy + dy, 1.08, "#b98a52", 0.2 * dx)
              for dx, dy in [(-1.0, -0.15), (-0.4, 0.2), (0.3, -0.1), (0.9, 0.18), (0.0, 0.05)]]
    multibox("bakery_stall", stall)


def post_office(x=40, y=14):
    trim = [(9.2, 0.15, 0.35, 0, 4.1, 0.9, "#4f6a8a"), (9.2, 0.15, 0.2, 0, 4.1, 3.3, "#a3302a")]
    house("post_office", x, y, -90, w=9, d=8, h=4.3, wall="#cdbb98", roof="#5a5f62", sign="POST OFFICE", extra=trim)
    multibox("po_box", [(0.7, 0.6, 1.1, x + 4, y - 5, 0.75, "#4f6a8a"), (0.8, 0.7, 0.2, x + 4, y - 5, 1.35, "#3f5470")])


def school(x=-42, y=14, face=-90):
    root = empty("school", (x, y, 0), rz(face))
    boxes = [(13, 9, 5.2, 0, 0, 2.6, "#b59a86"), (13.4, 9.4, 0.3, 0, 0, 0.15, "#6d6252"),
             (1.8, 0.2, 2.4, 0, 4.55, 1.2, "#5b4030"), (14, 0.25, 0.4, 0, 4.6, 5.0, "#e8e0cc")]
    for i, wx in enumerate((-4.8, -2.6, 2.6, 4.8)):
        for wz in (1.6, 3.7):
            boxes += [(1.4, 0.14, 1.1, wx, 4.55, wz, "#4d5f6e"), (1.6, 0.1, 0.12, wx, 4.58, wz - 0.6, "#e8e0cc")]
    boxes += [(2.2, 2.2, 1.8, 0, 0, 6.1, "#b59a86"), (0.9, 0.12, 0.9, 0, 1.15, 6.2, "#e8e0cc")]  # bell tower
    multibox("school_body", boxes, parent=root)
    poly("school_roof", [(-7, -5, 5.2), (7, -5, 5.2), (7, 5, 5.2), (-7, 5, 5.2), (-7, 0, 7.2), (7, 0, 7.2)],
         [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)], "#5a5f62", parent=root)
    poly("school_tower_roof", [(-1.3, -1.3, 7.0), (1.3, -1.3, 7.0), (1.3, 1.3, 7.0), (-1.3, 1.3, 7.0), (0, 0, 8.6)],
         [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], "#7a4a36", parent=root)
    multibox("school_signboard", [(5.0, 0.15, 0.8, 0, 4.72, 4.3, "#4f3a2a")], parent=root)
    text("school_sign", "SCHOOL", (0, 4.82, 4.3), math.pi, 0.55, "#efe6d0", parent=root)
    # playground: swing frame + seesaw in front
    fx, fy = (x, y - 9) if face == -90 else (x, y + 9)
    multibox("playground", [(0.15, 0.15, 2.4, fx - 5.5, fy, 1.2, "#7a4a36"), (0.15, 0.15, 2.4, fx - 3.0, fy, 1.2, "#7a4a36"),
                            (2.7, 0.15, 0.15, fx - 4.25, fy, 2.4, "#7a4a36"), (0.6, 0.3, 0.06, fx - 4.25, fy, 0.6, "#a3593d"),
                            (3.0, 0.3, 0.1, fx + 4.5, fy, 0.55, "#4f6a8a"), (0.3, 0.3, 0.5, fx + 4.5, fy, 0.25, "#5e4430")])


def town_hall(x=82, y=0, podium=(66.6, 0)):
    th = empty("town_hall", (x, y, 0), rz(180))
    multibox("hall_body", [(16, 11, 7.5, 0, 0, 3.75, "#c9bfa8"), (17, 12, 0.5, 0, 0, 0.25, "#8f877a"),
                           (2.4, 0.2, 3.4, 0, 5.55, 1.7, "#4f3b2c"), (18, 13, 0.5, 0, 0, 7.7, "#8f877a"),
                           (12, 3, 0.3, 0, 7.0, 0.15, "#a39b8c"), (11, 2, 0.3, 0, 6.6, 0.45, "#a39b8c"),
                           (3.4, 0.2, 2.0, -5, 5.55, 4.2, "#4d5f6e"), (3.4, 0.2, 2.0, 5, 5.55, 4.2, "#4d5f6e"),
                           (6.0, 0.25, 1.1, 0, 7.1, 7.0, "#5a4636")]
             + [(0.7, 0.7, 6.8, cx, 6.6, 3.9, "#e2dccb") for cx in (-6, -3.6, 3.6, 6)], parent=th)
    poly("hall_pediment", [(-9, 6.5, 7.95), (9, 6.5, 7.95), (0, 6.5, 11), (-9, -6.5, 7.95), (9, -6.5, 7.95),
                           (0, -6.5, 11)], [(0, 1, 2), (3, 5, 4), (0, 2, 5, 3), (1, 4, 5, 2)], "#6a5a4c", parent=th)
    text("hall_text", "TOWN HALL", (0, 7.27, 7.0), math.pi, 0.62, "#efe6d0", parent=th)
    if podium:
        px, py = podium
        multibox("podium", [(3.2, 3.6, 0.6, px, py, 0.3, "#7a5c40"), (0.7, 1.2, 1.15, px - 0.9, py, 1.17, "#5e4430"),
                            (0.9, 1.4, 0.08, px - 0.95, py, 1.78, "#4a3626"), (0.12, 2.2, 0.3, px - 1.7, py, 0.75, "#a0453a")])
    cyl("flagpole", 0.08, 9, (x - 12, y + 9, 0), "#3e3b38", seg=6)
    multibox("flag", [(0.05, 2.2, 1.3, x - 12, y + 10.15, 8.2, "#8a4a3a")])


def utilities(xs, y=-6.2, lamps_x=(), lamp_y=6.6, barrels_at=()):
    for i, x in enumerate(xs):
        pole(f"pole{i}", x, y)
    for a, b in zip(xs, xs[1:]):
        for dy in (-0.9, 0.9):
            wire(f"wire_{a}_{dy}", (a, y + dy, 7.45), (b, y + dy, 7.45))
    for i, x in enumerate(lamps_x):
        lamp(f"lamp{i}", x, lamp_y)
    for i, (x, yy) in enumerate(barrels_at):
        barrel(f"barrel{i}", x, yy)


def trees(points, style="A"):
    for i, (x, y) in enumerate(points):
        h = rnd.uniform(2.2, 3.4)
        cyl(f"tree{i}", 0.3, h, (x, y, 0), "#5c4634", seg=7)
        if style == "B":   # rounder, layered canopy
            multibox(f"tree{i}_top", [(3.2, 3.2, 2.0, 0, 0, h + 0.9, "#5f6b3e"), (2.6, 2.6, 1.6, 0.2, -0.1, h + 2.3, "#6a7244"),
                                       (1.8, 1.8, 1.2, -0.1, 0.2, h + 3.3, "#6f7a48"), (2.2, 3.4, 1.0, 0, 0, h + 1.4, "#56603a")],
                     loc=(x, y, 0), rot_z=rnd.uniform(0, 1.5))
        else:
            multibox(f"tree{i}_top", [(2.8, 2.8, 2.4, 0, 0, h + 1.0, rnd.choice(["#5f6b3e", "#6a7244", "#56603a"])),
                                       (2.0, 2.0, 1.4, 0, 0, h + 2.6, "#6f7a48")], loc=(x, y, 0), rot_z=rnd.uniform(0, 1))


def field(cx=-92, cy=-4, rows=17, cols=44, fence_box=None):
    multibox("field_soil", [(cols * 0.8 + 1, rows * 1.55 + 2, 0.05, cx, cy, 0.03, "#6e553e")])
    crops = []
    for r in range(rows):
        yy = cy + (r - rows / 2) * 1.55
        crops.append((cols * 0.8, 0.55, 0.12, cx, yy, 0.08, "#5c4532"))
        for i in range(cols):
            xx = cx + cols * 0.4 - 0.4 - i * 0.8
            crops.append((0.28, 0.28, 0.32 + 0.1 * ((i * 7 + r) % 3), xx, yy, 0.3, "#6d7a3c"))
            if (i + r) % 4 == 0:
                crops.append((0.16, 0.16, 0.14, xx, yy - 0.2, 0.17, "#c8743a"))
    multibox("crops", crops)


def sign(name, x, y, face_deg, label, w=3.2, h=0.9, post=2.4, board="#4f3a2a", ink="#f0e8d2", size=0.34):
    cyl(name + "_post", 0.08, post + h / 2, (x, y, 0), "#4a3a2c", seg=6)
    f = math.radians(face_deg)
    fx, fy = math.cos(f), math.sin(f)
    ob = multibox(name + "_board", [(w, 0.12, h, 0, 0, 0, board)], loc=(x + fx * 0.1, y + fy * 0.1, post), rot_z=f - math.pi / 2)
    lines = label.split("\n")
    for i, ln in enumerate(lines):
        zz = post + (len(lines) - 1) * size * 0.65 - i * size * 1.3
        text(f"{name}_txt{i}", ln, (x + fx * 0.17, y + fy * 0.17, zz), f + math.pi / 2, size, ink)
    return ob


# ------------------------------------------------------------------ landmarks
def windmill(cx, cy):
    hb, ht, H = 2.6, 1.5, 9.0
    vs = [(cx - hb, cy - hb, 0), (cx + hb, cy - hb, 0), (cx + hb, cy + hb, 0), (cx - hb, cy + hb, 0),
          (cx - ht, cy - ht, H), (cx + ht, cy - ht, H), (cx + ht, cy + ht, H), (cx - ht, cy + ht, H)]
    poly("mill_tower", vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], "#b9a07c")
    poly("mill_cap", [(cx - 1.9, cy - 1.9, H), (cx + 1.9, cy - 1.9, H), (cx + 1.9, cy + 1.9, H), (cx - 1.9, cy + 1.9, H),
                      (cx, cy - 1.9, H + 2.0), (cx, cy + 1.9, H + 2.0)], [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], "#6a5040")
    multibox("mill_door", [(1.3, 0.2, 2.2, cx, cy - hb - 0.02, 1.1, "#5b4030"), (3.2, 0.2, 0.7, cx, cy - hb - 0.05, 2.8, "#4f3a2a")])
    text("mill_sign", "MILL", (cx, cy - hb - 0.17, 2.8), 0, 0.45, "#efe6d0")
    hub = empty("mill_hub", (cx, cy - ht - 0.9, H - 1.2))
    bl = [(0.5, 0.35, 0.5, 0, 0, 0, "#4f3a2a")]
    for k in range(4):
        a = k * math.pi / 2
        dx, dz = math.cos(a), math.sin(a)
        for r in range(6):
            bl.append((0.6 if r else 0.2, 0.08, 0.6 if r else 0.2, dx * (0.8 + r * 0.6), -0.1, dz * (0.8 + r * 0.6), "#d8ccb0" if r else "#4f3a2a"))
        bl.append((0.14 if dz else 4.2, 0.12, 4.2 if dz else 0.14, dx * 2.2, -0.05, dz * 2.2, "#4f3a2a"))
    multibox("mill_blades", bl, parent=hub)


def lake(cx=-20, cy=-60, rx=26, ry=16, dock=True, waterfall=True, boat=True, ducks=True):
    """Lake with a wooden dock (pointing +y toward town), rowboat with oar, waterfall at the -y far edge, ducks."""
    verts = [(cx, cy, 0.06)] + [(cx + rx * math.cos(a), cy + ry * math.sin(a), 0.06)
                                for a in [i * 2 * math.pi / 40 for i in range(40)]]
    faces = [(0, i + 1, (i + 1) % 40 + 1) for i in range(40)]
    poly("lake_water", verts, faces, "#4a7a9a")
    shore = []
    for i in range(40):
        a = i * 2 * math.pi / 40
        shore.append((2.2, 2.2, 0.12, cx + (rx + 0.6) * math.cos(a), cy + (ry + 0.6) * math.sin(a), 0.05, "#b8a282", a))
    multibox("lake_shore", shore)
    if dock:   # from the north shore out to the middle
        dy0 = cy + ry + 1.5
        d = [(2.4, 14, 0.18, cx, dy0 - 7, 0.55, "#7a5c40")]
        d += [(0.25, 0.25, 1.2, cx + sx, dy0 - k * 2.2, 0.2, "#5e4430") for sx in (-1.1, 1.1) for k in range(7)]
        d += [(2.4, 0.1, 0.05, cx, dy0 - k * 0.7, 0.65, "#6a4e36") for k in range(20)]
        multibox("dock", d)
        multibox("icecream_stand", [(2.2, 1.4, 1.1, cx + 4.5, dy0 + 1.2, 0.55, "#e8e0cc"), (2.4, 1.6, 0.12, cx + 4.5, dy0 + 1.2, 2.4, "#a3593d"),
                                    (0.1, 0.1, 1.3, cx + 3.5, dy0 + 0.6, 1.75, "#e8e0cc"), (0.1, 0.1, 1.3, cx + 5.5, dy0 + 0.6, 1.75, "#e8e0cc"),
                                    (0.3, 0.3, 0.4, cx + 4.5, dy0 + 0.5, 1.3, "#f0c8d0")])
    if boat:
        bt = empty("rowboat", (cx + 2.6, cy + ry - 6, 0.12))
        multibox("rowboat_hull", [(1.4, 3.0, 0.5, 0, 0, 0.25, "#8a5a3a"), (1.1, 2.6, 0.12, 0, 0, 0.5, "#6a4428"),
                                  (1.2, 0.2, 0.1, 0, 0.3, 0.45, "#7a5c40"), (0.9, 0.5, 0.45, 0, 1.6, 0.22, "#8a5a3a", 0)], parent=bt)
        oar = multibox("rowboat_oar", [(0.06, 2.0, 0.06, 0, 0, 0, "#c8a878"), (0.08, 0.45, 0.25, 0, -1.0, 0, "#c8a878")], parent=bt)
        oar.location = (-0.55, 0.0, 0.7)
        oar.rotation_euler = (0.35, 0, 0.5)
        rope = cyl("rowboat_rope", 0.03, 2.0, (0, 1.6, 0.4), "#c8b080", seg=5, parent=bt, rot=(math.radians(-80), 0, 0))
    if waterfall:
        wy = cy - ry - 0.5
        multibox("waterfall_lip", [(10, 1.2, 0.5, cx, wy, 0.05, "#7c7a74")] +
                 [(rnd.uniform(1, 2), 1.4, rnd.uniform(0.6, 1.4), cx + rnd.uniform(-6, 6), wy - 0.3, 0.2, "#7c7a74") for _ in range(10)])
        fall = multibox("waterfall_sheet", [(8.5, 0.4, 9.0, cx, wy - 0.9, -4.4, "#cfe6f0")])
        for m in fall.data.materials:
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Emission Color"].default_value = srgb("#cfe6f0") + [1]
            b.inputs["Emission Strength"].default_value = 0.6
        multibox("waterfall_mist", [(rnd.uniform(1.5, 3), 1.6, rnd.uniform(0.8, 1.6), cx + rnd.uniform(-5, 5), wy - 2.2,
                                     rnd.uniform(-0.5, 0.8), "#eef4f6") for _ in range(12)])
        multibox("waterfall_cliff", [(40, 8, 12, cx, wy - 5, -6.1, "#7c7a74")])
        sign("falls_sign", cx - 8, cy + ry - 2, 90, "DANGER\nWATERFALL", w=3.0, h=1.2, size=0.3, board="#a3302a")
    if ducks:
        for i in range(5):
            dx, dy = cx + rnd.uniform(-10, 10), cy + rnd.uniform(-6, 8)
            dk = empty(f"duck{i}", (dx, dy, 0.08), rnd.uniform(0, 6))
            multibox(f"duck{i}_body", [(0.45, 0.3, 0.25, 0, 0, 0.12, "#e8e0cc"), (0.2, 0.2, 0.22, 0.18, 0, 0.32, "#5f7a4a"),
                                        (0.12, 0.08, 0.05, 0.32, 0, 0.3, "#d89a3a")], parent=dk)


def barn(cx, cy):
    multibox("barn_body", [(8, 10, 5, cx, cy, 2.5, "#8a4436"), (2.8, 0.2, 3.4, cx, cy - 5.05, 1.7, "#5e2e26"),
                           (0.15, 0.25, 3.4, cx - 1.4, cy - 5.1, 1.7, "#e8e0cc"), (0.15, 0.25, 3.4, cx + 1.4, cy - 5.1, 1.7, "#e8e0cc"),
                           (2.8, 0.25, 0.15, cx, cy - 5.1, 3.4, "#e8e0cc")])
    poly("barn_roof", [(cx - 4.4, cy - 5.3, 5), (cx + 4.4, cy - 5.3, 5), (cx + 4.4, cy + 5.3, 5), (cx - 4.4, cy + 5.3, 5),
                       (cx, cy - 5.3, 8), (cx, cy + 5.3, 8)], [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], "#4a4440")


def emissive(ob, strength=4.0):
    for m in ob.data.materials:
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Color"].default_value = b.inputs["Base Color"].default_value
        b.inputs["Emission Strength"].default_value = strength


# ------------------------------------------------------------------ interiors (planes with backface culling)
def room(name, cx, cy, W=10, D=10, H=3.2, floor="#8a6a4a", wall="#c9b48e", ceiling=False, front_door=None):
    """Planes facing inward with backface culling: cameras outside the room see straight in.
    front_door: (x0, x1, height) opening in the -y wall."""
    x0, x1, y0, y1 = cx - W / 2, cx + W / 2, cy - D / 2, cy + D / 2
    wm = mat(wall, cull=True)
    multibox(name + "_floor", [(W, D, 0.1, cx, cy, 0.05, floor)])
    poly(name + "_wall_back", [(x0, y1, 0), (x0, y1, H), (x1, y1, H), (x1, y1, 0)], [(0, 1, 2, 3)], wm)
    poly(name + "_wall_l", [(x0, y0, 0), (x0, y0, H), (x0, y1, H), (x0, y1, 0)], [(3, 2, 1, 0)], wm)
    poly(name + "_wall_r", [(x1, y0, 0), (x1, y0, H), (x1, y1, H), (x1, y1, 0)], [(0, 1, 2, 3)], wm)
    if front_door:
        dl, dr, dh = front_door
        poly(name + "_wall_f", [(x0, y0, 0), (dl, y0, 0), (dl, y0, H), (x0, y0, H), (dr, y0, 0), (x1, y0, 0), (x1, y0, H),
                                (dr, y0, H), (dl, y0, dh), (dr, y0, dh)], [(3, 2, 1, 0), (7, 6, 5, 4), (2, 7, 9, 8)], wm)
    else:
        poly(name + "_wall_f", [(x0, y0, 0), (x0, y0, H), (x1, y0, H), (x1, y0, 0)], [(3, 2, 1, 0)], wm)
    if ceiling:
        poly(name + "_ceiling", [(x0, y0, H), (x1, y0, H), (x1, y1, H), (x0, y1, H)], [(3, 2, 1, 0)], mat("#5a4632", cull=True))
    multibox(name + "_skirt", [(W, 0.08, 0.25, cx, y1 - 0.04, 0.12, "#5a4632"), (0.08, D, 0.25, x0 + 0.04, cy, 0.12, "#5a4632"),
                               (0.08, D, 0.25, x1 - 0.04, cy, 0.12, "#5a4632")])


def point_light(name, loc, energy, color=(1.0, 0.82, 0.6)):
    lt = bpy.data.lights.new(name, "POINT")
    lt.energy = energy
    lt.color = color
    lt.shadow_soft_size = 0.05
    lo = bpy.data.objects.new(name, lt)
    lo.location = loc
    link(lo)
    return lo


def kitchen(cx, cy, soup=True, name="kitchen", door=None):
    room(name, cx, cy, floor="#8a6a4a", wall="#c9b48e", front_door=door)
    t = [(2.8, 1.6, 0.12, cx, cy + 2, 0.9, "#7a5534")]
    t += [(0.12, 0.12, 0.86, cx + sx, cy + 2 + sy, 0.43, "#5e4028") for sx in (-1.25, 1.25) for sy in (-0.65, 0.65)]
    t += [(0.75, 0.75, 0.1, cx - 1.8, cy + 2, 0.5, "#6a4a30"), (0.75, 0.75, 0.1, cx + 1.8, cy + 2, 0.5, "#6a4a30"),
          (0.75, 0.75, 0.1, cx, cy + 3.4, 0.5, "#6a4a30"), (0.1, 0.75, 1.0, cx - 2.2, cy + 2, 1.0, "#6a4a30"),
          (0.1, 0.75, 1.0, cx + 2.2, cy + 2, 1.0, "#6a4a30"), (0.75, 0.1, 1.0, cx, cy + 3.8, 1.0, "#6a4a30")]
    t += [(5.0, 0.9, 1.0, cx + 2.2, cy + 4.5, 0.5, "#9a7a58"), (5.0, 1.0, 0.08, cx + 2.2, cy + 4.5, 1.04, "#d7cdb8"),
          (1.6, 0.06, 1.1, cx - 2.6, cy + 4.95, 1.9, "#8fb0c4"), (1.1, 0.9, 2.1, cx - 4.2, cy + 4.4, 1.05, "#d9d3c4"),
          (3.0, 2.0, 0.02, cx, cy + 0.6, 0.11, "#7d4b40")]
    multibox(name + "_props", t)
    if soup:
        for i, (dx, dy) in enumerate(((-0.8, 0), (0.8, 0), (0, 0.5))):
            cyl(f"{name}_bowl{i}", 0.2, 0.12, (cx + dx, cy + 2 + dy, 0.96), "#e2d8c0", seg=10, r2=0.24)
            cyl(f"{name}_soup{i}", 0.19, 0.02, (cx + dx, cy + 2 + dy, 1.06), "#b0763a", seg=10)
        cyl(f"{name}_pot", 0.3, 0.35, (cx, cy + 1.6, 0.96), "#4a4a4c", seg=10)
    point_light(name + "_lamp", (cx, cy + 2, 2.9), 45, (1.0, 0.85, 0.62))
    multibox(name + "_lampshade", [(0.6, 0.6, 0.25, cx, cy + 2, 3.05, "#3e3b38")])


def bedroom(cx, cy, name="bedroom", wall="#a8b4c0"):
    room(name, cx, cy, W=8, D=8, floor="#8a6a4a", wall=wall)
    b = [(1.8, 3.0, 0.5, cx + 2.4, cy + 2, 0.35, "#6a4a30"), (1.7, 2.9, 0.25, cx + 2.4, cy + 2, 0.72, "#e8e0cc"),
         (1.7, 2.0, 0.12, cx + 2.4, cy + 1.6, 0.86, "#7a8fb0"), (1.2, 0.5, 0.18, cx + 2.4, cy + 3.15, 0.9, "#f0ece4"),
         (1.8, 0.15, 1.2, cx + 2.4, cy + 3.55, 0.9, "#6a4a30"),
         (1.4, 0.7, 0.8, cx - 2.6, cy + 3.3, 0.4, "#8a6a4a"), (1.4, 0.7, 0.05, cx - 2.6, cy + 3.3, 0.82, "#9a7a58"),
         (1.4, 0.06, 1.0, cx, cy + 3.97, 1.9, "#8fb0c4"), (1.6, 0.08, 0.1, cx, cy + 3.95, 1.35, "#e8e0cc"),
         (2.4, 1.6, 0.02, cx, cy + 0.5, 0.11, "#b06a5a"), (0.8, 0.8, 0.9, cx - 3.3, cy - 2.8, 0.45, "#a3593d")]
    multibox(name + "_props", b)
    point_light(name + "_lamp", (cx - 2.6, cy + 3.0, 1.6), 30, (1.0, 0.8, 0.55))


def office_safe(cx, cy, name="hall"):
    room(name, cx, cy, floor="#7c7a74", wall="#b8ad96")
    G, BODY, TRIM = "#c9b16a", "#4f6458", "#2c3430"
    fy = cy + 3.85
    s = [(1.5, 1.1, 1.7, cx, cy + 4.4, 0.97, BODY), (1.66, 1.24, 0.14, cx, cy + 4.4, 1.89, TRIM),
         (1.7, 1.26, 0.12, cx, cy + 4.4, 0.06, TRIM), (1.25, 0.1, 1.45, cx, fy + 0.01, 0.97, "#1e1a18"),
         (1.2, 0.12, 0.05, cx, fy - 0.05, 0.62, "#8a8078"), (1.2, 0.12, 0.05, cx, fy - 0.05, 1.18, "#8a8078"),
         (0.7, 0.3, 0.08, cx + 0.1, fy - 0.12, 0.69, "#9a8a5a"), (1.42, 0.03, 0.05, cx, fy - 0.02, 1.74, G),
         (1.42, 0.03, 0.05, cx, fy - 0.02, 0.22, G), (0.05, 0.03, 1.5, cx - 0.69, fy - 0.02, 0.98, G),
         (0.05, 0.03, 1.5, cx + 0.69, fy - 0.02, 0.98, G), (0.9, 0.04, 0.12, cx, fy - 0.03, 1.89, "#d8c98e")]
    multibox("safe", s)
    text("safe_plate", "TOWN FUNDS", (cx, fy - 0.06, 1.89), 0, 0.085, "#2c2418", extrude=0.01)
    sh = empty("safe_door_hinge", (cx - 0.75, fy, 0.12))
    door = [(1.45, 0.16, 1.62, 0.72, -0.08, 0.85, "#5a7064"), (1.3, 0.03, 0.04, 0.72, -0.17, 1.55, G),
            (1.3, 0.03, 0.04, 0.72, -0.17, 0.15, G), (1.2, 0.08, 1.4, 0.72, 0.03, 0.85, "#3e4a44")]
    door += [(0.62, 0.05, 0.05, 0.72, -0.24, 0.62, "#b8b8b0", a) for a in (0, 1.047, 2.094)]
    multibox("safe_door", door, parent=sh)
    cyl("safe_dial", 0.17, 0.06, (0.72, -0.16, 1.12), G, seg=16, parent=sh, rot=(math.radians(90), 0, 0))
    sh.rotation_euler.z = math.radians(-115)
    multibox(name + "_props", [(3.0, 1.4, 0.1, cx - 2.8, cy + 1.5, 0.9, "#6a4a30"), (2.2, 1.6, 0.02, cx, cy + 1.0, 0.11, "#6e3c36")])
    point_light(name + "_lamp", (cx, cy + 1, 3.0), 220, (1.0, 0.86, 0.7))


def wall_planes(name, axis, coord, u0, u1, H, hole, normal_sign, material, uv_scale=None):
    """Vertical wall of quads with an optional rectangular hole (a, b, z0, z1)."""
    def rects(u0, u1, z0, z1, hole):
        if not hole:
            return [(u0, u1, z0, z1)]
        a, b, c, d = hole
        return [(u0, a, z0, z1), (b, u1, z0, z1), (a, b, z0, c), (a, b, d, z1)]
    verts, faces, uvs = [], [], []
    for (a, b, c, d) in rects(u0, u1, 0, H, hole):
        if b - a < 1e-3 or d - c < 1e-3:
            continue
        k = len(verts)
        q = [(a, coord, c), (b, coord, c), (b, coord, d), (a, coord, d)] if axis == "y" else \
            [(coord, a, c), (coord, b, c), (coord, b, d), (coord, a, d)]
        verts += q
        uvs += [((p[0] if axis == "y" else p[1]) / (uv_scale or 1), p[2] / (uv_scale or 1)) for p in q]
        f = (k, k + 1, k + 2, k + 3)
        if axis == "y":
            f = f if normal_sign < 0 else f[::-1]
        else:
            f = f[::-1] if normal_sign < 0 else f
        faces.append(f)
    return poly(name, verts, faces, material, uvs=uvs if uv_scale else None)


def img_mat(name, path, cull=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 1.0
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(path), check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    m.use_backface_culling = cull
    return m
