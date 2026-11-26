"""Kit paths (pathlib, no hardcoded locations), video module loading, portable file locks, CLI args.

Works both in plain Python and inside Blender's bundled Python (no PIL / numpy-only dependencies here).
"""
import importlib.util, os, sys, time, contextlib
from pathlib import Path

KIT = Path(__file__).resolve().parent
VIDEOS = KIT.parent
ASSETS = KIT / "assets"
FONT = ASSETS / "QRBlack.ttf"
FONT_NAME = "QR Montserrat Black"
VOICES = KIT / "voices"
DIGITS = ASSETS / "digits"
FACE_EXPR = ["neutral", "scared", "shocked", "tired", "grumpy", "laughing", "blank", "talk"]
SLUGS_ALL = ["quiet_rule", "mailman", "five_thousand_words", "thousand_bites", "two_thousand_doors", "three_thousand_hours"]
if str(KIT) not in sys.path:
    sys.path.insert(0, str(KIT))


def args():
    """Script arguments, whether run as `python x.py a b` or `blender -b -P x.py -- a b`."""
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else a[1:]


def preview():
    return os.environ.get("KIT_PREVIEW", "0") == "1"


def vdir(slug):
    return VIDEOS / slug


def bdir(slug):
    p = VIDEOS / slug / "build"
    p.mkdir(parents=True, exist_ok=True)
    return p


def frames_dir(slug):
    return bdir(slug) / ("frames_preview" if preview() else "frames")


def final_path(slug):
    return vdir(slug) / ("final_preview.mp4" if preview() else "final.mp4")


def source_hash(slug, names=("story", "config")):
    """Hash of a video's source files (line endings normalised, so a Windows checkout hashes the same)."""
    import hashlib
    h = hashlib.sha1()
    for n in names:
        p = vdir(slug) / f"{n}.py"
        h.update(p.read_bytes().replace(b"\r\n", b"\n") if p.exists() else b"")
    return h.hexdigest()[:16]


TTS_FIELDS = ("VOICE", "SPEAKER", "ENGINE", "EDGE_VOICE", "LENGTH_SCALE", "WPS", "WPS_TARGET", "MAX_SIL", "SQUEEZE_TO",
              "SENT_GAP", "MIN_AUDIO", "RED_NUMBERS", "RED_ALWAYS")


def tts_hash(slug):
    """What the narration depends on: story.py + the voice settings in config.py (not render settings)."""
    import hashlib
    cfg = load(slug, "config")
    h = hashlib.sha1(source_hash(slug, ("story",)).encode())
    h.update(repr([getattr(cfg, f, None) for f in TTS_FIELDS]).encode())
    return h.hexdigest()[:16]


def load(slug, name):
    path = vdir(slug) / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{slug}_{name}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def video(slug):
    return load(slug, "config"), load(slug, "story"), load(slug, "scene")


# ------------------------------------------------------------------ portable locks
def _try_lock(fh):
    try:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except ImportError:
        import msvcrt
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    except (BlockingIOError, OSError):
        return False


def _unlock(fh):
    try:
        import fcntl
        fcntl.flock(fh, fcntl.LOCK_UN)
    except ImportError:
        import msvcrt
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass


@contextlib.contextmanager
def file_lock(path):
    path = Path(str(path) + ".lock")
    fh = open(path, "a+")
    try:
        while not _try_lock(fh):
            time.sleep(0.1)
        yield
    finally:
        _unlock(fh)
        fh.close()


@contextlib.contextmanager
def render_slot():
    """Shared Blender semaphore: never more frame renders at once than RENDER_CONCURRENCY (previews included)."""
    from progress import concurrency
    n = max(1, concurrency())
    while True:
        for i in range(n):
            fh = open(VIDEOS / f".render_slot{i}.lock", "a+")
            if not _try_lock(fh):
                fh.close()
                continue
            try:
                yield i
            finally:
                _unlock(fh)
                fh.close()
            return
        time.sleep(0.3)
