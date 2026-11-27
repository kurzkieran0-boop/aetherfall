"""One-command pipeline for all six videos (called by run_all.ps1; works on Windows, macOS and Linux).

python kit/run_all.py [--blender PATH] [--preview] [--only SLUG] [--dry-run]

  1. hardware check (RENDER_CONCURRENCY: one Blender render at a time unless RAM + GPU allow more)
  2. per video: TTS + word timestamps (regenerated only if missing), shot list, faces/cards/textures, Blender scene
  3. render every shot, resume-safe, shortest video first, one Blender process at a time
  4. assemble (captions burned in) and verify each final.mp4, then print the table
--preview : 540x960, minimum samples -> final_preview.mp4 (quick look at all six)
--dry-run : everything except the full render: one test still per video + placeholder frames for assemble/verify
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT, VIDEOS, SLUGS_ALL, vdir, bdir, frames_dir, final_path, tts_hash

PY = sys.executable


def sh(cmd, env=None, check=True):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], env=env)
    if check and r.returncode:
        raise SystemExit(f"step failed ({r.returncode}): {' '.join(str(c) for c in cmd)}")
    return r.returncode


def find_blender(arg):
    if arg:
        return [arg, "-b", "--factory-startup", "--python-exit-code", "1", "-P"]
    b = shutil.which("blender")
    if not b and os.name == "nt":
        for root in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blender Foundation",):
            cands = sorted(root.glob("Blender*/blender.exe"), reverse=True) if root.exists() else []
            if cands:
                b = str(cands[0])
    if b:
        return [b, "-b", "--factory-startup", "--python-exit-code", "1", "-P"]
    try:   # the bpy module inside this Python (used on the build machine)
        import importlib.util
        if importlib.util.find_spec("bpy"):
            return [PY]
    except Exception:
        pass
    raise SystemExit("Blender not found: install it (winget install BlenderFoundation.Blender) or pass --blender PATH")


def newer(a, b):
    """True if file a is missing or older than any of b."""
    a = Path(a)
    if not a.exists():
        return True
    return any(Path(x).exists() and Path(x).stat().st_mtime > a.stat().st_mtime for x in b)


def placeholder_frames(slug):
    """Dry run only: cheap moving placeholder frames so assemble/verify can be exercised without Blender renders."""
    from PIL import Image, ImageDraw
    sj = json.loads((vdir(slug) / "shots.json").read_text())
    for s in sj["shots"]:
        if s["kind"] != "render":
            continue
        d = frames_dir(slug) / s["id"]
        if (d / ".done").exists():
            continue
        d.mkdir(parents=True, exist_ok=True)
        for i in range(s["frames"]):
            hue = (int(s["id"][5:]) * 37) % 200
            im = Image.new("RGB", (540, 960), (40 + hue // 2, 60 + (hue * 3) % 120, 90 + hue // 3))
            dr = ImageDraw.Draw(im)
            dr.rectangle([60 + i * 6, 300, 200 + i * 6, 440], fill=(230, 220, 200))
            dr.text((30, 30), f"{slug} {s['id']} {s['set']}/{s['cam']} f{i}", fill=(255, 255, 255))
            im.save(d / f"f_{i:04d}.png")
        (d / ".done").write_text("placeholder")


def main():
    a = sys.argv[1:]
    preview = "--preview" in a or "--dry-run" in a
    dry = "--dry-run" in a
    only = a[a.index("--only") + 1] if "--only" in a else None
    blender = find_blender(a[a.index("--blender") + 1] if "--blender" in a else None)
    env = dict(os.environ)
    env["KIT_PREVIEW"] = "1" if preview else "0"
    env["KIT_CONCURRENCY"] = "1"
    env["PYTHONUTF8"] = "1"
    os.environ.update(env)
    slugs = [only] if only else [s for s in SLUGS_ALL if (vdir(s) / "config.py").exists()]
    t_start = time.time()
    print("== phase 0: hardware", flush=True)
    sh([PY, KIT / "progress.py", "phase0"], env)
    print("== phase 1-2: narration, shots, art, scenes", flush=True)
    for s in slugs:
        B = bdir(s)
        v = vdir(s)
        tl = B / "timeline.json"
        if not (B / "voice.wav").exists() and (B / "voice.flac").exists():      # shipped narration (FLAC)
            sh(["ffmpeg", "-y", "-v", "error", "-i", B / "voice.flac", "-c:a", "pcm_s16le", B / "voice.wav"], env)
        stale = not tl.exists() or json.loads(tl.read_text()).get("source_hash") != tts_hash(s)
        if stale or not (B / "voice.wav").exists():
            print(f"  [{s}] narration missing or story changed -> regenerating TTS + word timestamps", flush=True)
            sh([PY, KIT / "tts.py", s], env)
        sh([PY, KIT / "shots.py", s], env)
        sh([PY, KIT / "art.py", s], env)
        import build_stamp
        want = build_stamp.stamp(s)
        have = (B / "town.blend.hash").read_text().split("|")[0] if (B / "town.blend.hash").exists() else ""
        if not (B / "town.blend").exists() or have != want:
            sh(blender + [KIT / "build.py", "--", s], env)
    order = sorted(slugs, key=lambda s: json.loads((bdir(s) / "timeline.json").read_text())["duration"])
    print("== phase 3: render (shortest first):", ", ".join(order), flush=True)
    rows = []
    for s in order:
        B = bdir(s)
        if not dry and final_path(s).exists() and (B / ".cleaned").exists():     # finished earlier: frames were deleted to save disk
            print(f"== {s}: already finished ({final_path(s).name}), skipping", flush=True)
            st = json.loads((vdir(s) / "status.json").read_text())
            ver = st.get("preview_verified" if preview else "verified", {})
            rows.append((str(final_path(s).relative_to(VIDEOS.parent)), ver.get("duration", "?"), ver.get("shots", "?"),
                         ver.get("wps", "?"), "; ".join(ver.get("flaws", [])) or "none"))
            continue
        if dry:
            sj = json.loads((vdir(s) / "shots.json").read_text())
            renders = [x["id"] for x in sj["shots"] if x["kind"] == "render"]
            first = getattr(__import__("common").load(s, "config"), "TEST_SHOT", None) or renders[len(renders) // 3]
            sh(blender + [KIT / "render.py", "--", s, "--only", first, "--still", bdir(s) / "test_still", "--res", "540x960"], env)
            placeholder_frames(s)
        else:
            sh(blender + [KIT / "render.py", "--", s], env)
        # assemble + verify each video as soon as its shots are done, so finished videos appear early
        print(f"== assemble + verify {s}", flush=True)
        sh([PY, KIT / "assemble.py", s], env)
        sh([PY, KIT / "verify.py", s], env, check=False)
        st = json.loads((vdir(s) / "status.json").read_text())
        ver = st.get("preview_verified" if preview else "verified", {})
        rows.append((str(final_path(s).relative_to(VIDEOS.parent)), ver.get("duration", "?"), ver.get("shots", "?"),
                     ver.get("wps", "?"), "; ".join(ver.get("flaws", [])) or "none"))
        if not dry and final_path(s).exists() and ver and not ver.get("flaws"):
            # the video is done and verified: delete its frames + clips (many GB) so the disk does not fill up
            for d in (frames_dir(s), B / ("clips_preview" if preview else "clips")):
                shutil.rmtree(d, ignore_errors=True)
            (B / ".cleaned").write_text("frames and clips removed after a verified final video")
            print(f"== {s}: verified; frames and clips deleted to free disk space", flush=True)
    print("\n" + "=" * 110)
    print(f"{'path':44s} {'duration':>9s} {'shots':>6s} {'wps':>5s}  flaws")
    for r in rows:
        print(f"{r[0]:44s} {str(r[1]):>9s} {str(r[2]):>6s} {str(r[3]):>5s}  {r[4]}")
    print("=" * 110)
    print(f"total time {(time.time() - t_start) / 60:.1f} min")


if __name__ == "__main__":
    main()
