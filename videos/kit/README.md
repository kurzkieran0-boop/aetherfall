# Shared kit — how a video is built

A video is `videos/<slug>/{config.py, story.py, scene.py}` on top of this kit. Reference implementations:
`videos/quiet_rule/` (Style A, interiors, hooks) and `videos/_smoke/` (Style B, counter, lake).

## Commands (run from `videos/`; on this Linux box `python3` has the `bpy` module, so Blender steps run as python3)
```
python3 kit/tts.py <slug>        # Piper narration, silence squeeze, auto-tuned to config.WPS, extension beats, whisper word times
python3 kit/shots.py <slug>      # shots.json (cuts every ~1-2 s, max 3 s), counter keyframes, sfx times
python3 kit/art.py <slug>        # faces / digits / cards / style-B textures (PIL)
python3 kit/build.py <slug>      # Blender scene -> build/town.blend   (on Windows: blender -b -P kit/build.py -- <slug>)
KIT_PREVIEW=1 python3 kit/render.py -- <slug> --only shot_010,shot_050 --still <slug>/build/preview_stills --res 270x480
                                 # test stills only (frame at 60% of each shot). NEVER render full shots here.
```
All Blender renders share one semaphore (videos/.render_slot0.lock), so stills from several videos queue politely.

## config.py
```
SLUG, TITLE, NARRATOR, STYLE ("A" flat low-poly | "B" textured semi-realistic)
VOICE = "en_US-xxx-medium"   # Piper voice name (auto-downloaded to kit/voices); SPEAKER = n for multi-speaker voices
LENGTH_SCALE = 0.95          # starting pace; tts.py auto-tunes it into WPS (generated at source, never sped up after)
WPS = (3.0, 3.6); MIN_AUDIO = 140.0 (extension beats are added until reached); MIN_SHOTS = 80
SHOT_TARGET = 1.4 (s); SAMPLES = 8 (full render); TEST_SHOT = "shot_0xx" (the one still checked in the dry run)
COUNTER = dict(label="words", who="finn") | None ; RED_NUMBERS = True (countdown numbers < 300 red) ; RED_ALWAYS = ("stone",)
```

## story.py
* `S = [(id, text, beats, light), ...]` — text VERBATIM from the brief. light: "day" | "golden" | "dusk" | "night".
  CAPS words are red captions automatically.
* `EXTRA = [(insert_after_id, (id, text, beats, light)), ...]` extension beats, used in order only while narration < MIN_AUDIO.
  An extra may be inserted after an earlier extra (list it later).
* `CARDS = {key: ([lines], [struck_line_indexes])}` lined-paper insert cards; beat `dict(card="key")`.
* `COUNTERS = {sentence_id: {char: spec}}` — spec is an int (counter jumps to it at sentence start) or a list of
  `(word, value[, "ramp"|"step"])` anchored to that word's spoken start (first match after the previous one; also
  "start"/"end"). "ramp" (default) ticks down smoothly from the previous key; "step" jumps. Initial values come from
  `CAST[name]["start"]`. Countdown numbers SPOKEN in the script must equal the counter at that word (verify checks).
* `COUNTDOWN = [sentence ids with spoken countdown numbers]` (red numbers + counter check)
* `SFX = {"heartbeat": [sentence ids], "stone": [(sentence_id, "word")]}` (heartbeat during countdowns, stone thud)

### beats
`dict(set=, cam=, tgt=, ...)` (a cut every ~1-2 s; the planner adds camera variants if a sentence needs more shots)
* cams: `ecu cu mcu(chest-up: face + counter) counter(ECU on chest counter) push pull low high ots(over=actor) whip track
  chase(behind subject) tilt orbit dutch wide drone(radius=) prop sky pan orbit_room tilt_wall ecu_wall shelf_pan
  ecu_hook hands`
