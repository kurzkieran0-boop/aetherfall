"""Shot builder for rig-v2 films (THE KINDNESS METER and later): armature characters,
kindness-meter billboards, procedural crowds, disaster VFX, Cycles hero shots.
Called from worker.py when film["rig"] == "v2".

Shot keys understood (on top of the classic camera/actions/fx):
  set_args   {sky, damage, door:[[t,deg]], plank_fixed:[t0,t1], spire_lean:[[t,deg]], sirens}
             (t = fraction of the shot, converted to frames here)
  actions    A(who, action, t0, t1, at|path|traj, facing|face_to, look_at, expr|exprs, ...)
  carry      {who: phone|pet_dragon|pet_fox|box|toy|beam}
  meters     {who: [[t, value, kind], ...]}  (kind: set|tick|flicker|fall_red|hide)
  zero       {pulse:1, glitch:t, glitch_frames:2, flip:[t_crack, t_burst, t_settle], inf:1, size}
  crowd      [{kind: mill|whisper|stare|watchers|flee|run_past|laugh|cheer, n, center, radius, ...}]
  vfx        [{kind: meteor|impact|sign|fire|streaks|flash|dust|embers|beam, t, at, ...}]
  lips       {who: [[frame, open, wide, round], ...]}
  engine     "cycles" for hero shots; lighting {key, rim, fill, practical} multipliers
"""
import math
import random

import bpy
from mathutils import Vector

import kit as K
import camera as CAM
import charrig as CR
import meter as MT
import kmset as KS

H = 8   # animation handles

PALETTES = [
    {"shirt": (0.75, 0.2, 0.18), "pants": (0.15, 0.17, 0.25)}, {"shirt": (0.2, 0.45, 0.8), "pants": (0.12, 0.12, 0.15)},
    {"shirt": (0.3, 0.65, 0.45), "pants": (0.25, 0.2, 0.18)}, {"shirt": (0.9, 0.7, 0.2), "pants": (0.2, 0.22, 0.3)},
    {"shirt": (0.6, 0.35, 0.75), "pants": (0.15, 0.15, 0.2)}, {"shirt": (0.92, 0.92, 0.95), "pants": (0.3, 0.32, 0.4)},
    {"shirt": (0.95, 0.5, 0.2), "pants": (0.1, 0.12, 0.2)}, {"shirt": (0.2, 0.7, 0.75), "pants": (0.35, 0.25, 0.2)},
    {"shirt": (0.85, 0.3, 0.55), "pants": (0.18, 0.18, 0.22)}, {"shirt": (0.45, 0.48, 0.52), "pants": (0.1, 0.1, 0.12)},
]
SKINS = [(0.95, 0.78, 0.3), (0.86, 0.66, 0.48), (0.62, 0.43, 0.3), (0.98, 0.85, 0.7), (0.45, 0.3, 0.2)]
HAIRS = [(0.08, 0.05, 0.03), (0.45, 0.28, 0.1), (0.85, 0.7, 0.35), (0.6, 0.2, 0.08), (0.8, 0.8, 0.82), (0.15, 0.1, 0.25)]
ACCS = ["hair", "cap", "ponytail", "spiky", "beanie", "hair", "none"]


def _fr(t, nfr):
    """float -> fraction of the shot (may exceed 1 for events after the cut); int -> frame."""
    if isinstance(t, float):
        return int(round(t * nfr)) if t >= 0 else int(round(nfr + t * nfr))
    return int(t)


