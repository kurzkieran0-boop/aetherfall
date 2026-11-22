# Authoring helper: writes timeline.json (kept in Python for readable camera math).
import json
def chase(fb, fu, fs, tb, tu, ts, ahead=8, look=1.2, fov=(50, 50), shake=0, **kw):
    c = {"mode": "chase", "from": {"back": fb, "up": fu, "side": fs, "ahead": ahead, "lookUp": look, "fov": fov[0]},
         "to": {"back": tb, "up": tu, "side": ts, "ahead": ahead, "lookUp": look, "fov": fov[1]}, "ease": kw.pop("ease", "power1.inOut"), "shake": shake}
    c.update(kw); return c
def world(p0, l0, p1, l1, fov=(50, 50), ease="power1.inOut", shake=0, **kw):
    c = {"mode": "world", "from": {"pos": p0, "look": l0, "fov": fov[0]}, "to": {"pos": p1, "look": l1, "fov": fov[1]}, "ease": ease, "shake": shake}
    c.update(kw); return c
def track(p0, p1, look=(0, 1, 0), relZ=False, fov=(50, 50), ease="power1.inOut", target=None, shake=0):
    c = {"mode": "track", "from": {"pos": p0, "lookOff": list(look), "fov": fov[0]}, "to": {"pos": p1, "lookOff": list(look), "fov": fov[1]}, "relZ": relZ, "ease": ease, "shake": shake}
    if target: c["target"] = target
    return c
def orbit(a0, a1, r0, r1, up=1.3, look=0.9, fov=(45, 45), target=None, ease="power1.inOut"):
    c = {"mode": "orbit", "from": {"angle": a0, "radius": r0, "up": up, "lookUp": look, "fov": fov[0]}, "to": {"angle": a1, "radius": r1, "up": up, "lookUp": look, "fov": fov[1]}, "ease": ease}
    if target: c["target"] = target
    return c
def shot(i, scene, cam, car=None, fx=None, sound=None, **kw):
    d = {"id": i, "scene": scene, "duration": "auto", "camera": cam, "fx": fx or {}}
    if car: d["car"] = car
    if sound: d["sound"] = sound
    d.update(kw); return d

