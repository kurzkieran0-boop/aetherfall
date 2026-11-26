"""Build the town, Mr. Dobbs's envelope house, Eli's kitchen and the blocky cast (bpy, headless) -> build/town.blend"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blocks as K
from blocks import mat, multibox, poly, cyl, empty, text, rz, house, fence, barrel, lamp, pole, wire, link, srgb
from scene_lib import CAST, INT_KITCHEN, DOBBS_HOUSE, ELI_HOUSE, HELD

TEX = os.path.join(HERE, "build", "tex")
FACES = os.path.join(HERE, "build", "faces")
rnd = random.Random(11)
CREAM, SEAL = "#efe5c8", "#a3302a"


def img_mat(name, path, cull=True, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.0
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    t.interpolation = "Linear"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if emit:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    m.use_backface_culling = cull
    return m


def ground():
    bpy.ops.mesh.primitive_plane_add(size=3000, location=(0, 0, 0))
    g = bpy.context.object
    g.name = "ground"
    g.data.materials.append(mat("#8c8a5c"))
    multibox("main_road", [(160, 8, 0.04, 0, 0, 0.02, "#a68a66")])
    multibox("plaza", [(26, 26, 0.04, 66, 0, 0.03, "#b8a282")])
    multibox("po_lane", [(4, 16, 0.04, 40, 18, 0.025, "#a68a66")])
    multibox("mill_lane", [(3, 18, 0.04, -36, 12, 0.025, "#a68a66")])
    multibox("ruts", [(158, 0.25, 0.01, 0, sy, 0.045, "#8f7656") for sy in (-1.4, 1.4)])
    tufts = []
    for i in range(500):
        x, y = rnd.uniform(-120, 110), rnd.uniform(-90, 90)
        if abs(y) < 5 or (52 < x < 80 and abs(y) < 14) or x < -73 or (36 < x < 46 and 8 < y < 36):
            continue
        s = rnd.uniform(0.2, 0.5)
        tufts.append((s, s, s * 0.6, x, y, s * 0.3, rnd.choice(["#76784a", "#6b7044", "#858456"])))
    multibox("tufts", tufts)


def rects_minus_hole(u0, u1, z0, z1, hole):
    if not hole:
        return [(u0, u1, z0, z1)]
    a, b, c, d = hole
    return [(u0, a, z0, z1), (b, u1, z0, z1), (a, b, z0, c), (a, b, d, z1)]


def wall_planes(name, axis, coord, u0, u1, H, hole, normal_sign, material, uv_scale=None, thickness_off=0.0):
    """Vertical wall of quads. axis 'y': wall at y=coord spanning x in [u0,u1]; axis 'x': at x=coord spanning y."""
    verts, faces, uvs = [], [], []
    for (a, b, c, d) in rects_minus_hole(u0, u1, 0, H, hole):
        if b - a < 1e-3 or d - c < 1e-3:
            continue
        k = len(verts)
        if axis == "y":
            q = [(a, coord, c), (b, coord, c), (b, coord, d), (a, coord, d)]
        else:
            q = [(coord, a, c), (coord, b, c), (coord, b, d), (coord, a, d)]
        verts += q
        uvs += [((p[0] if axis == "y" else p[1]) / (uv_scale or 1), p[2] / (uv_scale or 1)) for p in q]
        # orient so the normal points to normal_sign along the wall axis
        f = (k, k + 1, k + 2, k + 3)
        if axis == "y":
            f = f if normal_sign < 0 else f[::-1]
        else:
            f = f[::-1] if normal_sign < 0 else f
        faces.append(f)
    return poly(name, verts, faces, material, uvs=uvs if uv_scale else None)


def dobbs_house():
    cx, cy = DOBBS_HOUSE
    W, D, H = 6.0, 6.0, 3.2
    x0, x1, y0, y1 = cx - W / 2, cx + W / 2, cy - D / 2, cy + D / 2
    door = (cx - 0.6, cx + 0.6, 0.0, 2.35)
    win = (cy - 0.65, cy + 0.65, 1.0, 2.05)
    ext = mat("#5f86a8", cull=True)
    env = img_mat("envwall", os.path.join(TEX, "envwall.png"))
    t = 0.12
    # exterior shell (outward normals) and interior skin (inward normals, envelope wallpaper)
    wall_planes("dh_ext_front", "y", y0 - t, x0 - t, x1 + t, H, door, -1, ext)
    wall_planes("dh_ext_back", "y", y1 + t, x0 - t, x1 + t, H, None, 1, ext)
    wall_planes("dh_ext_w", "x", x0 - t, y0 - t, y1 + t, H, None, -1, ext)
    wall_planes("dh_ext_e", "x", x1 + t, y0 - t, y1 + t, H, win, 1, ext)
    wall_planes("dh_in_front", "y", y0, x0, x1, H, door, 1, env, uv_scale=1.3)
    wall_planes("dh_in_back", "y", y1, x0, x1, H, None, -1, env, uv_scale=1.3)
    wall_planes("dh_in_w", "x", x0, y0, y1, H, None, 1, env, uv_scale=1.3)
    wall_planes("dh_in_e", "x", x1, y0, y1, H, win, -1, env, uv_scale=1.3)
    # hole reveals, sill, floor, ceiling, trims
    multibox("dh_frames", [
        (0.12, 0.26, 2.4, door[0] - 0.06, y0 - t / 2, 1.2, "#e8e0cc"), (0.12, 0.26, 2.4, door[1] + 0.06, y0 - t / 2, 1.2, "#e8e0cc"),
        (1.36, 0.26, 0.12, cx, y0 - t / 2, 2.41, "#e8e0cc"),
        (0.4, 1.5, 0.1, x1 + 0.05, cy, 0.95, "#e8e0cc"), (0.26, 1.5, 0.1, x1 + t / 2, cy, 2.1, "#e8e0cc"),
        (0.26, 0.1, 1.15, x1 + t / 2, win[0] - 0.05, 1.52, "#e8e0cc"), (0.26, 0.1, 1.15, x1 + t / 2, win[1] + 0.05, 1.52, "#e8e0cc"),
        (W + 0.5, D + 0.5, 0.2, cx, cy, 0.0, "#6d6252"),
        (W, D, 0.06, cx, cy, 0.11, "#7a5a3e"),
        (W + 0.3, 0.1, 0.25, cx, y0 - 0.2, 0.12, "#4a5a6a")])
    poly("dh_ceiling", [(x0, y0, H), (x1, y0, H), (x1, y1, H), (x0, y1, H)], [(3, 2, 1, 0)], mat("#5a4632", cull=True))
    rh = 1.9
    o = 0.45
    vs = [(x0 - o, y0 - o, H), (x1 + o, y0 - o, H), (x1 + o, y1 + o, H), (x0 - o, y1 + o, H), (cx, y0 - o, H + rh), (cx, y1 + o, H + rh)]
    poly("dh_roof", vs, [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], mat("#4f4a52", cull=True))
    poly("dh_gable", [(x0 - t, y0 - t, H), (x1 + t, y0 - t, H), (cx, y0 - t, H + rh - 0.1),
                      (x0 - t, y1 + t, H), (x1 + t, y1 + t, H), (cx, y1 + t, H + rh - 0.1)],
         [(0, 1, 2), (3, 5, 4)], mat("#5f86a8"))
    # door (hinged, swings inward)
    hinge = empty("dh_door_hinge", (door[0], y0 - 0.02, 0.0))
    multibox("dh_door", [(1.2, 0.08, 2.33, 0.6, 0, 1.17, "#3f5f7e"), (0.1, 0.12, 0.1, 1.05, -0.08, 1.15, "#c8a85a"),
                         (0.9, 0.1, 0.6, 0.6, 0, 1.75, "#355070")], parent=hinge)
    # envelopes sticking out of the walls (3D depth on top of the wallpaper)
    env3 = []
    for i in range(260):
        side = rnd.choice(["w", "w", "back", "back", "front", "e"])
        z = rnd.uniform(0.35, 3.0)
        rz_ = rnd.uniform(-0.3, 0.3)
        if side == "w":
            p = (x0 + 0.03, rnd.uniform(y0 + 0.3, y1 - 0.3)); dims = (0.03, 0.3, 0.2)
        elif side == "e":
            yy = rnd.uniform(y0 + 0.3, y1 - 0.3)
            if win[0] - 0.3 < yy < win[1] + 0.3 and z > 0.7: continue
            p = (x1 - 0.03, yy); dims = (0.03, 0.3, 0.2)
        elif side == "back":
            xx = rnd.uniform(x0 + 0.3, x1 - 0.3)
            if abs(xx - cx) < 0.5 and 1.4 < z < 2.2: continue
            p = (xx, y1 - 0.03); dims = (0.3, 0.03, 0.2)
        else:
            xx = rnd.uniform(x0 + 0.3, x1 - 0.3)
            if door[0] - 0.3 < xx < door[1] + 0.3: continue
            p = (xx, y0 + 0.03); dims = (0.3, 0.03, 0.2)
        if side == "w" and 28.2 < p[1] < 29.8 and 1.0 < z < 2.0:   # keep the name shelf clear
            continue
        env3.append((dims[0], dims[1], dims[2], p[0], p[1], z, CREAM, rz_ if side in ("back", "front") else 0))
        sd = 0.045
        if side in ("w", "e"):
            env3.append((0.05, sd, sd, p[0] + (0.02 if side == "w" else -0.02), p[1], z, SEAL))
        else:
            env3.append((sd, 0.05, sd, p[0], p[1] + (0.02 if side == "front" else -0.02), z, SEAL))
    multibox("dh_envelopes", env3)
    # the shelf of kids' names (west wall)
    sh = [(0.36, 1.9, 0.05, x0 + 0.18, cy - 1.0, z, "#6a4a30") for z in (1.15, 1.62)]
    names = ["CLARA", "THEO", "MAYA", "JONAH", "LUCY", "SAM", "IVY", "BEN"]
    for i, nm in enumerate(names):
        zz = 1.18 if i < 4 else 1.65
        yy = cy - 1.75 + (i % 4) * 0.5
        sh.append((0.05, 0.36, 0.26, x0 + 0.25, yy, zz + 0.13, CREAM, 0))
        sh.append((0.06, 0.06, 0.06, x0 + 0.28, yy, zz + 0.2, SEAL))
        text(f"dh_name_{nm}", nm, (x0 + 0.285, yy, zz + 0.07), math.radians(90), 0.075, "#2c2418", extrude=0.005)
    multibox("dh_shelf", sh)
    text("dh_shelf_label", "KIDS", (x0 + 0.21, cy - 1.0, 1.98), math.radians(90), 0.14, "#e8e0cc", extrude=0.005)
    # the ELI letter alone on its hook (back wall)
    cyl("dh_hook", 0.025, 0.12, (cx, y1 - 0.12, 2.0), "#8f8f8f", seg=6, rot=(math.radians(90), 0, 0))
    multibox("dh_eli_env", [(0.4, 0.03, 0.27, cx, y1 - 0.09, 1.78, CREAM), (0.07, 0.04, 0.07, cx, y1 - 0.11, 1.72, SEAL)])
    text("dh_eli_text", "ELI", (cx, y1 - 0.115, 1.83), 0, 0.09, "#2c2418", extrude=0.005)
    # furniture: table, lamp, stacks, chair, mailbag
    multibox("dh_furniture", [(1.4, 0.9, 0.08, cx - 0.6, cy + 1.2, 0.8, "#6a4a30")] +
             [(0.08, 0.08, 0.76, cx - 0.6 + dx, cy + 1.2 + dy, 0.4, "#5a3e28") for dx in (-0.6, 0.6) for dy in (-0.38, 0.38)] +
             [(0.34, 0.24, 0.05 + 0.03 * i, cx - 0.9 + 0.1 * i, cy + 1.15, 0.86 + 0.02 * i, CREAM, 0.2 * i) for i in range(4)] +
             [(0.6, 0.6, 0.08, cx + 0.4, cy + 1.1, 0.48, "#6a4a30"), (0.6, 0.08, 0.7, cx + 0.4, cy + 1.42, 0.85, "#6a4a30"),
              (0.7, 0.4, 0.6, cx + 2.2, cy - 2.2, 0.42, "#6a4e36"), (0.08, 0.5, 0.6, cx + 2.2, cy - 2.2, 0.9, "#4a3a28")])
    cyl("dh_lamp", 0.16, 0.35, (cx - 1.0, cy + 1.3, 0.84), "#d9c27a", seg=8, r2=0.08)
    lt = bpy.data.lights.new("dobbs_lamp", "POINT")
    lt.energy = 160
    lt.color = (1.0, 0.78, 0.5)
    lt.shadow_soft_size = 0.05
    lo = bpy.data.objects.new("dobbs_lamp", lt)
    lo.location = (cx - 0.4, cy + 0.4, 2.6)
    link(lo)


def eli_house():
    x, y = ELI_HOUSE
    house("eli_house", x, y, 90, w=7, d=7, h=3.6, wall="#8b9aa6", roof="#5e4c3e")
    fence("eli_fence_l", (x - 6, -8.8), (x - 0.85, -8.8))
    fence("eli_fence_r", (x + 0.85, -8.8), (x + 6, -8.8))
    gh = empty("eli_gate_hinge", (x - 0.8, -8.8, 0))
    multibox("eli_gate", [(0.12, 0.1, 1.1, 0.08 + i * 0.3, 0, 0.6, "#8a7052") for i in range(6)] +
             [(1.6, 0.08, 0.12, 0.8, 0, 0.45, "#7d6448"), (1.6, 0.08, 0.12, 0.8, 0, 0.95, "#7d6448")], parent=gh)
    mx, my = -52.6, -8.45
    multibox("mailbox", [(0.1, 0.1, 1.0, mx, my - 0.1, 0.5, "#5e4a38"), (0.36, 0.5, 0.06, mx, my - 0.1, 0.97, "#5e4a38"),
                         (0.34, 0.52, 0.04, mx, my - 0.1, 1.0, "#5d6a70"), (0.04, 0.52, 0.3, mx - 0.17, my - 0.1, 1.15, "#5d6a70"),
                         (0.04, 0.52, 0.3, mx + 0.17, my - 0.1, 1.15, "#5d6a70"), (0.36, 0.52, 0.06, mx, my - 0.1, 1.31, "#5d6a70"),
                         (0.34, 0.04, 0.3, mx, my - 0.36, 1.15, "#4d585e"),
                         (0.03, 0.2, 0.05, mx + 0.2, my - 0.05, 1.32, "#a3302a"), (0.03, 0.05, 0.25, mx + 0.2, my + 0.03, 1.2, "#a3302a")])
    # open front lid (hinged at the bottom, folded down toward the street)
    multibox("mailbox_lid", [(0.32, 0.03, 0.28, mx, my + 0.3, 0.92, "#5d6a70")])
    # the very confused spider and its web
    sp = [(0.07, 0.07, 0.05, mx, my, 1.05, "#141210"), (0.05, 0.05, 0.05, mx, my + 0.05, 1.06, "#141210")]
    for i in range(4):
        for s in (-1, 1):
            sp.append((0.09, 0.012, 0.012, mx + s * 0.06, my - 0.02 + i * 0.025, 1.04, "#141210", s * (0.4 - i * 0.25)))
    sp += [(0.003, 0.003, 0.25, mx - 0.1 + 0.07 * i, my + 0.15, 1.15, "#d8d8d0") for i in range(4)]
    multibox("spider", sp)


def windmill(cx, cy):
    hb, ht, H = 2.6, 1.5, 9.0
    vs = [(cx - hb, cy - hb, 0), (cx + hb, cy - hb, 0), (cx + hb, cy + hb, 0), (cx - hb, cy + hb, 0),
          (cx - ht, cy - ht, H), (cx + ht, cy - ht, H), (cx + ht, cy + ht, H), (cx - ht, cy + ht, H)]
    poly("mill_tower", vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)], "#b9a07c")
    poly("mill_cap", [(cx - 1.9, cy - 1.9, H), (cx + 1.9, cy - 1.9, H), (cx + 1.9, cy + 1.9, H), (cx - 1.9, cy + 1.9, H),
                      (cx, cy - 1.9, H + 2.0), (cx, cy + 1.9, H + 2.0)],
         [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], "#6a5040")
    multibox("mill_door", [(1.3, 0.2, 2.2, cx, cy - hb - 0.02, 1.1, "#5b4030"), (1.0, 0.2, 0.8, cx, cy - 2.1, 5.2, "#4d5f6e"),
                           (3.2, 0.2, 0.7, cx, cy - hb - 0.05, 2.8, "#4f3a2a")])
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
    multibox("mill_sacks", [(0.7, 0.5, 0.6, cx + 2.2 + 0.7 * i, cy - 3.2, 0.3, "#c8b890") for i in range(3)])


def barn(cx, cy):
    multibox("barn_body", [(8, 10, 5, cx, cy, 2.5, "#8a4436"), (2.8, 0.2, 3.4, cx, cy - 5.05, 1.7, "#5e2e26"),
                           (0.15, 0.25, 3.4, cx - 1.4, cy - 5.1, 1.7, "#e8e0cc"), (0.15, 0.25, 3.4, cx + 1.4, cy - 5.1, 1.7, "#e8e0cc"),
                           (2.8, 0.25, 0.15, cx, cy - 5.1, 3.4, "#e8e0cc")])
    poly("barn_roof", [(cx - 4.4, cy - 5.3, 5), (cx + 4.4, cy - 5.3, 5), (cx + 4.4, cy + 5.3, 5), (cx - 4.4, cy + 5.3, 5),
                       (cx, cy - 5.3, 8), (cx, cy + 5.3, 8)], [(0, 1, 4), (3, 5, 2), (1, 2, 5, 4), (0, 4, 5, 3)], "#4a4440")
    fire = []
    for i in range(40):
        x = cx + rnd.uniform(-4, 4)
        y = cy + rnd.uniform(-5, 5)
        z = 5 + (1 - abs(x - cx) / 4.4) * 3 + rnd.uniform(0, 1.5)
        s = rnd.uniform(0.5, 1.4)
        fire.append((s, s, s * 1.6, x, y, z, rnd.choice(["#ff8a2a", "#ffb43a", "#ff6a1a"])))
    for i in range(8):
        fire.append((1.0, 0.3, 1.2, cx + rnd.uniform(-3, 3), cy - 5.1, rnd.uniform(1, 4), "#ff9a2a"))
    f = multibox("barn_fire", fire)
    for m in f.data.materials:
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Color"].default_value = b.inputs["Base Color"].default_value
        b.inputs["Emission Strength"].default_value = 4.0
    f.hide_render = True
    sm = multibox("barn_smoke", [(rnd.uniform(1.5, 3), rnd.uniform(1.5, 3), rnd.uniform(1.5, 2.5), cx + rnd.uniform(-3, 3),
                                  cy + rnd.uniform(-4, 4), 9 + i * 1.2, rnd.choice(["#3a3634", "#4a4644", "#2e2a28"])) for i in range(14)])
    sm.hide_render = True


def town():
    ground()
    k = 0
    for x in (-60, -50, -30, -10, 0, 10, 20, 30, 50, 60):
        house(f"house_n{k}", x + rnd.uniform(-0.5, 0.5), 14, -90, w=rnd.uniform(6.2, 7.4), d=7, h=rnd.uniform(3.2, 4.2)); k += 1
    for x in (-65, -45, -35, -25, -15, -5, 5, 15, 25, 35, 45, 55):
        house(f"house_s{k}", x + rnd.uniform(-0.5, 0.5), -14, 90, w=rnd.uniform(6.2, 7.4), d=7, h=rnd.uniform(3.2, 4.2)); k += 1
    aw = [(0.6, 1.6, 0.12, -2.1 + i * 0.6, 4.3, 2.75, "#b74b3c" if i % 2 == 0 else "#e9dfc8") for i in range(8)]
    house("bakery", -20, 14, -90, w=8, d=8, h=4.0, wall="#d6bf92", roof="#7d4734", sign="BAKERY", extra=aw)
    po_trim = [(9.2, 0.15, 0.35, 0, 4.1, 0.9, "#4f6a8a"), (9.2, 0.15, 0.2, 0, 4.1, 3.3, "#a3302a")]
    house("post_office", 40, 14, -90, w=9, d=8, h=4.3, wall="#cdbb98", roof="#5a5f62", sign="POST OFFICE", extra=po_trim)
    multibox("po_box", [(0.7, 0.6, 1.1, 44, 9.0, 0.75, "#4f6a8a"), (0.8, 0.7, 0.2, 44, 9.0, 1.35, "#3f5470"),
                        (0.16, 0.16, 0.3, 44, 9.0, 0.15, "#2c3430"), (0.4, 0.05, 0.06, 44, 8.68, 1.05, "#1c1c1c")])
    windmill(-36, 26)
    eli_house()
    dobbs_house()
    barn(-100, 14)
    # town hall + plaza + podium
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
    multibox("podium", [(3.2, 3.6, 0.6, 66.6, 0, 0.3, "#7a5c40"), (0.7, 1.2, 1.15, 65.7, 0, 1.17, "#5e4430"),
                        (0.9, 1.4, 0.08, 65.65, 0, 1.78, "#4a3626"), (0.12, 2.2, 0.3, 64.9, 0, 0.75, "#a0453a")])
    cyl("flagpole", 0.08, 9, (70, 9, 0), "#3e3b38", seg=6)
    multibox("flag", [(0.05, 2.2, 1.3, 70, 10.15, 8.2, "#8a4a3a")])
    # field + crops + fences
    multibox("field_soil", [(36, 36, 0.05, -92, -4, 0.03, "#6e553e")])
    crops = []
    for r in range(-11, 6):
        yy = r * 1.55 - 4
        crops.append((35, 0.55, 0.12, -92, yy, 0.08, "#5c4532"))
        for i in range(44):
            xx = -74.5 - i * 0.8
            crops.append((0.28, 0.28, 0.32 + 0.1 * ((i * 7 + r) % 3), xx, yy, 0.3, "#6d7a3c"))
    multibox("crops", crops)
    fence("field_f1", (-74, -22), (-110, -22))
    fence("field_f2", (-74, 5), (-88, 5))
    fence("perim", (-72, -4.5), (-72, -21))
    for i, (x, y) in enumerate([(-25.5, 8.6), (-26.3, 9.3), (-62.2, 4.6), (-62.9, 5.4), (-61.4, 5.4), (72, -7),
                                (35.5, 9.5), (-4, 8.6), (16, -8.5), (5.6, -8.6), (-40, 17.5), (46, 26.5)]):
        barrel(f"barrel{i}", x, y)
    for i, x in enumerate((-45, -28, -2, 22, 34, 55, 62)):
        lamp(f"lamp{i}", x, 6.6)
    xs = (-70, -59, -45, -30, -15, 0, 15, 30, 48, 62)
    for i, x in enumerate(xs):
        pole(f"pole{i}", x, -6.2)
    for a, b in zip(xs, xs[1:]):
        for dy in (-0.9, 0.9):
            wire(f"wire_{a}_{dy}", (a, -6.2 + dy, 7.45), (b, -6.2 + dy, 7.45))
    K.trees()


def kitchen():
    cx, cy = INT_KITCHEN
    H = 3.2
    x0, x1, y0, y1 = cx - 5, cx + 5, cy - 5, cy + 5
    wm = mat("#c9b48e", cull=True)
    multibox("k_floor", [(10, 10, 0.1, cx, cy, 0.05, "#8a6a4a")])
    poly("k_wall_back", [(x0, y1, 0), (x0, y1, H), (x1, y1, H), (x1, y1, 0)], [(0, 1, 2, 3)], wm)
    poly("k_wall_l", [(x0, y0, 0), (x0, y0, H), (x0, y1, H), (x0, y1, 0)], [(3, 2, 1, 0)], wm)
    poly("k_wall_r", [(x1, y0, 0), (x1, y0, H), (x1, y1, H), (x1, y1, 0)], [(0, 1, 2, 3)], wm)
    poly("k_wall_f", [(x0, y0, 0), (x0, y0, H), (x1, y0, H), (x1, y0, 0)], [(3, 2, 1, 0)], wm)
    t = [(2.8, 1.6, 0.12, cx, cy + 2, 0.9, "#7a5534")]
    t += [(0.12, 0.12, 0.86, cx + sx, cy + 2 + sy, 0.43, "#5e4028") for sx in (-1.25, 1.25) for sy in (-0.65, 0.65)]
    for (px, py, back) in ((cx - 1.25, cy + 2, "w"), (cx + 1.25, cy + 2, "e"), (cx, cy + 3.4, "n")):
        t += [(0.75, 0.75, 0.1, px + (-0.55 if back == "w" else 0.55 if back == "e" else 0), py + (0.55 if back == "n" else 0), 0.5, "#6a4a30")]
    t += [(0.1, 0.75, 1.0, cx - 2.2, cy + 2, 1.0, "#6a4a30"), (0.1, 0.75, 1.0, cx + 2.2, cy + 2, 1.0, "#6a4a30"),
          (0.75, 0.1, 1.0, cx, cy + 4.3, 1.0, "#6a4a30")]
    t += [(5.0, 0.9, 1.0, cx + 2.2, cy + 4.5, 0.5, "#9a7a58"), (5.0, 1.0, 0.08, cx + 2.2, cy + 4.5, 1.04, "#d7cdb8"),
          (1.6, 0.06, 1.1, cx - 2.6, cy + 4.95, 1.9, "#8fb0c4"), (1.8, 0.08, 0.1, cx - 2.6, cy + 4.93, 1.32, "#e8e0cc"),
          (1.1, 0.9, 2.1, cx - 4.2, cy + 4.4, 1.05, "#d9d3c4"), (3.0, 2.0, 0.02, cx, cy + 0.6, 0.11, "#7d4b40"),
          (2.8, 0.04, 0.7, cx + 1, cy - 4.95, 1.9, "#a09070")]
    multibox("k_props", t)
    for i, (dx, dy) in enumerate(((-0.8, 0), (0.8, 0), (0, 0.5))):
        cyl(f"bowl{i}", 0.2, 0.12, (cx + dx, cy + 2 + dy, 0.96), "#e2d8c0", seg=10, r2=0.24)
        cyl(f"soup{i}", 0.19, 0.02, (cx + dx, cy + 2 + dy, 1.06), "#b0763a", seg=10)
    cyl("k_pot", 0.3, 0.35, (cx, cy + 1.6, 0.96), "#4a4a4c", seg=10)
    lt = bpy.data.lights.new("kitchen_lamp", "POINT")
    lt.energy = 45
    lt.color = (1.0, 0.85, 0.62)
    lo = bpy.data.objects.new("kitchen_lamp", lt)
    lo.location = (cx, cy + 2, 2.9)
    link(lo)
    multibox("k_lampshade", [(0.6, 0.6, 0.25, cx, cy + 2, 3.05, "#3e3b38")])


def face_plane(name, parent, img_path):
    s = 0.29
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = "FACE"
    tex.interpolation = "Closest"
    tex.image = bpy.data.images.load(img_path, check_existing=True)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    ob = poly(name, [(s, 0, -s), (-s, 0, -s), (-s, 0, s), (s, 0, s)], [(0, 1, 2, 3)], m, parent=parent,
              uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    ob.location = (0, 0.312, 0.33)
    return ob


def character(name, spec):
    sk, shirt, pants, hair, kind = spec["skin"], spec["shirt"], spec["pants"], spec["hair"], spec["kind"]
    root = empty(name + "_root", (0, 0, -200))
    root.scale = (spec["scale"],) * 3
    torso = [(0.92, 0.46, 0.9, 0, 0, 1.35, shirt)]
    if kind == "mayor":
        torso += [(0.3, 0.05, 0.62, 0, 0.235, 1.48, "#e8e4da"), (0.1, 0.06, 0.5, 0, 0.245, 1.45, "#7a2e2e"),
                  (0.96, 0.5, 0.12, 0, 0, 0.95, "#2f3034")]
    if kind == "baker":
        torso += [(0.78, 0.05, 1.2, 0, 0.235, 1.2, "#f6f2ea")]
    if kind == "mail":   # big mailbag the size of a sheep, strap across the chest
        torso += [(0.12, 0.52, 1.0, 0.0, 0.0, 1.4, "#5a4430", 0.75), (0.5, 0.95, 0.85, -0.75, 0.05, 0.95, "#8a6a46"),
                  (0.52, 0.97, 0.12, -0.75, 0.05, 1.33, "#6a5034"), (0.2, 0.06, 0.2, -0.99, 0.2, 1.1, "#c8a85a"),
                  (0.6, 0.05, 0.1, 0.0, 0.235, 1.75, "#3f5470")]
    if kind == "pell":
        torso += [(1.0, 0.6, 0.65, 0, 0, 0.62, pants)]
    if kind == "mom":
        torso += [(0.96, 0.56, 0.55, 0, 0, 0.66, pants)]
    if kind == "kid":
        torso += [(0.6, 0.05, 0.08, 0, 0.235, 1.6, "#e8e0cc")]
    if kind == "farmer":
        torso += [(0.94, 0.48, 0.5, 0, 0, 1.15, "#4a5a6a"), (0.1, 0.05, 0.4, -0.25, 0.24, 1.6, "#4a5a6a"),
                  (0.1, 0.05, 0.4, 0.25, 0.24, 1.6, "#4a5a6a")]
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
    if kind == "mom":
        hb += [(0.7, 0.2, 0.8, 0, -0.3, 0.3, hair), (0.12, 0.4, 0.6, -0.34, -0.1, 0.35, hair), (0.12, 0.4, 0.6, 0.34, -0.1, 0.35, hair)]
    if kind == "dad":
        hb += [(0.26, 0.04, 0.05, 0, 0.318, 0.27, "#3a2a1e")]
    if kind == "mail":   # sweat drops
        hb = [(0.66, 0.66, 0.12, 0, -0.01, 0.66, hair), (0.1, 0.5, 0.3, -0.33, -0.05, 0.5, hair), (0.1, 0.5, 0.3, 0.33, -0.05, 0.5, hair),
              (0.68, 0.16, 0.4, 0, -0.27, 0.4, hair),
              (0.06, 0.04, 0.1, 0.18, 0.325, 0.55, "#bfe0f0"), (0.05, 0.04, 0.08, -0.22, 0.325, 0.4, "#bfe0f0"),
              (0.04, 0.06, 0.1, 0.335, 0.15, 0.35, "#bfe0f0"), (0.04, 0.06, 0.08, -0.335, 0.1, 0.45, "#bfe0f0")]
    if kind == "farmer":
        hb += [(1.0, 1.0, 0.05, 0, 0, 0.74, "#d8c078"), (0.62, 0.62, 0.3, 0, 0, 0.9, "#d8c078"), (0.64, 0.64, 0.06, 0, 0, 0.8, "#8a4436")]
    multibox(name + "_hair", hb, parent=head)
    if kind == "mail":
        cap = multibox(name + "_cap", [(0.72, 0.72, 0.2, 0, 0, 0.0, "#3f5470"), (0.6, 0.34, 0.05, 0, 0.45, -0.07, "#2f3f52"),
                                       (0.3, 0.04, 0.1, 0, 0.365, 0.02, "#c8a85a")], parent=head)
        cap.location = (0, 0, 0.72)
    if kind == "baker":
        cyl(name + "_hat", 0.3, 0.36, (0, 0, 0.66), "#f6f2ea", seg=10, parent=head)
        cyl(name + "_hat_top", 0.42, 0.3, (0, 0, 0.98), "#ffffff", seg=10, r2=0.36, parent=head)
    if name in HELD:
        arm = bpy.data.objects[name + "_armR"]
        env = multibox(name + "_env", [(0.36, 0.25, 0.025, 0, 0, 0, CREAM), (0.07, 0.07, 0.05, 0, 0, 0, SEAL)], parent=arm)
        env.location = (0, 0.1, -0.86)
        env.hide_render = True
        label = {"eli2": "MR. DOBBS", "mayor": "MAYOR"}.get(name, "ELI")
        for zs, rx in ((1, 0.0), (-1, math.pi)):
            tx = text(f"{name}_env_text{zs}", label, (0, 0.075, zs * 0.0135), 0, 0.055 if len(label) > 4 else 0.075,
                      "#2c2418", parent=env, extrude=0.002)
            tx.rotation_euler = (rx, 0, math.pi)
    return root


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    K.world_and_render()
    town()
    kitchen()
    for n, spec in CAST.items():
        character(n, spec)
    out = os.path.join(HERE, "build", "town.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("saved", out, "objects:", len(bpy.data.objects))


if __name__ == "__main__":
    main()