def build(job):
    film, shot, r = job["film"], job["shot"], job["render"]
    K.reset_scene()
    nfr = shot["frames"]
    f0, f1 = 1, nfr
    fa, fb = f0 - H, f1 + H
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = f0, f1
    rng = random.Random(hash(shot["id"]) & 0xffff)
    # ------------------------------------------------------------------ set
    sa = dict(shot.get("set_args", {}))
    for k in ("door", "spire_lean"):
        if k in sa and isinstance(sa[k], list):
            sa[k] = [[_fr(t, nfr), v] for t, v in sa[k]]
    if "plank_fixed" in sa:
        sa["plank_fixed"] = [_fr(t, nfr) for t in sa["plank_fixed"]]
    marks = KS.set_meter_city(seed=film.get("seed", 7), frame_range=(fa, fb), **sa)
    marks = {k: tuple(v) for k, v in marks.items()}

    def P(p):
        if isinstance(p, str):
            return Vector(marks[p[5:] if p.startswith("mark:") else p])
        return Vector(p)

    needs_rb = any(v.get("kind") in ("impact", "sign") for v in shot.get("vfx", []))
    if needs_rb:
        KS.rigid_world(fa, fb)
    # ------------------------------------------------------------------ characters
    chars = {}
    cast = list(dict.fromkeys(shot.get("cast", []) + [a["who"] for a in shot.get("actions", [])]))
    for cid in cast:
        spec = film["characters"].get(cid)
        if spec is None:
            continue
        c = CR.BrickChar(cid, spec)
        chars[cid] = c
    # actions -> timelines
    acts = {}
    for a in shot.get("actions", []):
        acts.setdefault(a["who"], []).append(a)
    starts = {}
    for cid, c in chars.items():
        lst = acts.get(cid) or [{"action": "idle", "at": film["characters"][cid].get("mark", "plaza")}]
        first = lst[0]
        if first.get("path"):
            st = P(first["path"][0])
        elif first.get("at") is not None:
            st = P(first["at"])
        else:
            st = P(film["characters"][cid].get("mark", "plaza"))
        starts[cid] = st
    for cid, c in chars.items():
        lst = acts.get(cid) or [{"action": "idle", "at": film["characters"][cid].get("mark", "plaza")}]
        first = lst[0]
        facing = first.get("facing", 0.0)
        if first.get("face_to") is not None:
            tgt = _target(first["face_to"], marks, starts)
            d = tgt - starts[cid]
            facing = CR.yaw_to(d.x, d.y)
        c.place(tuple(starts[cid]), facing)
        for a in lst:
            kw = {k: v for k, v in a.items() if k not in ("who", "action", "f0", "f1", "t0", "t1")}
            a0 = _fr(a.get("t0", a.get("f0", 0.0)), nfr) if ("t0" in a or "f0" in a) else fa
            a1 = _fr(a.get("t1", a.get("f1", 1.0)), nfr) if ("t1" in a or "f1" in a) else fb
            if "t0" in a and a["t0"] == 0:
                a0 = fa
            if "t1" in a and a["t1"] == 1:
                a1 = fb
            for k in ("at",):
                if k in kw and kw[k] is not None:
                    kw[k] = tuple(P(kw[k]))
            if "path" in kw:
                kw["path"] = [tuple(P(p)) for p in kw["path"]]
            if kw.get("face_to") is not None:
                kw["face_to"] = tuple(_target(kw["face_to"], marks, starts))
            if kw.get("look_at") is not None:
                kw["look_at"] = tuple(_target(kw["look_at"], marks, starts, head=True))
            for k in ("stumble", "withdraw"):
                if k in kw and isinstance(kw[k], float):
                    kw[k] = int(kw[k] * nfr)
            if kw.get("exprs"):
                kw["exprs"] = [[(_fr(t, nfr) - a0) if isinstance(t, float) else t, e] for t, e in kw["exprs"]]
            c.add(a["action"], a0, a1, **kw)
        c.lips = [tuple(x) for x in shot.get("lips", {}).get(cid, [])]
    # ------------------------------------------------------------------ crowds
    crowd_chars = []
    for ci, cw in enumerate(shot.get("crowd", [])):
        crowd_chars += _crowd(cw, ci, nfr, fa, fb, marks, starts, film)
    for c in list(chars.values()) + [x[0] for x in crowd_chars]:
        c.bake(fa, fb, seed=hash(shot["id"]) & 0xff)
    # ------------------------------------------------------------------ props carried
    for cid, item in shot.get("carry", {}).items():
        if cid in chars:
            _carry(chars[cid], item, fa, fb)
    for c, cw, i, _vals in crowd_chars:
        if cw.get("carry"):
            if cw["carry"] == "phone" or (cw["carry"] == "pets" and i % 2 == 0):
                _carry(c, "phone" if cw["carry"] == "phone" else ("pet_dragon" if i % 4 == 0 else "pet_fox"), fa, fb)
    # ------------------------------------------------------------------ props
    for pr in shot.get("props", []):
        _prop(pr, P, nfr, fa, fb)
    # ------------------------------------------------------------------ VFX
    impacts = []
    for v in shot.get("vfx", []):
        kind = v["kind"]
        t = _fr(v.get("t", 0.5), nfr)
        if kind == "meteor":
            KS.meteor(f"met{t}", tuple(P(v["at"])), t, tuple(v.get("from", (0.45, 0.25, 1.0))), v.get("dist", 260),
                      v.get("size", 3.0), v.get("travel", 36), seed=t)
        elif kind == "impact":
            KS.impact(f"imp{t}", tuple(P(v["at"])), t, v.get("power", 1.0), seed=t, debris=v.get("debris", True),
                      fire=v.get("fire", True), f_range=(fa, fb), crater_=v.get("crater", True))
            impacts.append((t, tuple(P(v["at"])), v.get("shake", 1.0)))
        elif kind == "shake":
            impacts.append((t, tuple(P(v.get("at", "plaza"))), v.get("shake", 0.6)))
        elif kind == "sign":
            KS.falling_sign(f"sign{t}", tuple(P(v["at"])), tuple(v.get("size", (4, 0.4, 1.6))), t,
                            tuple(v.get("color", (0.35, 0.8, 1.0))), v.get("text", "OPEN"), math.radians(v.get("rot", 0)))
        elif kind == "fire":
            KS.fire_volume(f"fire{len(impacts)}{t}", tuple(P(v["at"])), tuple(v.get("size", (3, 3, 4))),
                           v.get("intensity", 1.0), (fa, fb), seed=t)
        elif kind == "embers":
            p = P(v.get("at", "plaza"))
            K.particles("embers", tuple(p), (fa, fb), count=int(v.get("count", 300) * r.get("fx_scale", 1.0)),
                        area=v.get("area", 30), height=v.get("height", 12), name=f"emb{t}")
        elif kind == "dust":
            p = P(v.get("at", "plaza"))
            K.particles("dust", tuple(p), (fa, fb), count=int(v.get("count", 220) * r.get("fx_scale", 1.0)),
                        area=v.get("area", 16), height=v.get("height", 6), name=f"dst{t}")
        elif kind == "ash":
            p = P(v.get("at", "plaza"))
            K.particles("ash", tuple(p), (fa, fb), count=int(v.get("count", 300) * r.get("fx_scale", 1.0)),
                        area=v.get("area", 30), height=v.get("height", 14), name=f"ash{t}")
        elif kind == "streaks":
            KS.sky_streaks((fa, fb), n=v.get("n", 8), seed=t)
        elif kind == "dustcloud":
            K.dust_cloud(t, tuple(P(v["at"])), radius=v.get("radius", 8), name=f"dc{t}", duration=v.get("dur", 60),
                         density=v.get("density", 0.3))
        elif kind == "flash":
            L = K.light('SUN', (0, 0, 50), 0, tuple(v.get("color", (1, 0.7, 0.5))), name=f"flash{t}")
            L.rotation_euler = (0.6, 0.1, 0.8)
            L.data.use_shadow = False
            L.data.keyframe_insert("energy", frame=t - 1)
            L.data.energy = v.get("energy", 25)
            L.data.keyframe_insert("energy", frame=t)
            L.data.energy = 0
            L.data.keyframe_insert("energy", frame=t + v.get("len", 4))
        elif kind == "sparks":
            MT.spark_burst(None, t, v.get("count", 60), tuple(v.get("color", (1, 0.7, 0.3))), name=f"sp{t}",
                           speed=v.get("speed", 6), seed=t, life=26, gravity=9, size=0.05)
            for o in bpy.data.objects:
                if o.name.startswith(f"sp{t}") and o.parent is None:
                    o.location = (0, 0, 0)
                    for fc in K._fcurves(o):
                        if fc.data_path == "location":
                            for kp in fc.keyframe_points:
                                kp.co.y += P(v["at"])[fc.array_index]
                            fc.update()
        elif kind == "beam":
            _beam(v, P, nfr, fa, fb)
    # ------------------------------------------------------------------ camera
    allc = dict(chars)
    subj = CAM.Subjects(allc, None, marks)
    subj.meter_room = not shot.get("no_meter_room")
    cs = dict(shot["camera"])
    if isinstance(cs.get("subject"), list):
        cs["subject"] = list(P(cs["subject"]))
    if isinstance(cs.get("subject2"), list):
        cs["subject2"] = list(P(cs["subject2"]))
    if cs.get("pos") is not None and isinstance(cs["pos"], (str, list)):
        cs["pos"] = list(P(cs["pos"]))
    if cs.get("pos2") is not None and isinstance(cs["pos2"], (str, list)):
        cs["pos2"] = list(P(cs["pos2"]))
    cam, cam_keys = CAM.build_camera(cs, subj, f0, f1, impacts, step=1)
    # ------------------------------------------------------------------ meters
    meters = []
    zero_spec = shot.get("zero", {})
    for cid, c in chars.items():
        ms = film["characters"][cid].get("meter")
        if ms is None or shot.get("no_meters"):
            continue
        if ms == "zero":
            if zero_spec.get("off"):
                continue
            hz = MT.HeroZero(cid, c.meter_anchor, (fa, fb), size=zero_spec.get("size", 0.78))
            cr = hz.holder.constraints.new('COPY_ROTATION')
            cr.target = cam
            fl = zero_spec.get("flip")
            if zero_spec.get("inf"):
                hz.zero.scale = (0.0001,) * 3
                hz.zero.keyframe_insert("scale", frame=fa)
                hz.inf.scale = (1, 1, 1)
                hz.inf.keyframe_insert("scale", frame=fa)
                gem = hz.gold.node_tree.nodes["Emission"].inputs[1]
                for f in range(fa, fb + 1, 6):
                    gem.default_value = 7 + 2 * math.sin(f / 8.0)
                    gem.keyframe_insert("default_value", frame=f)
                hz.lamp.data.color = MT.COL["gold"]
                hz.lamp.data.energy = 900
            else:
                hz.pulse(fa, (_fr(fl[0], nfr) - 1) if fl else fb, period=zero_spec.get("period", 20))
                if zero_spec.get("glitch") is not None:
                    hz.glitch_inf(_fr(zero_spec["glitch"], nfr), zero_spec.get("glitch_frames", 2))
                if fl:
                    hz.flip(_fr(fl[0], nfr), _fr(fl[1], nfr), _fr(fl[2], nfr), sparks=zero_spec.get("sparks", 140),
                            glow=zero_spec.get("glow", 1.0))
            meters.append(hz)
        else:
            base = ms["value"]
            for b_, v_ in sorted((int(k), v) for k, v in ms.get("after", {}).items()):
                if shot.get("beat", 0) >= b_:
                    base = v_
            ev = [[fa, base, "set"]]
            for t, val, kind in shot.get("meters", {}).get(cid, []):
                ev.append([_fr(t, nfr) if kind != "flicker" else _fr(t, nfr), val if kind != "flicker" else _fr(val, nfr), kind])
            m = MT.Meter(cid, c.meter_anchor, ev, size=ms.get("size", 0.36) * c.s ** 0.5, color=ms.get("color", "white"),
                         strength=ms.get("strength", 4.5 if ms.get("color") == "gold" else 5.5), f_range=(fa, fb), seed=len(cid))
            m.build(cam)
            meters.append(m)
    for c, cw, i, val in crowd_chars:
        if cw.get("meters", True) and val is not None:
            ev = [[fa, val, "set"]]
            if cw.get("flicker"):
                fs = _fr(cw["flicker"][0], nfr) + (i * 3) % 9
                ev.append([fs, _fr(cw["flicker"][1], nfr), "flicker"])
            if cw.get("fall_red") and val >= 5000:
                ft = _fr(cw["fall_red"], nfr) + (i * 2) % 6
                for k, vv in enumerate((int(val * 0.6), int(val * 0.2), int(val * 0.03), 12 + i % 40)):
                    ev.append([ft + k * 4, vv, "fall_red"])
            m = MT.Meter(c.name, c.meter_anchor, ev, size=0.36 * c.s ** 0.5, color="gold" if val >= 5000 else "white",
                         strength=4.5 if val >= 5000 else 5.0, f_range=(fa, fb), seed=i)
            m.build(cam)
    lights_rig(film, shot, subj, cam_keys, chars)
    return chars, None, cam, [x[0] for x in crowd_chars]


