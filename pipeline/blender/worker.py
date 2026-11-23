"""Render one shot.  Usage (either works):
    blender -b -P pipeline/blender/worker.py -- <job.json>
    python3 pipeline/blender/worker.py <job.json>         (pip `bpy` module)

job.json = { "shot": {...shot from shotlist...}, "film": {...film context...},
             "render": {"w":540,"h":960,"step":2,"samples":8,"out_dir":...,
                        "budget_s": 6.0, "still": false} }
Writes frames to out_dir/f_####.png, meta.json (timings, screen-safe boxes).
"""
import json
import math
import os
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit as K  # noqa: E402
import camera as CAM  # noqa: E402

LOOKS = {
    # film grade + key/rim colours per look (post grade lives in compose.py)
    "night_blue": dict(key=(1.0, 0.82, 0.62), rim=(0.45, 0.65, 1.0), fill=(0.3, 0.4, 0.8), exposure=0.4),
    "storm": dict(key=(0.9, 0.9, 1.0), rim=(0.5, 0.7, 1.0), fill=(0.25, 0.3, 0.5), exposure=0.3),
    "ember": dict(key=(1.0, 0.7, 0.45), rim=(1.0, 0.45, 0.2), fill=(0.25, 0.3, 0.55), exposure=0.35),
    "sunny": dict(key=(1.0, 0.93, 0.82), rim=(1.0, 0.85, 0.6), fill=(0.55, 0.7, 1.0), exposure=-0.55, bloom=3.0),
    "toxic": dict(key=(0.9, 1.0, 0.85), rim=(0.3, 1.0, 0.6), fill=(0.2, 0.35, 0.5), exposure=0.35),
    "kindness": dict(key=(1.0, 0.8, 0.6), rim=(0.45, 0.62, 1.0), fill=(0.25, 0.32, 0.65), exposure=-0.2, bloom=1.6),
}


def args():
    a = sys.argv
    if "--" in a:
        a = a[a.index("--") + 1:]
    else:
        a = a[1:]
    return a[0]


def setup_render(r, look):
    scn = bpy.context.scene
    scn.render.engine = 'BLENDER_EEVEE'
    scn.render.resolution_x = r["w"]
    scn.render.resolution_y = r["h"]
    scn.render.resolution_percentage = 100
    scn.render.fps = 24
    scn.render.image_settings.file_format = 'PNG'
    scn.render.image_settings.color_mode = 'RGB'
    scn.render.film_transparent = False
    e = scn.eevee
    e.taa_render_samples = r.get("samples", 8)
    e.use_raytracing = r.get("raytrace", True)
    try:
        e.ray_tracing_method = 'SCREEN'
        e.ray_tracing_options.resolution_scale = '2' if r["w"] <= 600 else '2'
        e.ray_tracing_options.use_denoise = True
    except Exception:
        pass
    e.use_shadows = True
    e.shadow_ray_count = 1
    e.shadow_step_count = 4
    e.use_volumetric_shadows = r.get("vol_shadows", True)
    e.volumetric_tile_size = r.get("vol_tile", '8')
    e.volumetric_samples = r.get("vol_samples", 48)
    e.volumetric_end = r.get("vol_end", 400)
    e.use_fast_gi = True
    e.fast_gi_method = 'GLOBAL_ILLUMINATION'
    e.fast_gi_resolution = '4'
    scn.render.use_motion_blur = r.get("motion_blur", True)
    scn.render.motion_blur_shutter = 0.5
    vs = scn.view_settings
    vs.view_transform = 'AgX'
    try:
        vs.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    vs.exposure = LOOKS.get(look, LOOKS["night_blue"])["exposure"] + r.get("exposure_bias", 0.0)
    # compositor: HDR bloom (glare) – lens bloom on floodlights / eyes / sirens
    ng = bpy.data.node_groups.new("COMP", "CompositorNodeTree")
    scn.compositing_node_group = ng
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new("CompositorNodeRLayers")
    g = ng.nodes.new("CompositorNodeGlare")
    g.inputs["Type"].default_value = 'Bloom'
    g.inputs["Quality"].default_value = 'Medium' if r["w"] > 600 else 'Low'
    g.inputs["Threshold"].default_value = LOOKS.get(look, {}).get("bloom", 1.2)
    g.inputs["Strength"].default_value = 0.55
    g.inputs["Size"].default_value = 0.65
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(rl.outputs["Image"], g.inputs["Image"])
    ng.links.new(g.outputs["Image"], out.inputs[0])


