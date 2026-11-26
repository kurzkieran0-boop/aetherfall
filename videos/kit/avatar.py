"""Blocky avatar rig (bpy): cube torso/limbs/head, swappable face texture, hats/kit extras, held props,
and the chest COUNTER (dark rounded pill + 4 glowing digit planes whose images are swapped per frame).

CAST spec keys: shirt, pants, hair, skin, scale, kind, held=[...], counter=True/False
kinds: kid, mail, mom, dad, baker, pell, mayor, farmer, granny, baby, doctor, plain
"""
import bpy, math, os
from blocks import mat, multibox, poly, cyl, empty, text
from common import FACE_EXPR, DIGITS

CREAM, SEAL = "#efe5c8", "#a3302a"


def _img_plane(name, parent, img_path, size, loc, emit=0.0):
    sx, sz = size
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = "IMG"
    tex.interpolation = "Closest" if not emit else "Linear"
    tex.image = bpy.data.images.load(str(img_path), check_existing=True)
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    if emit:
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    ob = poly(name, [(sx, 0, -sz), (-sx, 0, -sz), (-sx, 0, sz), (sx, 0, sz)], [(0, 1, 2, 3)], m, parent=parent,
              uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    ob.location = loc
    return ob


def held_prop(name, kind, arm, label="ELI"):
    """A prop in the right hand, hidden unless an act shows it."""
    if kind == "env":
        ob = multibox(f"{name}_held_env", [(0.36, 0.25, 0.025, 0, 0, 0, CREAM), (0.07, 0.07, 0.05, 0, 0, 0, SEAL)], parent=arm)
        for zs, rx in ((1, 0.0), (-1, math.pi)):
            tx = text(f"{name}_held_env_text{zs}", label, (0, 0.075, zs * 0.0135), 0, 0.055 if len(label) > 4 else 0.075,
                      "#2c2418", parent=ob, extrude=0.002)
            tx.rotation_euler = (rx, 0, math.pi)
    elif kind == "postcard":
        ob = multibox(f"{name}_held_postcard", [(0.34, 0.24, 0.02, 0, 0, 0, "#e8d8a8"), (0.12, 0.1, 0.03, 0.08, 0.05, 0, "#6a9ab0")], parent=arm)
    elif kind == "whiteboard":
        ob = multibox(f"{name}_held_whiteboard", [(0.7, 0.5, 0.03, 0, 0.12, 0, "#f4f4f0"), (0.74, 0.54, 0.02, 0, 0.12, -0.012, "#4a6a8a")], parent=arm)
        for zs, rx in ((1, 0.0), (-1, math.pi)):
            tx = text(f"{name}_held_whiteboard_text{zs}", label, (0, 0.12, zs * 0.018), 0,
                      min(0.16, 0.6 / max(1, len(label)) * 1.6), "#2a3a6a", parent=ob, extrude=0.002)
            tx.rotation_euler = (rx, 0, 0)
    elif kind == "thermos":
        ob = multibox(f"{name}_held_thermos", [(0.14, 0.14, 0.4, 0, 0.0, 0, "#a3302a"), (0.15, 0.15, 0.08, 0, 0, 0.22, "#d8d8d0")], parent=arm)
    elif kind == "loaf":
        ob = multibox(f"{name}_held_loaf", [(0.45, 0.22, 0.2, 0, 0.05, 0, "#c08a4a"), (0.3, 0.16, 0.06, 0, 0.05, 0.11, "#d8a868")], parent=arm)
    elif kind == "crumb":
        ob = multibox(f"{name}_held_crumb", [(0.06, 0.06, 0.05, 0, 0.0, 0, "#c08a4a")], parent=arm)
    elif kind == "key":
        ob = multibox(f"{name}_held_key", [(0.05, 0.3, 0.02, 0, 0.05, 0, "#c9b16a"), (0.14, 0.12, 0.03, 0, 0.22, 0, "#c9b16a")], parent=arm)
    else:
        ob = multibox(f"{name}_held_{kind}", [(0.2, 0.2, 0.2, 0, 0, 0, "#888888")], parent=arm)
    ob.location = (0, 0.1, -0.86)
    if kind == "whiteboard":          # writing faces outward, toward whoever the holder shows it to
        ob.rotation_euler = (0, math.pi, 0)
    ob.hide_render = True
    for c in ob.children:
        c.hide_render = True
    return ob


def character(name, spec, faces_dir, digits_dir=None):
    sk, shirt, pants, hair, kind = spec["skin"], spec["shirt"], spec["pants"], spec["hair"], spec["kind"]
    root = empty(name + "_root", (0, 0, -200))
    root.scale = (spec["scale"],) * 3
    torso = [(0.92, 0.46, 0.9, 0, 0, 1.35, shirt)]
    if kind == "mayor":
        torso += [(0.3, 0.05, 0.62, 0, 0.235, 1.48, "#e8e4da"), (0.1, 0.06, 0.5, 0, 0.245, 1.45, "#7a2e2e"),
                  (0.96, 0.5, 0.12, 0, 0, 0.95, "#2f3034")]
    if kind == "baker":
        torso += [(0.78, 0.05, 1.2, 0, 0.235, 1.2, "#f6f2ea")]
    if kind == "doctor":
        torso += [(0.96, 0.5, 1.0, 0, 0, 1.3, "#f2f2ee"), (0.3, 0.05, 0.3, 0.2, 0.26, 1.6, "#a3302a")]
    if kind == "mail":
        torso += [(0.12, 0.52, 1.0, 0.0, 0.0, 1.4, "#5a4430", 0.75), (0.5, 0.95, 0.85, -0.75, 0.05, 0.95, "#8a6a46"),
                  (0.52, 0.97, 0.12, -0.75, 0.05, 1.33, "#6a5034"), (0.2, 0.06, 0.2, -0.99, 0.2, 1.1, "#c8a85a")]
    if kind in ("pell", "granny"):
        torso += [(1.0, 0.6, 0.65, 0, 0, 0.62, pants)]
    if kind == "granny":
        torso += [(0.98, 0.5, 0.35, 0, 0, 1.68, "#c8b8a8")]   # shawl
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
    fp = _img_plane(name + "_face", head, os.path.join(faces_dir, f"{name}_neutral.png"), (0.29, 0.29), (0, 0.312, 0.33))
    fp.active_material.node_tree.nodes["IMG"].name = "FACE"
    hb = [(0.68, 0.68, 0.16, 0, -0.02, 0.69, hair), (0.68, 0.16, 0.5, 0, -0.27, 0.45, hair),
          (0.1, 0.5, 0.36, -0.33, -0.05, 0.5, hair), (0.1, 0.5, 0.36, 0.33, -0.05, 0.5, hair)]
    if kind == "kid":
        hb += [(0.2, 0.2, 0.14, 0.12, 0.12, 0.82, hair, 0.5), (0.7, 0.12, 0.1, 0, 0.3, 0.63, hair)]
    if kind == "baby":
        hb = [(0.3, 0.3, 0.1, 0, 0, 0.68, hair)]
    if kind == "mayor":
        hb = [(0.9, 0.9, 0.06, 0, 0, 0.72, "#55585c"), (0.6, 0.6, 0.62, 0, 0, 1.04, "#6b6e72"),
              (0.62, 0.62, 0.1, 0, 0, 0.8, "#2f3034"), (0.1, 0.5, 0.25, -0.33, -0.05, 0.55, hair),
              (0.1, 0.5, 0.25, 0.33, -0.05, 0.55, hair)]
    if kind == "pell":
        hb += [(0.32, 0.32, 0.3, 0, -0.18, 0.85, hair)]
    if kind == "granny":
        hb += [(0.36, 0.36, 0.32, 0, -0.12, 0.88, hair), (0.66, 0.04, 0.08, 0, 0.32, 0.38, "#3a3a3a")]  # bun + glasses bar
    if kind == "mom":
        hb += [(0.7, 0.2, 0.8, 0, -0.3, 0.3, hair), (0.12, 0.4, 0.6, -0.34, -0.1, 0.35, hair), (0.12, 0.4, 0.6, 0.34, -0.1, 0.35, hair)]
    if kind == "dad":
        hb += [(0.26, 0.04, 0.05, 0, 0.318, 0.27, "#3a2a1e")]
    if kind == "mail":
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
    arm = bpy.data.objects[name + "_armR"]
    for kd in spec.get("held", []):
        held_prop(name, kd, arm, label=spec.get("label", "ELI"))
    if spec.get("counter") and digits_dir:
        torso_ob = bpy.data.objects[name + "_torso"]
        multibox(name + "_counter_pill", [(0.56, 0.05, 0.25, 0, 0.255, 1.43, "#16191e")], parent=torso_ob)
        for sx in (-0.28, 0.28):
            cyl(f"{name}_counter_cap{sx}", 0.125, 0.05, (sx, 0.23, 1.43), "#16191e", seg=12, parent=torso_ob,
                rot=(math.radians(-90), 0, 0))
        for i, dx in enumerate((0.195, 0.065, -0.065, -0.195)):  # slot 0 = leftmost as seen from the front
            p = _img_plane(f"{name}_digit{i}", torso_ob, os.path.join(digits_dir, "teal_0.png"), (0.058, 0.09),
                           (dx, 0.284, 1.43), emit=3.0)
            p.active_material.node_tree.nodes["IMG"].name = "DIG"
    return root
