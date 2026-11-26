"""videos/progress.json: per-stage status so a crash resumes instead of restarting.

Each video writes only videos/<slug>/status.json; progress.json is the aggregate, rebuilt under a lock.
"""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import VIDEOS, SLUGS_ALL, file_lock, preview

PROG = VIDEOS / "progress.json"


def _read(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def _write(p, data):
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    os.replace(tmp, p)


def stage_name(stage):
    return f"preview_{stage}" if preview() and stage in ("rendered", "assembled", "verified") else stage


def video_status(slug):
    return _read(VIDEOS / slug / "status.json", {})


def mark(slug, stage, ok=True, **info):
    p = VIDEOS / slug / "status.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(p):
        st = _read(p, {})
        st[stage_name(stage)] = dict(ok=ok, at=time.strftime("%Y-%m-%d %H:%M:%S"), **info)
        _write(p, st)
    sync()


def done(slug, stage):
    return video_status(slug).get(stage_name(stage), {}).get("ok", False)


def sync(**top):
    with file_lock(PROG):
        pr = _read(PROG, {})
        pr.update(top)
        pr["videos"] = {s: video_status(s) for s in SLUGS_ALL}
        pr["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _write(PROG, pr)


def phase0():
    import multiprocessing, shutil, subprocess
    cores = multiprocessing.cpu_count()
    try:
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except (AttributeError, ValueError):
        import ctypes   # Windows
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS(); m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        ram = m.ullTotalPhys / 2 ** 30
    gpu = None
    if shutil.which("nvidia-smi"):
        r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
        gpu = r.stdout.strip() or None
    # one Blender render at a time is the rule for the final run; 2 only if RAM and a GPU allow it
    conc = 1 if (ram < 16 and not gpu) else (2 if gpu else 1)
    sync(phase0=dict(cores=cores, ram_gb=round(ram, 1), gpu=gpu or "none", RENDER_CONCURRENCY=conc))
    return conc


def concurrency():
    return int(os.environ.get("KIT_CONCURRENCY", _read(PROG, {}).get("phase0", {}).get("RENDER_CONCURRENCY", 1)))


if __name__ == "__main__":
    if sys.argv[1:] == ["phase0"]:
        print("RENDER_CONCURRENCY =", phase0())
    else:
        sync()
        print(json.dumps(_read(PROG, {}), indent=1)[:3000])