def _target(t, marks, starts, head=False):
    if isinstance(t, str):
        if t in starts:
            return starts[t] + Vector((0, 0, 2.1 if head else 0))
        return Vector(marks[t[5:] if t.startswith("mark:") else t])
    return Vector(t)


def _crowd(cw, ci, nfr, fa, fb, marks, starts, film):
    """Procedural crowd: varied bodies/heights/colours, individual timing, never lockstep."""
    rng = random.Random(cw.get("seed", 7) * 31 + ci)
    kind = cw.get("kind", "mill")
    center = Vector(marks[cw["center"]] if isinstance(cw["center"], str) else cw["center"])
    n = cw.get("n", 10)
    out = []
    face_to = cw.get("face_to")
    if isinstance(face_to, str):
        face_to = starts.get(face_to, Vector(marks.get(face_to, (0, 0, 0))))
    look = cw.get("look_at")
    if isinstance(look, str):
        look = (starts[look] if look in starts else Vector(marks.get(look, (0, 0, 0)))) + Vector((0, 0, 2.1))
    sims = None
    if kind == "flee":
        thr = cw.get("threat", "plaza")
        thr = Vector(marks[thr] if isinstance(thr, str) else thr)
        sims = KS.crowd_flee(n, center, cw.get("radius", 10), thr, _fr(cw.get("t0", 0.0), nfr) if cw.get("t0") else fa,
                             fb, seed=cw.get("seed", 1), speed=tuple(cw.get("speed", (3.8, 6.4))), avoid=cw.get("avoid", ()),
                             exits=cw.get("exits"), delay=tuple(cw.get("delay", (2, 16))))
    for i in range(n):
        pal = dict(rng.choice(PALETTES))
        pal["hair"] = rng.choice(HAIRS)
        pal["hat"] = rng.choice(PALETTES)["shirt"]
        vip = rng.random() < cw.get("vip_frac", 0.2)
        if vip:
            pal["shirt"] = rng.choice(((0.95, 0.75, 0.25), (0.95, 0.95, 0.97), (0.1, 0.1, 0.12)))
            pal["stripe"] = (1.0, 0.72, 0.2)
        spec = {"palette": pal, "accessory": rng.choice(ACCS) if not vip else rng.choice(("crown", "shades", "hair")),
                "scale": rng.uniform(0.86, 1.08) * (0.78 if rng.random() < 0.12 else 1.0), "skin": rng.choice(SKINS)}
        c = CR.BrickChar(f"x{ci}_{i}", spec)
        val = rng.randint(5200, 9700) if vip else rng.randint(1200, 4900)
        if kind in ("mill", "whisper", "stare", "watchers", "laugh", "cheer", "stand"):
            a = rng.uniform(0, math.tau)
            rr = rng.uniform(cw.get("inner", 1.5), cw.get("radius", 8))
            p = center + Vector((math.cos(a) * rr * cw.get("sx", 1.0), math.sin(a) * rr * cw.get("sy", 1.0), 0))
            p.z = center.z
            if face_to is not None:
                d = Vector(face_to) - p
                fc = CR.yaw_to(d.x, d.y) + rng.uniform(-14, 14)
            else:
                fc = rng.uniform(0, 360)
            c.place(tuple(p), fc)
            if kind == "mill":
                r = rng.random()
                if r < 0.4:
                    d = Vector((math.cos(rng.uniform(0, 6.28)), math.sin(rng.uniform(0, 6.28)), 0)) * rng.uniform(2.5, 5)
                    c.add("walk", fa, fb, path=[tuple(p), tuple(p + d)], keep_going=True, start_moving=True,
                          expr=rng.choice(("neutral", "happy", "smug")))
                elif r < 0.7:
                    c.add("talk", fa, fb, expr=rng.choice(("happy", "neutral", "smug")), facing=fc)
                    c.lips = [(f, 0.25 + 0.25 * math.sin(f * 0.9 + i), 0.3, 0.2) for f in range(fa, fb) if (f // 9 + i) % 3]
                else:
                    c.add(rng.choice(("idle", "cross_arms", "idle")), fa, fb, expr=rng.choice(("neutral", "smug", "calm")), facing=fc)
            elif kind == "whisper":
                c.add(rng.choice(("whisper", "cross_arms", "whisper", "stare")), fa + rng.randint(0, 8), fb,
                      side=rng.choice((-1, 1)), expr=rng.choice(("disgust", "wary", "smug")), look_at=tuple(look) if look else None,
                      facing=fc)
            elif kind == "stare":
                d0 = _fr(cw.get("t0", 0.0), nfr) + rng.randint(0, 10)
                c.add("idle", fa, d0, expr="neutral", facing=fc)
                c.add(rng.choice(("hands_mouth", "stare", "gasp", "stare")), d0, fb, expr=rng.choice(("awe", "shock", "hurt")),
                      look_at=tuple(look) if look else None, facing=fc)
            elif kind == "watchers":
                c.add("pose", fa + rng.randint(0, 10), fb, kind="selfie", expr=rng.choice(("happy", "smug")),
                      facing=fc, look_at=tuple(look) if look else None)
                cw = dict(cw, carry="phone")
            elif kind in ("laugh", "cheer"):
                c.add("laugh" if kind == "laugh" else "cheer", fa + rng.randint(0, 6), fb, facing=fc)
            else:
                c.add("idle", fa, fb, facing=fc, expr=rng.choice(("neutral", "wary")))
        elif kind == "flee":
            ag = sims[i]
            tr = [[f, x, y, center.z] for f, x, y in ag["traj"]]
            st = tuple(Vector((tr[0][1], tr[0][2], center.z)))
            dd = Vector((tr[-1][1] - tr[0][1], tr[-1][2] - tr[0][2], 0))
            fc = CR.yaw_to(dd.x, dd.y) if dd.length > 0.1 else ag["yaw"]
            c.place(st, ag["yaw"])
            dl = max(fa + 1, ag["delay"])
            c.add(rng.choice(("gasp", "look_around", "flinch")), fa, dl, expr="fear", face_to=tuple(Vector(st) - (dd.normalized() if dd.length else Vector((1, 0, 0)))))
            c.add("panic_sprint" if rng.random() < 0.7 else "run", dl, fb, traj=tr, stumble=(rng.randint(6, 30) if ag["stumble"] else None),
                  carry_pet=(cw.get("carry") == "pets" and i % 2 == 0))
        elif kind == "run_past":
            # sprint along a direction through `center`, staggered lanes
            dirv = Vector(cw.get("dir", (1, 0, 0))).normalized()
            side = Vector((-dirv.y, dirv.x, 0))
            lane = (i - n / 2) * cw.get("spacing", 1.5) + rng.uniform(-0.4, 0.4)
            back = rng.uniform(cw.get("spread", (4, 22))[0], cw.get("spread", (4, 22))[1])
            spd = rng.uniform(4.2, 6.4)
            p0 = center + side * lane - dirv * back
            dur = (fb - fa) / 24.0
            p1 = p0 + dirv * spd * dur
            p0.z = p1.z = center.z
            c.place(tuple(p0), CR.yaw_to(dirv.x, dirv.y))
            ac = "panic_sprint" if rng.random() < 0.6 else "run"
            c.add(ac, fa, fb, path=[tuple(p0), tuple(p1)], start_moving=True, keep_going=True,
                  stumble=(rng.randint(6, 40) if rng.random() < 0.15 else None),
                  carry_pet=(cw.get("carry") == "pets" and i % 3 == 0))
        out.append((c, cw, i, val))
    return out


def _carry(c, item, fa, fb):
    """Props held by a character, placed in rest-pose space then bound to a bone."""
    n = f"{c.name}_{item}"
    if item == "phone":
        ph = K.box(n, (0, 0, 0), (0.14, 0.03, 0.26), K.plastic((0.04, 0.04, 0.05), 0.2), collection="chars")
        K.box(n + "_scr", (0, 0.02, 0), (0.12, 0.01, 0.22), K.emissive((0.55, 0.75, 1.0), 8, name="phone_scr"), ph,
              collection="chars")
        c.attach(ph, "hand_R", (-0.5, -0.16, 0.86), (0, 0, 0))
        L = K.light('POINT', (0, 0, 0), 12, (0.55, 0.75, 1.0), 0.05, name=n + "_glow", volume=0.0)
        L.parent = ph
        L.location = (0, 0.15, 0)
        L.data.use_shadow = False
    elif item in ("pet_dragon", "pet_fox"):
        pet = KS.rare_pet(n, "dragon" if item == "pet_dragon" else "fox",
                          (0.55, 0.25, 1.0) if item == "pet_dragon" else (0.2, 0.85, 1.0))
        for ch in list(pet.children):
            pass
        c.attach(pet, "chest", (0, -0.5, 1.28), (0, 0, 0))
    elif item == "box":
        b = K.box(n, (0, 0, 0), (0.75, 0.5, 0.5), K.plastic((0.62, 0.45, 0.28), 0.8, coat=0), collection="chars", bevel=0.02)
        K.box(n + "_tape", (0, 0, 0.256), (0.12, 0.5, 0.01), K.plastic((0.8, 0.7, 0.4), 0.4), b, collection="chars")
        c.attach(b, "chest", (0, -0.55, 1.22), (0, 0, 0))
    elif item == "toy":
        t = K.box(n, (0, 0, 0), (0.22, 0.07, 0.07), K.emissive((0.4, 1.0, 0.6), 6, name="toy_glow"), collection="chars",
                  bevel=0.02)
        for s in (-1, 1):
            K.sphere(n + f"_k{s}", (s * 0.11, 0, 0), 0.06, K.emissive((0.4, 1.0, 0.6), 6, name="toy_glow"), t, collection="chars")
        c.attach(t, "hand_R", (-0.5, -0.12, 0.86), (0, 0, 0))


def _prop(pr, P, nfr, fa, fb):
    kind = pr["kind"]
    loc = tuple(P(pr.get("at", (0, 0, 0))))
    if kind == "box":
        o = K.box(pr.get("name", "pbox"), loc, tuple(pr.get("size", (0.75, 0.5, 0.55))),
                  K.plastic(tuple(pr.get("color", (0.62, 0.45, 0.28))), 0.8, coat=0), bevel=0.02,
                  rot=(0, 0, math.radians(pr.get("rot", 0))))
        if pr.get("fall"):
            t = _fr(pr["fall"][0], nfr)
            o.keyframe_insert("location", frame=t)
            o.keyframe_insert("rotation_euler", frame=t)
            o.location = tuple(P(pr["fall"][1]))
            o.rotation_euler = (0.3, 0.6, 1.0)
            o.keyframe_insert("location", frame=t + 8)
            o.keyframe_insert("rotation_euler", frame=t + 8)
    elif kind == "toy":
        o = K.box("toy_bone", loc, (0.22, 0.07, 0.07), K.emissive((0.4, 1.0, 0.6), 6, name="toy_glow"), bevel=0.02,
                  rot=(0, 0, math.radians(pr.get("rot", 30))))
        for s in (-1, 1):
            K.sphere(f"toy_k{s}", (s * 0.11, 0, 0), 0.06, K.emissive((0.4, 1.0, 0.6), 6, name="toy_glow"), o)
        if pr.get("hide_at") is not None:
            t = _fr(pr["hide_at"], nfr)
            o.keyframe_insert("scale", frame=t - 1)
            o.scale = (0.0001,) * 3
            o.keyframe_insert("scale", frame=t)
        if pr.get("show_at") is not None:
            t = _fr(pr["show_at"], nfr)
            o.scale = (0.0001,) * 3
            o.keyframe_insert("scale", frame=t - 1)
            o.scale = (1, 1, 1)
            o.keyframe_insert("scale", frame=t)
    elif kind == "poster":
        o = K.box("poster", loc, (0.05, 0.9, 1.2), K.emissive((0.95, 0.92, 0.8), 2.5, name="poster_m"),
                  rot=(0, 0, math.radians(pr.get("rot", 0))))
        m = MT._glow_mat("poster_t", (0.15, 0.1, 0.1), 0.2)
        t = MT.text_obj("poster_txt", "LOST\nPET", 0.26, m)
        t.location = (loc[0] + pr.get("dx", 0.04), loc[1], loc[2] + 0.2)
        t.rotation_euler = (math.radians(90), 0, math.radians(pr.get("rot", 0) + 90))
    elif kind == "neon":
        m = MT._glow_mat("neonprop", tuple(pr.get("color", (1, 0.3, 0.3))), pr.get("strength", 12))
        t = MT.text_obj(pr.get("name", "neonp"), pr.get("text", "OPEN"), pr.get("size", 0.5), m)
        t.location = loc
        t.rotation_euler = (math.radians(90), 0, math.radians(pr.get("rot", 0)))
    elif kind == "light":
        K.light(pr.get("type", 'POINT'), loc, pr.get("energy", 1000), tuple(pr.get("color", (1, 1, 1))),
                pr.get("size", 0.5), spot=pr.get("spot", 45), target=tuple(P(pr["aim"])) if "aim" in pr else None,
                name=pr.get("name", "plight"), volume=pr.get("volume", 1.0))
    elif kind == "police_car":
        K.police_car(loc, math.radians(pr.get("rot", 0)), (fa, fb), seed=int(loc[0] * 7 + loc[1]), name=pr.get("name", "copx"))
    elif kind == "ambulance":
        KS.ambulance(loc, math.radians(pr.get("rot", 0)), (fa, fb), name=pr.get("name", "ambx"))


def _beam(v, P, nfr, fa, fb):
    """The concrete beam pinning the kid; keyed by the hero's lift (with a slip)."""
    loc = P(v["at"])
    piv = K.empty("beam_pivot", tuple(loc + Vector((1.7, 0.4, 0.15))), collection="set")
    piv.rotation_euler = (0, 0, math.radians(v.get("rot", 15)))
    b = K.box("beam", (-1.6, 0, 0.32), (3.6, 0.55, 0.55), K.pbr("concrete", 0.4, tint=(0.5, 0.5, 0.52), name="beam_m"),
              piv, bevel=0.03, collection="set")
    K.box("beam_rebar", (-1.6, 0.0, 0.62), (3.4, 0.06, 0.06), K.plastic((0.35, 0.2, 0.12), 0.7), piv, collection="set")
    for t, ang in v.get("keys", [[0.0, 0]]):
        piv.rotation_euler = (0, math.radians(ang), math.radians(v.get("rot", 15)))
        piv.keyframe_insert("rotation_euler", frame=_fr(t, nfr))


def lights_rig(film, shot, subj, cam_keys, chars):
    """Motivated key/rim/fill per act colour script + a practical glow on faces."""
    act = shot.get("act", "cold")
    L = {"cold": dict(key=(0.75, 0.82, 1.0), rim=(0.4, 0.62, 1.0), fill=(0.18, 0.25, 0.55), k=110, r=2600, f=26),
         "warm": dict(key=(1.0, 0.78, 0.55), rim=(0.45, 0.62, 1.0), fill=(0.25, 0.3, 0.6), k=150, r=2400, f=30),
         "red": dict(key=(1.0, 0.45, 0.22), rim=(1.0, 0.3, 0.12), fill=(0.25, 0.18, 0.35), k=170, r=3400, f=22),
         "gold": dict(key=(1.0, 0.78, 0.45), rim=(1.0, 0.7, 0.35), fill=(0.35, 0.3, 0.45), k=170, r=3000, f=34)}[act]
    lc = shot.get("lighting", {})
    s1 = shot["camera"].get("subject", "hero")
    if not isinstance(s1, str) or s1 not in subj.chars:
        s1 = shot.get("light_subject") or ("hero" if "hero" in subj.chars else next(iter(subj.chars), None))
    if not s1:
        return
    fm = cam_keys[len(cam_keys) // 2][0]
    bpy.context.scene.frame_set(fm)
    Pp, yaw, Hh = subj.point(s1, "chest")
    cam = Vector(cam_keys[len(cam_keys) // 2][1])
    v = cam - Pp
    v.z = 0
    v = v.normalized() if v.length > 0.01 else Vector((0, -1, 0))
    side = v.cross(Vector((0, 0, 1)))
    ks = lc.get("key", 1.0)
    K.light('AREA', Pp + (v * 0.6 + side * 0.8).normalized() * 3.5 + Vector((0, 0, 1.8)), L["k"] * ks, L["key"], size=1.6,
            name="key", target=Pp + Vector((0, 0, 0.6)), volume=0.15)
    K.light('SPOT', Pp - v * 4 - side * 1.8 + Vector((0, 0, 2.6)), L["r"] * lc.get("rim", 1.0), L["rim"], size=0.25, spot=40,
            name="rim", target=Pp + Vector((0, 0, 0.5)), volume=0.5)
    K.light('SPOT', Pp - v * 4 + side * 2.2 + Vector((0, 0, 2.2)), L["r"] * 0.5 * lc.get("rim", 1.0), L["rim"], size=0.25,
            spot=40, name="rim2", target=Pp + Vector((0, 0, 0.6)), volume=0.3)
    K.light('AREA', Pp + v * 5 - side * 2 + Vector((0, 0, 0.6)), L["f"] * lc.get("fill", 1.0), L["fill"], size=4,
            name="fill", target=Pp, volume=0.0)
    for k, lt in enumerate(shot.get("extra_lights", [])):
        K.light(lt.get("type", 'POINT'), tuple(Vector(lt["at"])), lt.get("energy", 500), tuple(lt.get("color", (1, 1, 1))),
                lt.get("size", 0.5), name=lt.get("name", f"xl{k}"), target=tuple(lt["aim"]) if lt.get("aim") else None,
                volume=lt.get("volume", 0.5))