T = 2060  # tower z
beats = [
 {"id": "B0", "name": "HOOK", "lead": 0.12, "tease": "WHO'S DRIVING?",
  "music": {"kick": True, "clap": True, "hats": "16", "bass": True, "arp": "16", "lead": True, "energy": 1.05},
  "narration": ["In *Neo Kaia*, every car *drives itself*.", "Every *light*, every *lane*, every *turn* is decided by *one machine*.", "Mine is the *only car* with a *steering wheel*."],
  "shots": [
   shot("B0-1", "city", chase(14, 2.6, -3.5, 11, 1.7, 2.5, fov=(58, 48), shake=0.12, ease="none"), car={"s": [110, 250]}, overlay={"style": "hook", "text": ["EVERY CAR HERE", "DRIVES ITSELF.", "EXCEPT MINE."]}, sound=[{"sfx": "engine", "at": 0, "dur": 3.4, "from": 90, "to": 170}, {"sfx": "rain", "at": 0, "dur": 60, "gain": 1}]),
   shot("B0-2", "city", world([0, 78, -150], [0, 0, -330], [4, 58, -235], [0, 0, -360], fov=(55, 50)), car={"s": [250, 330]}, fx={"drones": 12}),
   shot("B0-3", "city", track([1.6, 1.7, 7], [1.4, 1.5, -5], look=(0, 0.9, -2), relZ=True, fov=(46, 40)), car={"s": [330, 430]}, sound=[{"sfx": "whoosh", "at": 0.5, "gain": 0.6}]),
   shot("B0-4", "city", orbit(140, 220, 12, 10.5, up=1.8, look=0.8, fov=(44, 40)), car={"s": [430, 470]}),
  ]},
 {"id": "B1", "name": "THE JOB", "tease": "WHAT'S ON IT?",
  "music": {"kick": True, "hats": "8", "bass": True, "arp": "16", "pad": True, "energy": 0.85},
  "narration": ["I'm *Kira*.", "I move things the *grid* can't *see*.", "Tonight's package is a *drive* the size of a *fingernail*,", "and the client paid in *cash*, which *nobody* does anymore."],
  "shots": [
   shot("B1-1", "city", track([15.2, 1.7, -33], [15.0, 1.6, -35], target="kira", look=(0, 1.3, 0), fov=(42, 36)), car={"s": [47, 47], "lane": 11.0}, fx={"kira": {"pos": [13.4, 0, -40.5], "yaw": -0.9}, "beams": False}),
   shot("B1-2", "city", orbit(-70, -20, 7.5, 6.2, up=2.2, look=1.0, fov=(46, 42), target="kira"), car={"s": [47, 47], "lane": 11.0}, fx={"kira": {"pos": [13.4, 0, -40.5], "yaw": -0.9, "pose": "reach", "reach": [0.05, 0.4]}, "beams": False, "blur": 0}),
   shot("B1-3", "city", chase(11, 1.8, 3, 14, 2.6, -1, fov=(45, 52), ease="power2.in"), car={"s": [47, 150], "ease": "power2.in", "lane": 7.5}, sound=[{"sfx": "engine", "at": 0.05, "dur": 3.6, "from": 60, "to": 150}, {"sfx": "screech", "at": 0.08, "dur": 0.8, "gain": 0.6}]),
   shot("B1-4", "city", track([22, 42, 26], [16, 36, 6], look=(0, 0, -6), relZ=True, fov=(50, 46)), car={"s": [140, 230]}, fx={"drones": 8}),
  ]},
 {"id": "B2", "name": "THE GRID WAKES", "tease": "RUN.",
  "music": {"kick": True, "bass": True, "arp": "8", "pad": "loud", "energy": 0.8},
  "narration": ["Three blocks in, *every traffic light* turns *red* at once.", "The other cars *stop*.", "Then they *turn around*.", "*All of them*.", "Toward *me*."],
  "shots": [
   shot("B2-1", "city", world([1.5, 5.2, -150], [5, 6.0, -330], [1.8, 5.6, -160], [5, 6.0, -330], fov=(34, 30)), car={"s": [182, 196], "ease": "power2.out"}, fx={"red": 0.35, "flash": [[0.35, 0.18]], "flashCol": [1, 0.2, 0.25], "blur": 0}, sound=[{"sfx": "buzz", "at": 0.35, "dur": 1.2, "gain": 0.8}]),
   shot("B2-2", "city", world([0, 22, -150], [0, 2, -300], [0, 18, -165], [0, 2, -300], fov=(52, 48)), car={"s": [196, 205], "ease": "power2.out"}, fx={"red": 0, "trafficStop": 0.1}, sound=[{"sfx": "screech", "at": 0.12, "dur": 1.2, "gain": 0.5}]),
   shot("B2-3", "city", world([-2, 1.2, -228], [0, 1.2, -320], [-2, 1.0, -232], [0, 1.0, -320], fov=(40, 40)), car={"s": [205, 205]}, fx={"red": 0, "trafficStop": 0, "trafficTurn": [0.15, 0.75]}, sound=[{"sfx": "screech", "at": 0.15, "dur": 1.8, "gain": 0.7}]),
   shot("B2-4", "city", chase(-15, 3.6, 2.8, -11, 2.4, 2.2, ahead=0, look=0.9, fov=(44, 38), shake=0.1), car={"s": [205, 207]}, fx={"red": 0, "trafficStop": 0, "trafficTurn": [0, 0.01], "drones": 24, "flash": [[0.45, 0.3]], "flashCol": [0.9, 0.95, 1]}, sound=[{"sfx": "siren", "at": 0.2, "dur": 3, "gain": 0.8}]),
  ]},
 {"id": "B3", "name": "THE CHASE", "tease": "TOO LATE?",
  "music": {"kick": "busy", "clap": True, "hats": "16", "bass": True, "arp": "16", "lead": True, "energy": 1.15},
  "narration": ["So I *floor it*.", "Through the *market tunnel*,", "down the *wrong side* of the *skyway*,", "and straight at the *drawbridge* while it's still *rising*."],
  "shots": [
   shot("B3-1", "city", chase(10, 1.3, 2.5, 13, 2.0, -2, fov=(48, 64), shake=0.35, ease="power2.in"), car={"s": [207, 330], "ease": "power2.in"}, fx={"red": 0, "trafficStop": 0, "trafficTurn": [0, 0.01], "drones": 30}, sound=[{"sfx": "screech", "at": 0.02, "dur": 0.9}, {"sfx": "engine", "at": 0.02, "dur": 3.8, "from": 70, "to": 230, "gain": 1.2}]),
   shot("B3-2", "city", chase(11, 1.6, -4.5, 9, 1.2, 3.5, fov=(60, 55), shake=0.2, ease="none", whipIn="left"), car={"s": [630, 790], "weave": 2.5}, sound=[{"sfx": "engine", "at": 0, "dur": 3.6, "from": 180, "to": 220}]),
   shot("B3-3", "city", chase(16, 6, 3, 12, 3.5, -2, fov=(55, 50), shake=0.2, ease="none"), car={"s": [1060, 1230], "lane": -5.5, "weave": 1.8}, fx={"drones": 30}, sound=[{"sfx": "whoosh", "at": 0.3, "gain": 0.7}, {"sfx": "whoosh", "at": 0.65, "gain": 0.6}]),
   shot("B3-4", "city", chase(13, 2.5, 0, 10, 1.6, 0, ahead=40, look=6, fov=(52, 60), shake=0.3, ease="none"), car={"s": [1360, 1500]}, fx={"bridgeLift": [0.05, 0.24], "drones": 40}, sound=[{"sfx": "siren", "at": 0, "dur": 3.5, "gain": 0.6}, {"sfx": "engine", "at": 0, "dur": 3.8, "from": 200, "to": 260}]),
  ]},
 {"id": "B4", "name": "THE JUMP", "tease": "AND THEN?",
  "music": {"pad": "loud", "arp": "8", "arpLevel": 0.6, "energy": 0.7},
  "narration": ["For *two seconds*, I'm *flying*.", "Below me, *ten thousand headlights*.", "Above me, the *drones*.", "Ahead, *Tower Nine*."],
  "shots": [
   shot("B4-1", "city", track([38, 30, 30], [38, 36, -10], look=(0, 1, 0), relZ=True, fov=(46, 40), ease="none"), car={"s": [1512, 1600], "jump": True}, fx={"bridgeLift": [0.26, 0.28], "rainRel": 0.3, "blur": 0.2}, sound=[{"sfx": "whoosh", "at": 0.1, "gain": 1.0}]),
   shot("B4-2", "city", world([-55, 44, -1520], [0, 12, -1575], [-48, 40, -1540], [0, 14, -1590], fov=(58, 54)), car={"s": [1540, 1585], "jump": True}, fx={"bridgeLift": [0.28, 0.28], "rainRel": 0.3}),
   shot("B4-3", "city", chase(11, 7, 12, 9, 6, 10, ahead=-2, look=6, fov=(62, 58)), car={"s": [1560, 1592], "jump": True}, fx={"bridgeLift": [0.28, 0.28], "drones": 70, "rainRel": 0.3}, sound=[{"sfx": "buzz", "at": 0, "dur": 3.5, "gain": 1}]),
   shot("B4-4", "city", chase(15, 5, 0, 12, 3, 0, ahead=260, look=160, fov=(50, 58), shake=0.25, ease="none"), car={"s": [1606, 1720], "jump": True}, fx={"bridgeLift": [0.28, 0.28], "drones": 20}, sound=[{"sfx": "impact", "at": 0.03, "gain": 0.8}, {"sfx": "screech", "at": 0.05, "dur": 1}]),
  ]},
 {"id": "B5", "name": "TOWER NINE", "tease": "A TRAP?",
  "music": {"kick": True, "bass": True, "arp": "16", "pad": True, "energy": 0.85},
  "narration": ["*Tower Nine* is where the *grid lives*.", "The client said: plug it into the *core*, and the city goes *free*.", "I take the elevator *two hundred floors* up,", "and *nobody* stops me.", "That should've been my *first clue*."],
  "shots": [
   shot("B5-1", "city", world([10, 34, -1760], [0, 420, -T], [8, 30, -1800], [0, 560, -T], fov=(62, 58)), car={"s": [1880, 1960], "ease": "power2.out"}),
   shot("B5-2", "city", track([-6, 26.5, -1972], [-5, 26, -1988], target="kira", look=(0, 1.2, 0), fov=(46, 42)), car={"s": [1970, 1970]}, fx={"kira": {"from": [2.5, 24, -1978], "to": [0.3, 24, -2007], "yaw": 3.05}, "beams": False}),
   shot("B5-3", "city", world([34, 90, -1960], [0, 120, -2012], [34, 280, -1960], [0, 330, -2012], fov=(50, 50)), car={"s": [1970, 1970]}, fx={"elevator": [0, 420], "beams": False}, sound=[{"sfx": "ding", "at": 0.92}]),
   shot("B5-4", "core", world([0, 1.8, -6], [0, 2.2, -60], [0, 1.8, -22], [0, 2.2, -60], fov=(50, 48)), fx={"kira": {"from": [0, 0, -12], "to": [0, 0, -30], "yaw": 3.1416}}),
   shot("B5-5", "core", world([-4.5, 0.6, -36], [0, 4.5, -46], [-3.5, 0.6, -40], [0, 4.5, -48], fov=(44, 44)), fx={"kira": {"from": [0, 0, -38], "to": [0, 0, -48], "yaw": 3.1416}, "pulse": [0.4, 0.8]}, sound=[{"sfx": "buzz", "at": 0.4, "dur": 2, "gain": 0.5}]),
  ]},
 {"id": "B6", "name": "THE CORE", "lead": 0.3, "tease": "BACK?!",
  "music": {"pad": "loud", "drone": True, "arp": "8", "arpLevel": 0.5, "energy": 0.6},
  "narration": ["The core is a *wall of light*.", "I *plug* the drive in.", "The screen goes *black*.", "Then *white*.", "And one line appears:", "*Welcome back*, *Kira*."],
  "shots": [
   shot("B6-1", "core", world([0, 3, -40], [0, 9, -90], [0, 3.4, -58], [0, 9.5, -90], fov=(52, 48)), fx={"kira": {"pos": [0, 0, -82], "yaw": 3.1416}}, fromLine=0),
   shot("B6-2", "core", world([2.6, 1.7, -80.6], [0, 1.25, -83.6], [2.2, 1.6, -81.2], [0, 1.25, -83.6], fov=(36, 32)), fx={"kira": {"pos": [0, 0, -83.1], "yaw": 3.1416, "pose": "reach", "reach": [0.05, 0.45]}, "plugged": 0.5, "blur": 0}, sound=[{"sfx": "click", "atLine": 1, "offset": 0.4}], fromLine=1),
   shot("B6-3", "core", world([0, 2.5, -52], [0, 9, -90], [0, 2.6, -60], [0, 9, -90], fov=(50, 50)), fx={"kira": {"pos": [0, 0, -82], "yaw": 3.1416}, "screen": {"black": 0.0, "white": 0.5}, "flash": [[0.5, 0.6]]}, sound=[{"sfx": "riser", "endLine": 5}], fromLine=2),
   shot("B6-4", "core", world([1.8, 2.4, -72], [0, 9, -90], [1.2, 2.3, -76], [0, 9.5, -90], fov=(46, 40)), fx={"kira": {"pos": [0, 0, -82], "yaw": 3.1416}, "screen": {"text": 0.0, "typeAt": 0.55}, "glitch": [0.6, 0.7, 0.4]}, sound=[{"sfx": "impact", "atLine": 5}, {"sfx": "glitch", "atLine": 5, "offset": 0.6, "dur": 0.6}], fromLine=4),
  ]},
 {"id": "B7", "name": "CLIFFHANGER", "lead": 0.25,
  "music": {"drone": True, "pad": True, "energy": 0.5},
  "musicDrop": {"kick": "busy", "clap": True, "hats": "16", "bass": True, "arp": "16", "lead": True, "pad": "loud", "energy": 1.2},
  "dropLine": 3,
  "narration": [{"text": "*Back*?", "speed": 1.0}, {"text": "I've *never* been here.", "speed": 1.0}, {"text": "Then *every screen* in the city shows the *same face*.", "speed": 1.12}, {"text": "*Mine*.", "speed": 0.95}, {"text": "And the grid speaks in *my voice*:", "speed": 1.1}, {"text": "*Thanks* for bringing me *home*.", "speed": 1.0}],
  "shots": [
   shot("B7-1", "core", world([1.2, 1.7, -77.5], [0, 6, -90], [0.8, 1.7, -78.5], [0, 6.5, -90], fov=(48, 42)), fx={"kira": {"pos": [0, 0, -82.5], "yaw": 3.1416}, "screen": {"full": True, "msg": "WELCOME BACK, KIRA."}, "blur": 0}, fromLine=0),
   shot("B7-2", "city", world([2, 12, -230], [0, 34, -420], [2, 12, -270], [0, 36, -460], fov=(60, 56)), car={"s": [215, 215]}, fx={"face": 0.12, "glitch": [0.1, 0.2, 0.6], "trafficStop": 0, "trafficTurn": [0, 0.01]}, sound=[{"sfx": "glitch", "at": 0.1, "dur": 0.8}, {"sfx": "riser", "endLine": 3}], fromLine=2),
   shot("B7-3", "city", world([40, 520, -1700], [0, 700, -T], [30, 560, -1760], [0, 710, -T], fov=(48, 40)), car={"s": [1970, 1970]}, fx={"face": 0.0, "glitch": [0.0, 0.08, 0.8], "flash": [[0.0, 0.5]], "flashCol": [0.4, 1, 1]}, fromLine=3),
   shot("B7-4", "city", world([90, 110, -1440], [0, 0, -1600], [80, 100, -1460], [0, 0, -1620], fov=(60, 56), shake=0.3), car={"s": [1970, 1970]}, fx={"face": 0.0, "riverTurn": [0.1, 0.6], "allLit": 0.5, "flash": [[0.5, 0.4]]}, sound=[{"sfx": "glitch", "at": 0.48, "dur": 0.5}], fromLine=4),
   shot("B7-5", "core", world([0, 1.7, -72], [0, 5, -90], [0, 1.65, -75], [0, 5.5, -90], fov=(50, 46)), fx={"kira": {"pos": [0, 0, -82], "yaw": 3.1416}, "screen": {"full": True, "msg": "THANKS FOR BRINGING ME HOME.", "sub": "— KIRA"}, "glitch": [0.75, 1.0, 0.8], "pulse": [0, 0.5]}, sound=[{"sfx": "whoosh", "at": "end", "gain": 1}], fromLine=5),
  ]},
]
tl = {
  "series": "LAST DRIVER", "part": 1, "output": "last-driver-part1.mp4", "width": 1080, "height": 1920, "fps": 30, "bpm": 128,
  "minDuration": 120, "maxDuration": 170, "shotBeats": {"min": 7, "max": 10},
  "voice": {"engine": "kokoro", "voice": "af_nova", "speed": 1.08, "lang": "en-us", "fallbacks": ["piper", "edge-tts"], "edgeVoice": "en-US-AriaNeural"},
  "beats": beats,
  "endCard": {"id": "END", "scene": "city", "beats": 9, "flashIn": 1.0,
    "music": {"kick": "busy", "clap": True, "hats": "16", "bass": True, "arp": "16", "lead": True, "pad": "loud", "energy": 1.1},
    "camera": chase(18, 3.4, -5, 14, 2.6, -3.5, fov=(62, 58), ease="power2.in"), "car": {"s": [-20, 110], "ease": "power2.in"},
    "fx": {}, "overlay": {"style": "end", "text": ["PART 2", "FOLLOW SO YOU", "DON'T MISS IT."]},
    "sound": [{"sfx": "impact", "at": 0}, {"sfx": "engine", "at": 0.3, "dur": 3.5, "from": 70, "to": 170}]},
}
json.dump(tl, open(__file__.replace("build_timeline.py", "timeline.json"), "w"), indent=1)
print(sum(len(b["shots"]) for b in beats) + 1, "shots")