* tgt: an actor in the set (aims at the head), `"pt:x,y,z"`, a PROPS key, `"<actor>_chest"`, `"<actor>_held_<kind>"`,
  or any object name in the blend.
* other keys: `acts={actor: act}`, `faces={actor: expr}`, `hide=[actors]`, `add={actor: (x,y,deg,act,z)}`,
  `paper=True` (paper rustle sfx), `light="night"` (override), `blind=True` (pure black POV shot, video 6 only),
  plus any custom key your scene.apply hook reads (e.g. `fire=True`, `door="open"`, `boat=0.4`).
* faces: neutral scared shocked tired grumpy laughing blank talk
* acts: idle walk walk_down run sneak sit sit_talk lie talk whisper laugh yell sing point clap wave sign(hand signals)
  nod shrug hug read hold give eat drink pour shake peek stagger head_turn head_turn_r look_down look_up paddle cry turn.
  Held props: `"hold:whiteboard"`, `"read:env"`, `"drink:thermos"`, `"give:loaf"`, `"eat:crumb"` (kind must be in CAST held).

## scene.py
* `CAST = {name: dict(shirt, pants, hair, skin, scale, kind, held=[kinds], label="TEXT", start=<counter start>)}`
  kinds: kid mail mom dad baker pell mayor farmer granny baby doctor plain. Held kinds: env postcard whiteboard
  thermos loaf crumb key. A character faces +Y locally; facing angle 0 = +X, 90 = +Y.
* `SETS = {set: {actor: (x, y, facing_deg, default_act, z)}}` — only listed actors are on screen.
* `PROPS = {name: (x, y, z, facing_deg)}` camera targets; camera sits on the facing side.
* optional: `HATS` (pull close-ups back), `ROOMS = {set: (x0,x1,y0,y1,zmax)}` (clamp cameras inside closed rooms),
  `INTERIOR_SETS`, `SET_MOOD = {set: mood}`, `LIGHTS = {light_obj: {sets}}`, `FAR_PROPS` (push from far away),
  `STRAIGHT_PROPS`, `DEFAULT_FACE = {actor: expr}`, `NEEDS_ENVWALL`.
* `build(kit)` — make the world with `kit.town` / `kit.blocks`:
  * town: `ground(roads, plazas, keep_clear)`, `houses(north=[x..], south=[x..])` (y=±14), `bakery(x,y)`,
    `school(x,y)`, `post_office`, `town_hall(x,y,podium=(x,y))`, `utilities(xs, y, lamps_x, lamp_y, barrels_at)`,
    `trees(points, style)`, `field`, `windmill`, `barn`, `lake(cx,cy,rx,ry)` (dock, rowboat empty "rowboat" with
    "rowboat_oar", waterfall at the far -y edge, ducks, ice-cream stand, danger sign), `sign(name,x,y,face,label)`,
    `kitchen(cx,cy)`, `bedroom(cx,cy)`, `office_safe(cx,cy)`, `room(...)`, `wall_planes(...)`, `point_light(...)`,
    `emissive(obj, strength)` (glowing -> bloom in style B)
  * blocks: `multibox(name, [(sx,sy,sz,cx,cy,cz,"#hex"[,rz])], parent, loc, rot_z)`, `poly`, `cyl`, `empty`, `text`,
    `house`, `fence`, `barrel`, `lamp`, `pole`, `wire`, `mat`. Style B automatically textures the standard palette.
  * Put interiors far away (e.g. y=+600 / -600 / x=+600) as their own little sets.
* `apply(stage, sh, t, gt)` hook (inside Blender): animate custom objects per frame (`stage.ob[name]`), move actors
  after posing (`stage.ob["pip_root"].location = ...`), `stage.set_face(n, expr)`. `t` = time in shot, `gt` = global.
* `cam_override(stage, sh, t, actors, T, f, u)` hook: return `(pos, look, lens)` to replace a camera.
* Import `mathutils` only inside hook functions (scene.py is also loaded by plain Python).
