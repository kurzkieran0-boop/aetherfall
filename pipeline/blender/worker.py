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
    "toxic": dict(key=(0.9, 1.0, 0.85), rim=(0.3, 1.0, 0.6), fill=(0.2, 0.35, 0.5), exposure=0.35),
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
    g.inputs["Threshold"].default_value = 1.2
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
        K.light('SPOT', Pm + back * m.H * 0.9 + Vector((0, 0, m.H * 0.5)), 2.5e6 * m.u ** 2, L["rim"], size=4,
                spot=50, name="rim_monster", target=Pm - Vector((0, 0, m.H * 0.3)), volume=0.3)
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
        if kind == "police_car":
            K.police_car(loc, rz, (f0 - handles, f1 + handles), seed=pr.get("seed", int(loc[0] * 7 + loc[1])),
                         lights=pr.get("lights", True), name=pr.get("name", f"cop{len(bpy.data.objects)}"))
        elif kind == "sedan":
            K.sedan(loc, rz, tuple(pr.get("color", (0.5, 0.1, 0.1))), name=pr.get("name", "car"))
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
        if cid in chars and shot.get("carry", {}).get(cid):
            item = shot["carry"][cid]
            col = (1, 0.95, 0.8) if item == "torch" else (0.6, 0.8, 1.0)
            Lt = K.light('SPOT', (0, 0, 0), 900 if item == "torch" else 120, col, 0.05, spot=35 if item == "torch" else 90,
                         name=f"{item}_{cid}", volume=3.0)
            Lt.parent = chars[cid].sh["R"]
            Lt.location = (0, -0.2, -0.8)
            Lt.rotation_euler = (math.radians(90), 0, 0)
            K.box(f"{item}_{cid}_obj", (0, -0.1, -0.85), (0.12, 0.3, 0.12), K.emissive(col, 30), chars[cid].sh["R"])

    # selective shadows: only hero lights cast shadow maps (dominant CPU cost)
    keep = ("key", "rim", "flood", "eyeL", "torch", "moon", "doorlight") + tuple(r.get("shadow_keep", ()))
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


def main():
    job = json.load(open(args()))
    r = job["render"]
    out_dir = r["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    t_build = time.time()
    chars, monster, cam = build(job)
    if job['shot'].get('monster', True) is False:
        monster = None
    setup_render(r, job["film"].get("look", "night_blue"))
    t_build = time.time() - t_build
    scn = bpy.context.scene
    nfr = job["shot"]["frames"]
    step = r.get("step", 1)
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
    with open(os.path.join(out_dir, "meta.json"), "w") as fh:
        json.dump(meta, fh)
    print(f"[worker] {job['shot']['id']} build {t_build:.1f}s render {sum(times):.1f}s "
          f"({len(frames)} fr, {meta['per_frame_s']}s/fr)", flush=True)


if __name__ == "__main__":
    main()
