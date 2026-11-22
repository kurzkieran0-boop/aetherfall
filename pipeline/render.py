"""Parallel, hash-cached shot renderer.

* Each shot -> job.json -> one Blender process (blender -b -P worker.py, or the
  pip `bpy` module when no Blender binary is installed).
* Cache key = sha1(shot spec + film context + render settings + kit source). A
  finished shot (meta.json present) is never rendered again, so editing one shot
  only re-renders that shot.
* GPU detection picks a profile: GPU -> native 1080x1920, every frame (24 fps),
  16 samples. CPU-only -> 432x768 rendered on twos and upscaled in compose.
* Prints per-shot time; the worker auto-lowers settings for slow shots.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "shots")
WORKER = os.path.join(ROOT, "pipeline", "blender", "worker.py")


def blender_cmd():
    exe = shutil.which("blender") or os.environ.get("BLENDER")
    if not exe and os.name == "nt":
        import glob
        c = sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"))
        exe = c[-1] if c else None
    if exe:
        return [exe, "-b", "--factory-startup", "-P", WORKER, "--"]
    return [sys.executable, WORKER]  # pip bpy module


def detect_gpu():
    """Return 'OPTIX'/'CUDA'/'HIP'/'METAL'/'ONEAPI' or None."""
    if shutil.which("nvidia-smi"):
        try:
            subprocess.run(["nvidia-smi", "-L"], check=True, capture_output=True, timeout=10)
            return "OPTIX"
        except Exception:
            pass
    if shutil.which("rocm-smi") or shutil.which("hipInfo"):
        return "HIP"
    if sys.platform == "darwin":
        return "METAL"
    if os.name == "nt":
        try:
            out = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"], capture_output=True,
                                 text=True, timeout=10).stdout.lower()
            if "nvidia" in out:
                return "OPTIX"
            if "radeon" in out or "amd" in out:
                return "HIP"
            if "arc" in out:
                return "ONEAPI"
        except Exception:
            pass
    return None


def profile(kind, gpu=None):
    gpu = gpu if gpu is not None else detect_gpu()
    if kind == "still":
        return dict(w=540, h=960, step=1, samples=8, still=True, vol_tile='8', vol_samples=32, budget_s=999)
    if kind == "preview":
        return dict(w=270, h=480, step=4, samples=2, vol_tile='16', vol_samples=16, budget_s=3.0, fx_scale=0.5,
                    motion_blur=False)
    if gpu:  # native finals
        return dict(w=1080, h=1920, step=1, samples=16, vol_tile='8', vol_samples=48, budget_s=4.0, gpu=gpu)
    return dict(w=432, h=768, step=2, samples=4, vol_tile='8', vol_samples=32, budget_s=8.0, fx_scale=0.8)


def _kit_hash():
    h = hashlib.sha1()
    for f in ("kit.py", "camera.py", "worker.py"):
        h.update(open(os.path.join(ROOT, "pipeline", "blender", f), "rb").read())
    return h.hexdigest()[:10]


def shot_key(film_ctx, shot, rset):
    blob = json.dumps({"f": film_ctx, "s": shot, "r": rset, "k": _kit_hash()}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def film_context(film):
    keys = ("set", "seed", "look", "characters", "monster", "fx")
    return {k: film.get(k) for k in keys}


def render_shots(film, shots, kind="final", jobs=None, log=print, only=None):
    """Render every shot (or only ids in `only`). Returns {shot_id: dir}."""
    rset = profile(kind)
    ctx = film_context(film)
    gpu = rset.get("gpu")
    if jobs is None:
        ncpu = os.cpu_count() or 4
        jobs = 2 if gpu else max(1, min(3, ncpu // 3))
    todo, result = [], {}
    for s in shots:
        if only and s["id"] not in only:
            continue
        key = shot_key(ctx, s, rset)
        d = os.path.join(CACHE, f"{kind}_{key}")
        result[s["id"]] = d
        if os.path.exists(os.path.join(d, "meta.json")):
            continue
        todo.append((s, d))
    log(f"[render:{kind}] {len(result)} shots, {len(result) - len(todo)} cached, {len(todo)} to render "
        f"({rset['w']}x{rset['h']}, step {rset['step']}, {jobs} parallel, gpu={gpu})")
    t_all = time.time()

    def run(item):
        s, d = item
        tmp = d + ".tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        r = dict(rset, out_dir=tmp)
        job = {"film": ctx, "shot": s, "render": r}
        jp = os.path.join(tmp, "job.json")
        json.dump(job, open(jp, "w"))
        env = dict(os.environ)
        if not gpu:
            env["LP_NUM_THREADS"] = str(max(1, (os.cpu_count() or 4) // jobs))
        t = time.time()
        p = subprocess.run(blender_cmd() + [jp], capture_output=True, text=True, env=env)
        dt = time.time() - t
        if p.returncode != 0 or not os.path.exists(os.path.join(tmp, "meta.json")):
            open(os.path.join(tmp, "error.log"), "w").write(p.stdout[-6000:] + "\n" + p.stderr[-6000:])
            log(f"  ✗ {s['id']} FAILED after {dt:.1f}s (see {tmp}/error.log)")
            return s["id"], None
        meta = json.load(open(os.path.join(tmp, "meta.json")))
        meta["wall_s"] = round(dt, 1)
        json.dump(meta, open(os.path.join(tmp, "meta.json"), "w"))
        shutil.rmtree(d, ignore_errors=True)
        os.replace(tmp, d)
        dg = f"  auto-lowered: {', '.join(meta['downgraded'])}" if meta.get("downgraded") else ""
        log(f"  ✓ {s['id']:<10} {dt:6.1f}s  ({len(meta['frames'])} fr @ {meta['per_frame_s']}s){dg}")
        return s["id"], d

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for sid, d in ex.map(run, todo):
            if d is None:
                result.pop(sid, None)
    log(f"[render:{kind}] done in {time.time() - t_all:.1f}s")
    return result


def timings(dirs):
    out = {}
    for sid, d in dirs.items():
        try:
            m = json.load(open(os.path.join(d, "meta.json")))
            out[sid] = {"wall_s": m.get("wall_s"), "per_frame_s": m.get("per_frame_s"), "frames": len(m["frames"]),
                        "downgraded": m.get("downgraded", [])}
        except Exception:
            pass
    return out
