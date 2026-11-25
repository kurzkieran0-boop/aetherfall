"""Render the middle frame of selected shots for a quick look: python3 preview.py shot_001,shot_005 ..."""
import json, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_shots as R
from PIL import Image

ids = sys.argv[1].split(",") if len(sys.argv) > 1 else None
shots = [s for s in json.load(open(os.path.join(R.HERE, "shots.json")))["shots"] if s["kind"] == "render"]
if ids:
    shots = [s for s in shots if s["id"] in ids]
st = R.Stage()
out = os.path.join(R.HERE, "build", "preview")
os.makedirs(out, exist_ok=True)
ims = []
for sh in shots:
    st.mood(sh["light"] if sh["set"] not in ("kitchen", "door") else "interior")
    actors = st.actors_for(sh)
    bias = st.choose_bias(sh, actors)
    t = sh["dur"] * 0.6
    st.apply(sh, t, actors)
    st.place_cam(*st.cam_rig(sh, t, actors, bias))
    p = os.path.join(out, sh["id"] + ".png")
    st.sc.render.filepath = p
    R.bpy.ops.render.render(write_still=True)
    ims.append((sh, Image.open(p).convert("RGB").resize((180, 320))))
cols = 8
rows = math.ceil(len(ims) / cols)
sheet = Image.new("RGB", (cols * 180, rows * 320), (0, 0, 0))
from PIL import ImageDraw
for i, (sh, im) in enumerate(ims):
    d = ImageDraw.Draw(im)
    d.text((4, 4), f"{sh['id'][5:]} {sh['set']}/{sh['cam']}/{sh['tgt']}", fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * 180, (i // cols) * 320))
sheet.save(os.path.join(out, "sheet.png"))
print("sheet", len(ims))