def auto_lights(film, shot, subj, cam_keys, look):
    """Per-shot key / rim / fill rig placed relative to camera & subject: 3 deliberate
    lights on top of the set practicals."""
    L = LOOKS.get(look, LOOKS["night_blue"])
    lc = shot.get("lighting", {})
    if subj.monster is not None:
        # back-rim the giant against the sky so its silhouette always reads
        m = subj.monster
        bpy.context.scene.frame_set(cam_keys[len(cam_keys) // 2][0])
        Pm = m.root.matrix_world.translation + Vector((0, 0, m.H * 0.75))
        camp = Vector(cam_keys[len(cam_keys) // 2][1])
        back = Pm - camp
        back.z = 0
        back = back.normalized() if back.length > 0.1 else Vector((0, 1, 0))
        K.light('SPOT', Pm + back * m.H * 0.9 + Vector((0, 0, m.H * 0.5)), 1.5e6 * m.u ** 2, L["rim"], size=4,
                spot=50, name="rim_monster", target=Pm - Vector((0, 0, m.H * 0.3)), volume=0.15)
    s1 = shot["camera"].get("subject", "hero")
    if s1 == "monster" or str(s1).startswith("mark:") or isinstance(s1, list):
        s1 = shot.get("light_subject") or next(iter(subj.chars), None)
    if not s1 or s1 not in subj.chars:
        return
    bpy.context.scene.frame_set(cam_keys[len(cam_keys) // 2][0])
    P, yaw, H = subj.point(s1, "chest")
    cam = Vector(cam_keys[len(cam_keys) // 2][1])
    v = (cam - P)
    v.z = 0
    v = v.normalized() if v.length > 0.01 else Vector((0, -1, 0))
    side = v.cross(Vector((0, 0, 1)))
    ks = lc.get("key", 1.0)
    rs = lc.get("rim", 1.0)
    # key: 45° off camera, above
    kp = P + (v * 0.7 + side * 0.7).normalized() * 4 + Vector((0, 0, 2.2))
    K.light('AREA', kp, 260 * ks, L["key"], size=2.0, name="key", target=P, volume=0.2)
    # rim: behind subject, opposite side, strong + coloured
    rp = P - v * 4 - side * 1.5 + Vector((0, 0, 2.5))
    K.light('SPOT', rp, 2200 * rs, L["rim"], size=0.3, spot=40, name="rim", target=P, volume=0.6)
    # fill: low, camera side, cool
    fp = P + v * 5 - side * 2 + Vector((0, 0, 0.5))
    K.light('AREA', fp, 60 * lc.get("fill", 1.0), L["fill"], size=4, name="fill", target=P, volume=0.0)


def build(job):
    film, shot, r = job["film"], job["shot"], job["render"]
    K.reset_scene()
    nfr = shot["frames"]
    f0, f1 = 1, nfr
    handles = 6
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = f0, f1
    setname = shot.get("set", film.get("set", "city_block"))
    marks = K.SETS[setname](seed=film.get("seed", 3), frame_range=(f0 - handles, f1 + handles),
                            **shot.get("set_args", {}))
    marks = {k: tuple(v) for k, v in marks.items()}
    marks.update({k: tuple(v) for k, v in shot.get("marks", {}).items()})

    def resolve(p):
        if isinstance(p, str):
            return marks[p[5:]] if p.startswith("mark:") else marks[p]
        return tuple(p)

    # props
    for pr in shot.get("props", []):
        kind = pr["kind"]
        loc = resolve(pr.get("at", (0, 0, 0)))
        rz = math.radians(pr.get("rot", 0))
        res = None
        if kind == "police_car":
            res = K.police_car(loc, rz, (f0 - handles, f1 + handles), seed=pr.get("seed", int(loc[0] * 7 + loc[1])),
                         lights=pr.get("lights", True), name=pr.get("name", f"cop{len(bpy.data.objects)}"))
        elif kind == "sedan":
            res = K.sedan(loc, rz, tuple(pr.get("color", (0.5, 0.1, 0.1))), name=pr.get("name", "car"))
        elif kind == "barrier":
            K.barrier(loc, rz)
        elif kind == "floodlight":
            K.floodlight_tower(loc, resolve(pr.get("aim", (0, 0, 0))), pr.get("height", 14), pr.get("energy", 60000),
                               name=pr.get("name", "fl"))
        elif kind == "fence":
            K.fence(resolve(pr["start"]), resolve(pr["end"]))
        elif kind == "crane":
            K.crane(loc, pr.get("height", 70), rot_z=rz)
        elif kind == "pylon":
            K.pylon(loc, pr.get("height", 45), rot_z=rz)
        elif kind == "streetlamp":
            K.streetlamp(loc, rz, name=pr.get("name", "lamp"), energy=pr.get("energy", 1500))
        elif kind == "stall":
            res = K.stall(loc, rz, tuple(pr.get("color", (0.95, 0.35, 0.3))), name=pr.get("name", "stallx"))
        elif kind == "bench":
            K.bench(loc, rz)
        elif kind == "fire_truck":
            K.fire_truck(loc, rz, (f0 - handles, f1 + handles), name=pr.get("name", "firetruck"))
        elif kind == "rubble":
            K.rubble(resolve(pr["start"]), resolve(pr["end"]), pr.get("width", 8), pr.get("height", 3),
                     pr.get("seed", 0), count=pr.get("count", 60))
        elif kind == "crate":
            K.crate(loc, pr.get("size", 1.2), rz)
        elif kind == "tree":
            K.tree(loc, pr.get("height", 7), pr.get("seed", 0))
        elif kind == "box":
            K.box(pr.get("name", "box"), loc, tuple(pr["size"]),
                  K.emissive(tuple(pr["emit"]), pr.get("strength", 10)) if "emit" in pr else
                  K.plastic(tuple(pr.get("color", (0.3, 0.3, 0.3))), pr.get("rough", 0.5)))
        elif kind == "light":
            K.light(pr.get("type", 'POINT'), loc, pr.get("energy", 1000), tuple(pr.get("color", (1, 1, 1))),
                    pr.get("size", 0.5), spot=pr.get("spot", 45), target=resolve(pr["aim"]) if "aim" in pr else None,
                    name=pr.get("name", "plight"), volume=pr.get("volume", 1.0))

        mv = pr.get("move")
        if mv and res is not None:
            res.location = loc
            res.keyframe_insert("location", frame=mv.get("f0", f0))
            res.location = resolve(mv["to"])
            res.keyframe_insert("location", frame=mv.get("f1", f1))
            if "rot_to" in mv:
                res.keyframe_insert("rotation_euler", frame=mv.get("f0", f0))
                res.rotation_euler = (0, 0, math.radians(mv["rot_to"]))
                res.keyframe_insert("rotation_euler", frame=mv.get("f1", f1))

    # characters
    chars = {}
    for cid, cdef in film.get("characters", {}).items():
        if cid not in shot.get("cast", []):
            continue
        chars[cid] = K.Rig(cid, cdef.get("palette", {}), cdef.get("accessory", "none"), cdef.get("scale", 1.0),
                           tuple(cdef.get("skin", (0.95, 0.78, 0.3))))
        chars[cid].place(f0 - handles, (0, 0, -200))
    acted = {a["who"] for a in shot.get("actions", [])}
    for cid in chars:
        if cid not in acted:
            K.act(chars[cid], "idle", f0, f1, at=resolve(film["characters"][cid].get("mark", "hero")),
                  facing=film["characters"][cid].get("facing", 180))
    for a in shot.get("actions", []):
        who = a["who"]
        kw = {k: v for k, v in a.items() if k not in ("who", "action", "f0", "f1")}
        for k in ("at", "target", "look_at"):
            if k in kw and kw[k] is not None:
                kw[k] = resolve(kw[k]) if not (k == "look_at" and kw[k] == "monster") else kw[k]
        if "path" in kw:
            kw["path"] = [resolve(p) for p in kw["path"]]
        fa, fb = a.get("f0", f0), a.get("f1", f1)
        if fa < 0:
            fa = nfr + fa
        if fb < 0:
            fb = nfr + fb + 1
        if who == "monster":
            continue
        if who in chars:
            if kw.get("look_at") == "monster":
                mp = resolve(shot.get("monster_at", "monster"))
                kw["look_at"] = (mp[0], mp[1], (film.get("monster") or {}).get("height", 50) * 0.85)
            K.act(chars[who], a["action"], fa, fb, **kw)

    cw = shot.get("crowd")
    if cw:
        import random as _r
        rng = _r.Random(cw.get("seed", 7))
        c0 = Vector(resolve(cw["center"]))
        face_t = resolve(cw["face"]) if cw.get("face") else None
        for i in range(cw.get("n", 8)):
            a = rng.uniform(0, math.tau)
            rr = rng.uniform(cw.get("inner", 2.0), cw.get("radius", 7))
            p = c0 + Vector((math.cos(a) * rr * 1.3, math.sin(a) * rr * 0.6, 0))
            pal = cw.get("palette") or {"shirt": rng.choice(K.PASTEL + [(0.9, 0.2, 0.2), (0.2, 0.4, 0.9)]),
                   "pants": rng.choice(((0.15, 0.2, 0.4), (0.3, 0.25, 0.2), (0.2, 0.2, 0.22))),
                   "hair": rng.choice(((0.1, 0.06, 0.03), (0.6, 0.4, 0.1), (0.3, 0.15, 0.05), (0.8, 0.8, 0.8))),
                   "hat": rng.choice(K.PASTEL)}
            rg = K.Rig(f"x{i}", pal, cw.get("accessory") or rng.choice(("hair", "cap", "ponytail", "glasses", "none")), rng.uniform(0.85, 1.05),
                       rng.choice(((0.95, 0.78, 0.3), (0.85, 0.62, 0.4), (0.6, 0.42, 0.28), (0.98, 0.85, 0.7))))
            fc = None
            if face_t is not None:
                d = Vector(face_t) - p
                fc = math.degrees(math.atan2(d.y, d.x)) + 90
            elif cw.get("facing") is not None:
                fc = cw["facing"]
            for act, t0, t1 in cw.get("actions", [["cheer", 0, 1]]):
                fa = max(1, int(t0 * nfr) + rng.randint(0, 3)); fb = max(fa + 2, int(t1 * nfr))
                K.act(rg, act, fa, fb, at=tuple(p), facing=fc if fc is not None else rng.uniform(0, 360),
                      expr=rng.choice(("happy", "shock", "happy")) if act == "cheer" else None)
    for cid, item in shot.get("carry", {}).items():
        if cid in chars and item in ("cake", "cake_bags"):
            ck = K.cake(chars[cid].torso, scale=chars[cid].s * 0.95, name=f"cake_{cid}")
            K.hold_front(chars[cid], f0 - handles, f1 + handles)
            if item == "cake_bags":
                bagm = K.plastic((0.75, 0.6, 0.4), 0.8, coat=0)
                for k in range(5):
                    K.box(f"bag{k}", ((k % 2 - 0.5) * 0.25, 0.05 * k, 0.75 + k * 0.42), (0.5, 0.35, 0.45), bagm, ck,
                          rot=(0, 0, 0.3 * (k - 2)), collection="chars")
                    K.box(f"bagtop{k}", ((k % 2 - 0.5) * 0.25, 0.05 * k, 1.0 + k * 0.42), (0.35, 0.25, 0.12),
                          K.plastic(((0.3, 0.7, 0.2), (0.95, 0.5, 0.1), (0.9, 0.1, 0.1))[k % 3], 0.6), ck, collection="chars")
    sp = shot.get("splat")
    if sp and sp["who"] in chars:
        rg = chars[sp["who"]]
        cols = ((0.98, 0.75, 0.85), (1.0, 0.98, 0.92), (0.95, 0.35, 0.5))
        import random as _r
        rr = _r.Random(3)
        for k in range(14):
            o = K.box(f"icing{k}", (rr.uniform(-0.3, 0.3), -0.31, rr.uniform(0.05, 0.55)), (rr.uniform(0.1, 0.25), 0.06, rr.uniform(0.08, 0.2)),
                      K.plastic(cols[k % 3], 0.3), rg.head, bevel=0.02, collection="chars")
            o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=sp["f"] - 1)
            o.scale = (rr.uniform(0.1, 0.25), 0.06, rr.uniform(0.08, 0.2)); o.keyframe_insert("scale", frame=sp["f"])
        ck = bpy.data.objects.get(f"cake_{sp['who']}")
        if ck:
            ck.keyframe_insert("scale", frame=sp["f"] - 1)
            ck.scale = (0.001,) * 3
            ck.keyframe_insert("scale", frame=sp["f"])
        bpy.context.scene.frame_set(sp["f"])
        hp = rg.head.matrix_world.translation
        for k in range(30):
            o = K.box(f"crumb{k}", tuple(hp), (0.08, 0.08, 0.08), K.plastic(cols[k % 3], 0.3), collection="fx")
            v = Vector((rr.uniform(-1, 1), rr.uniform(-1.5, -0.2), rr.uniform(0.5, 2.0))) * 3
            o.scale = (0.001,) * 3; o.keyframe_insert("scale", frame=sp["f"] - 1)
            o.scale = (1, 1, 1)
            for j in range(0, 24, 2):
                t = j / 24
                p = hp + v * t + Vector((0, 0, -4.9 * t * t))
                p.z = max(0.15, p.z)
                o.location = p; o.keyframe_insert("location", frame=sp["f"] + j)
    tk = shot.get("talk")
    if tk and tk["who"] in chars:
        chars[tk["who"]].talk(tk["f0"], tk["f1"])
    # monster
    monster = None
    impacts = []
    if shot.get("monster", True) and film.get("monster"):
        monster = K.Monster(film["monster"])
        monster.place(f0 - handles, resolve(shot.get("monster_at", "monster")), shot.get("monster_facing", 0))
        if shot.get("monster_glow") is not None:
            monster.glow(f0 - handles, shot["monster_glow"])
        for a in shot.get("actions", []):
            if a["who"] != "monster":
                continue
            kw = {k: v for k, v in a.items() if k not in ("who", "action", "f0", "f1")}
            if "path" in kw:
                kw["path"] = [resolve(p) for p in kw["path"]]
            if "at" in kw:
                kw["at"] = resolve(kw["at"])
            if "look_at" in kw and isinstance(kw["look_at"], str):
                kw["look_at"] = resolve(kw["look_at"]) if kw["look_at"] in marks or kw["look_at"].startswith("mark:") else None
            fa, fb = a.get("f0", f0), a.get("f1", f1)
            if fb < 0:
                fb = nfr + fb + 1
            monster.action(a["action"], fa, fb, **kw)
        for (fi, loc) in monster.impacts:
            power = 1.0 if monster.kind != "stalker" else 0.6
            impacts.append((fi, loc, power * shot.get("impact_power", 1.0)))
            if shot.get("debris", True) and f0 - 2 <= fi <= f1:
                K.debris_burst(fi, loc, count=int(30 * shot.get("impact_power", 1.0)), power=1.0 + monster.u * 0.3)
                K.dust_cloud(fi, loc, radius=8 * monster.u + 4)
    for ex in shot.get("impacts", []):  # explicit impacts (falling debris, car crash ...)
        impacts.append((ex["f"], resolve(ex["at"]), ex.get("power", 1.0)))
        if ex.get("debris", True):
            K.debris_burst(ex["f"], resolve(ex["at"]), count=ex.get("count", 25), power=ex.get("power", 1.0))
            K.dust_cloud(ex["f"], resolve(ex["at"]), radius=ex.get("radius", 8))

    # fx
    subj = CAM.Subjects(chars, monster, marks)
    fx = shot.get("fx", film.get("fx", []))
    bpy.context.scene.frame_set(f0)
    for x in fx:
        kind = x if isinstance(x, str) else x["kind"]
        opt = {} if isinstance(x, str) else x
        P, _, _ = subj.point(shot["camera"].get("subject", "hero"), "base")
        if shot["camera"].get("subject") == "monster" and chars:
            P, _, _ = subj.point(next(iter(chars)), "base")
        c = (P.x, P.y, max(0, P.z))
        if kind == "rain":
            K.rain(c, (f0 - handles, f1 + handles), count=int(opt.get("count", 3000) * r.get("fx_scale", 1.0)),
                   area=opt.get("area", 40))
        elif kind in ("embers", "dust", "leaves", "ash", "sparks"):
            K.particles(kind, c, (f0 - handles, f1 + handles), count=int(opt.get("count", 250) * r.get("fx_scale", 1.0)),
                        area=opt.get("area", 30), height=opt.get("height", 12))
        elif kind == "lightning":
            K.lightning(opt.get("frames", [max(2, nfr // 3)]), opt.get("peak", 3.0))
        elif kind == "fogbank":
            K.fog_bank(resolve(opt.get("at", (0, 0, 2))), tuple(opt.get("size", (60, 60, 6))), opt.get("density", 0.03))
        elif kind == "blackout":
            K.blackout(opt.get("f", nfr // 2), keep=tuple(opt.get("keep", ["key", "rim", "fill", "monster", "torch", "phone"])))
        elif kind == "light_keys":
            for o in list(bpy.data.objects):
                if o.type == 'LIGHT' and any(n in o.name for n in opt["names"]):
                    base = o.data.energy
                    for fk, fac in opt["keys"]:
                        o.data.energy = base * fac
                        o.data.keyframe_insert("energy", frame=int(fk))
                    o.data.energy = base
                    K._constant_all(o.data)
            for m in bpy.data.materials:  # matching emissive panels follow their light
                if any(n in m.name for n in opt["names"]) and m.node_tree and m.node_tree.nodes.get("Emission"):
                    em = m.node_tree.nodes["Emission"].inputs[1]
                    base = em.default_value
                    for fk, fac in opt["keys"]:
                        em.default_value = base * fac
                        em.keyframe_insert("default_value", frame=int(fk))
                    em.default_value = base
                    K._constant_all(m.node_tree)
        elif kind == "power":
            K.city_power([(int(f), float(v)) for f, v in opt["keys"]])
        elif kind == "flood":
            K.flood([(int(f), float(z)) for f, z in opt["keys"]])
        elif kind == "steam":
            K.steam(resolve(opt["at"]), opt.get("f", 1), opt.get("dur", 40), opt.get("radius", 4))
        elif kind == "spray":
            K.spray(resolve(opt["at"]), (f0, f1 + handles), opt.get("count", 400), height=opt.get("height", 8))
        elif kind == "lights_on":
            K.lights_on(opt.get("f", nfr // 2), tuple(opt.get("names", [])), opt.get("energy"))
        elif kind == "flicker":
            for o in list(bpy.data.objects):
                if o.type == 'LIGHT' and any(n in o.name for n in opt.get("names", ["lamp", "tl", "sl", "flood"])):
                    K.flicker_light(o, opt.get("f0", 1), opt.get("f1", nfr), seed=hash(o.name) & 0xff)
    # hand-held light sources carried by characters (torch / phone)
    for cid, cdef in film.get("characters", {}).items():
        if cid in chars and shot.get("carry", {}).get(cid) in ("torch", "phone"):
            item = shot["carry"][cid]
            col = (1, 0.95, 0.8) if item == "torch" else (0.6, 0.8, 1.0)
            Lt = K.light('SPOT', (0, 0, 0), 900 if item == "torch" else 120, col, 0.05, spot=35 if item == "torch" else 90,
                         name=f"{item}_{cid}", volume=3.0)
            Lt.parent = chars[cid].sh["R"]
            Lt.location = (0, -0.2, -0.8)
            Lt.rotation_euler = (math.radians(90), 0, 0)
            K.box(f"{item}_{cid}_obj", (0, -0.1, -0.85), (0.12, 0.3, 0.12), K.emissive(col, 30), chars[cid].sh["R"])

    # selective shadows: only hero lights cast shadow maps (dominant CPU cost)
    keep = ("key", "rim", "flood", "eyeL", "torch", "moon", "doorlight", "sun") + tuple(r.get("shadow_keep", ()))
    if not r.get("all_shadows"):
        for o in bpy.data.objects:
            if o.type == 'LIGHT' and not any(k in o.name for k in keep):
                o.data.use_shadow = False
    cam, cam_keys = CAM.build_camera(shot["camera"], subj, f0, f1, impacts, step=r.get("cam_step", 2))
    auto_lights(film, shot, subj, cam_keys, film.get("look", "night_blue"))
    return chars, monster, cam


def screen_boxes(chars, monster, cam, frames):
    """Normalised (x0,y0,x1,y1) screen boxes per frame for faces + monster, y=0 bottom."""
    scn = bpy.context.scene
    out = {}
    for f in frames:
        scn.frame_set(f)
        boxes = []
        objs = []
        for c in chars.values():
            objs += [("face", o) for o in c.parts if o.name.endswith("_skull")]
        for o in bpy.data.objects:
            if o.type in ('FONT', 'CURVE', 'MESH') and o.users_collection and o.users_collection[0].name == "meters" \
                    and o.matrix_world.to_scale().length > 0.05:
                objs.append(("number", o))
        if monster:
            objs += [("monster", o) for o in monster.parts]
            objs += [("monster_head", o) for o in monster.parts
                     if any(k in o.name for k in ("_skull", "_eye", "_jaw", "_maw"))]
        groups = {}
        for tag, o in objs:
            key = (tag, o.name.split("_")[0])
            for corner in o.bound_box:
                w = o.matrix_world @ Vector(corner)
                p = world_to_camera_view(scn, cam, w)
                if p.z <= 0:
                    continue
                groups.setdefault(key, []).append((p.x, p.y))
        for (tag, nm), pts in groups.items():
            xs = [min(1, max(0, p[0])) for p in pts]
            ys = [min(1, max(0, p[1])) for p in pts]
            if max(xs) - min(xs) < 1e-3 or max(ys) - min(ys) < 1e-3:
                continue
            if max(p[0] for p in pts) < 0 or min(p[0] for p in pts) > 1 or max(p[1] for p in pts) < 0 or min(p[1] for p in pts) > 1:
                continue
            boxes.append({"tag": tag, "who": nm, "box": [min(xs), min(ys), max(xs), max(ys)]})
        out[f] = boxes
    return out


def setup_cycles(r, shot):
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    c = scn.cycles
    c.device = 'GPU' if r.get("gpu") else 'CPU'
    c.samples = int(shot.get("spp", r.get("cycles_spp", 16)))
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.05
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.max_bounces = 4
    c.diffuse_bounces = 2
    c.glossy_bounces = 2
    c.transmission_bounces = 2
    c.volume_bounces = 0
    c.transparent_max_bounces = 4
    c.volume_step_rate = 4.0
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    scn.render.use_motion_blur = r.get("motion_blur", True)


def add_lens_fx(r, shot):
    """Lens flare ghosts + star streaks on the brightest highlights (meteors, flashes, the flip)."""
    if not shot.get("flare"):
        return
    scn = bpy.context.scene
    ng = scn.compositing_node_group
    out = next(n for n in ng.nodes if n.bl_idname == "NodeGroupOutput")
    src = out.inputs[0].links[0].from_node
    cur = src.outputs["Image"]
    for typ, thr, st in (("Ghosts", 6.0, 0.25), ("Streaks", 5.0, 0.35)):
        g = ng.nodes.new("CompositorNodeGlare")
        g.inputs["Type"].default_value = typ
        g.inputs["Quality"].default_value = 'Low'
        g.inputs["Threshold"].default_value = thr
        g.inputs["Strength"].default_value = st * shot.get("flare", 1.0)
        ng.links.new(cur, g.inputs["Image"])
        cur = g.outputs["Image"]
    ng.links.new(cur, out.inputs[0])


def main():
    job = json.load(open(args()))
    r = job["render"]
    out_dir = r["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    t_build = time.time()
    v2 = job["film"].get("rig") == "v2"
    crowd = []
    if v2:
        import worker2
        chars, monster, cam, crowd = worker2.build(job)
    else:
        chars, monster, cam = build(job)
    if job['shot'].get('monster', True) is False:
        monster = None
    setup_render(r, job["film"].get("look", "night_blue"))
    shot = job["shot"]
    if v2:
        bpy.context.scene.view_settings.exposure += shot.get("exposure", 0.0)
        add_lens_fx(r, shot)
        if shot.get("engine") == "cycles" and r.get("allow_cycles", True):
            setup_cycles(r, shot)
    t_build = time.time() - t_build
    scn = bpy.context.scene
    nfr = job["shot"]["frames"]
    step = r.get("step", 1)
    if v2 and not r.get("still") and r.get("shot_step", True):
        step = max(step, shot.get("step", step)) if r.get("step", 1) > 1 else shot.get("step", step)
    # rigid bodies: step the sim once from the start so the cache is valid for any frame order
    if scn.rigidbody_world is not None:
        for f in range(scn.rigidbody_world.point_cache.frame_start, nfr + 2):
            scn.frame_set(f)
    animq = None
    if v2 and not r.get("still"):
        import charrig as CR
        animq = CR.check(list(chars.values()), 1, nfr)
    if r.get("still"):
        frames = [int(r.get("still_frame", max(1, int(nfr * 0.6))))]
    else:
        frames = list(range(1, nfr + 1, step))
    times = []
    budget = r.get("budget_s", 999)
    downgraded = []
    # 1) probe frame (also compiles shaders); adapt quality if over budget
    probe = frames[0]
    scn.frame_set(probe)
    scn.render.filepath = os.path.join(out_dir, f"f_{probe:04d}.png")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    times.append(time.time() - t)
    rest = frames[1:]
    if rest:
        # second probe after compile = true steady-state cost
        scn.frame_set(rest[0])
        scn.render.filepath = os.path.join(out_dir, f"f_{rest[0]:04d}.png")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t
        times.append(dt)
        rest = rest[1:]
        e = scn.eevee
        while dt > budget and len(downgraded) < 3:
            if e.taa_render_samples > 4:
                e.taa_render_samples = max(4, e.taa_render_samples // 2); downgraded.append(f"samples->{e.taa_render_samples}")
            elif e.volumetric_tile_size in ('4', '8'):
                e.volumetric_tile_size = '16'; e.volumetric_samples = 24; downgraded.append("vol 16/24")
            elif e.use_volumetric_shadows:
                e.use_volumetric_shadows = False; downgraded.append("vol shadows off")
            dt *= 0.8
            print(f"[worker] steady frame {times[-1]:.1f}s > budget {budget}s -> {downgraded[-1]}", flush=True)
    if rest:
        # 2) remaining frames in one animation render (engine stays warm between frames)
        stamps = []
        def _post(scene, *_):
            stamps.append(time.time())
        bpy.app.handlers.render_post.append(_post)
        scn.frame_start, scn.frame_end, scn.frame_step = rest[0], rest[-1], step
        scn.render.filepath = os.path.join(out_dir, "f_####")
        t = time.time()
        bpy.ops.render.render(animation=True)
        prev = t
        for st in stamps:
            times.append(st - prev); prev = st
    print("[worker] frame times", [round(x, 1) for x in times], flush=True)
    meta = {"shot": job["shot"]["id"], "frames": frames, "step": step, "build_s": round(t_build, 2),
            "render_s": round(sum(times), 2), "per_frame_s": round(sum(times) / max(1, len(times)), 2),
            "downgraded": downgraded, "res": [r["w"], r["h"]],
            "impacts": [[int(f), list(l)] for f, l in (monster.impacts if monster else [])],
            "roar": getattr(monster, "roar_frame", None) if monster else None}
    meta["safe_boxes"] = screen_boxes(chars, monster, cam, frames[::max(1, len(frames) // 12)] if not r.get("still") else frames)
    if v2:
        meta["animcheck"] = animq
        meta["engine"] = scn.render.engine
        steps = []
        for c in chars.values():
            sv = getattr(c, "solved", None)
            if not sv:
                continue
            for side in ("L", "R"):
                ft = sv["feet"][side]
                for f in range(2, nfr + 1):
                    if f in ft and f - 1 in ft and ft[f - 1]["swing"] and not ft[f]["swing"]:
                        P0, P1 = sv["P"].get(f - 3, sv["P"][f]), sv["P"][f]
                        steps.append([f, c.name, round((P1 - P0).length * 8, 2)])
        meta["steps"] = sorted(steps)
        meta["crowd_n"] = len(crowd)
    with open(os.path.join(out_dir, "meta.json"), "w") as fh:
        json.dump(meta, fh)
    print(f"[worker] {job['shot']['id']} build {t_build:.1f}s render {sum(times):.1f}s "
          f"({len(frames)} fr, {meta['per_frame_s']}s/fr)", flush=True)


if __name__ == "__main__":
    main()
