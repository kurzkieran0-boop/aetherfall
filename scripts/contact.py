# contact sheet helper: python3 scripts/contact.py <glob> <out.jpg> [cols] [thumbW]
import sys, glob
from PIL import Image, ImageDraw
files = sorted(glob.glob(sys.argv[1])); out = sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6; tw = int(sys.argv[4]) if len(sys.argv) > 4 else 300
ims = [Image.open(f) for f in files]
th = int(ims[0].height * tw / ims[0].width)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 18)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * tw, (i // cols) * (th + 18)
    sheet.paste(im.resize((tw, th)), (x, y + 18))
    d.text((x + 3, y + 3), f.split('/')[-1][:44], fill=(230, 230, 200))
sheet.save(out, quality=88)
