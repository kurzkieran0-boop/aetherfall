"""Verify final.mp4: duration/size/audio, shot rules, black frames, contact sheet + sync strips."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build")
FINAL = os.path.join(HERE, "final.mp4")


def probe():
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
                          "-of", "json", FINAL], capture_output=True, text=True).stdout
    return json.loads(out)


def grab(t, path, w=270, h=480):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", FINAL, "-frames:v", "1",
                    "-vf", f"scale={w}:{h}", path], check=True)
    return Image.open(path).convert("RGB")


def main():
    fails = []
    p = probe()
    dur = float(p["format"]["duration"])
    v = [s for s in p["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    print(f"duration {dur:.2f}s  video {v['codec_name']} {v['width']}x{v['height']} @ {v['r_frame_rate']}  "
          f"audio: {a[0]['codec_name'] if a else 'MISSING'}")
    if dur < 135: fails.append("duration < 135s")
    if (v["width"], v["height"]) != (1080, 1920): fails.append("not 1080x1920")
    if v["r_frame_rate"] != "30/1": fails.append("not 30fps")
    if not a: fails.append("no audio stream")

    shots = json.load(open(os.path.join(HERE, "shots.json")))["shots"]
    content = [s for s in shots if s["kind"] != "black"]
    longest = max(s["dur"] for s in content)
    print(f"shots: {len(content)} (+ end black), longest {longest:.2f}s, "
          f"cards {sum(s['kind'] == 'card' for s in content)}")
    if len(content) < 70: fails.append("fewer than 70 shots")
    if longest > 3.0: fails.append("a shot is longer than 3s")

    # black / empty frames anywhere before the final hard cut
    end_black = shots[-1]["frame0"] / 30
    r = subprocess.run(["ffmpeg", "-v", "info", "-t", f"{end_black - 0.05:.2f}", "-i", FINAL, "-vf",
                        "blackdetect=d=0.1:pic_th=0.94:pix_th=0.08", "-an", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    blacks = [l for l in r.splitlines() if "black_start" in l]
    print("black segments before ending:", len(blacks))
    for l in blacks[:5]:
        print("   ", l.split("]")[-1].strip())
    if blacks: fails.append("black frames mid-video")

    # loudness (voice present throughout)
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", FINAL, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    print("audio:", " ".join(l.split("]")[-1].strip() for l in r.splitlines() if "mean_volume" in l or "max_volume" in l))

    # contact sheet: 24 frames
    os.makedirs(os.path.join(B, "verify"), exist_ok=True)
    sheet = Image.new("RGB", (6 * 270, 4 * 480))
    for i in range(24):
        t = (i + 0.5) * end_black / 24
        im = grab(t, os.path.join(B, "verify", f"c{i:02d}.png"))
        ImageDraw.Draw(im).text((6, 6), f"{t:6.1f}s", fill=(255, 255, 0))
        sheet.paste(im, ((i % 6) * 270, (i // 6) * 480))
    sheet.save(os.path.join(HERE, "contact_sheet.png"))

    # sync spot-checks: frame at the middle of a word should show that word
    tl = json.load(open(os.path.join(B, "timeline.json")))
    words = [w for s in tl["sentences"] for w in s["words"]]
    picks = [words[3], words[len(words) // 2], words[-2]]
    strip = Image.new("RGB", (3 * 360, 640))
    for i, w in enumerate(picks):
        t = (w["start"] + w["end"]) / 2
        im = grab(t, os.path.join(B, "verify", f"sync{i}.png"), 360, 640)
        ImageDraw.Draw(im).text((6, 6), f"{t:6.2f}s expect '{w['text']}'", fill=(255, 255, 0))
        strip.paste(im, (i * 360, 0))
        print(f"sync check @ {t:.2f}s: expected word '{w['text']}' (red={w['red']})")
    strip.save(os.path.join(HERE, "sync_check.png"))

    print("contact sheet:", os.path.join(HERE, "contact_sheet.png"))
    print("RESULT:", "PASS" if not fails else "FAIL -> " + "; ".join(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
