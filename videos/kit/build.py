"""Build videos/<slug>/build/town.blend.  Run inside Blender:
    blender -b -P kit/build.py -- <slug>        (or: python kit/build.py <slug> with the bpy module)
Assets (faces, digits, cards, textures) must exist first: python kit/art.py <slug>"""
import bpy, sys, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import video, bdir, args, DIGITS, source_hash
import blocks, town, avatar, progress


from build_stamp import stamp as scene_stamp


def main(slug):
    cfg, story, scene = video(slug)
    b = bdir(slug)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    blocks.set_style(cfg.STYLE)
    blocks.world_and_render()
    kit = types.SimpleNamespace(blocks=blocks, town=town, avatar=avatar, build_dir=b, style=cfg.STYLE)
    scene.build(kit)
    counter = getattr(cfg, "COUNTER", None)
    for n, spec in scene.CAST.items():
        spec = dict(spec)
        spec["counter"] = bool(counter) and spec.get("counter", True)
        avatar.character(n, spec, b / "faces", DIGITS if counter else None)
    out = b / "town.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    (b / "town.blend.hash").write_text(scene_stamp(slug) + "|" + bpy.app.version_string)
    progress.mark(slug, "dressing", ok=True, objects=len(bpy.data.objects))
    print("saved", out, "objects:", len(bpy.data.objects))


if __name__ == "__main__":
    main(args()[0])
