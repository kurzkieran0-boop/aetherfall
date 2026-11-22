# Paper Lantern Tales — 3D brick-city monster films

One command turns an idea into a finished, standalone 60–120 s vertical film
(1080×1920, 24 fps): blocky toy-brick characters, a night city at huge scale, and
an original giant monster that obeys one simple rule.

```bash
python make_film.py "surprise me"
python make_film.py "a monster that can't cross water"
python make_film.py "lights out" --stop-after stills     # review the contact sheet first
python make_film.py "lights out"                         # resumes, renders finals
python make_film.py "lights out" --redo-shots s012,s013  # re-render only those shots
```

Output goes to `output/<title>/`:

| File | What it is |
|---|---|
| `film.mp4` | final film, H.264 + AAC, loudness-normalised to −14 LUFS |
| `story.md` | story bible: 10 scored premises, characters, monster, outline, draft, critique, rewrite |
| `script.md` | final timed script |
| `shotlist.json` | camera plan per shot (move, framing, angle, lens, subjects) plus the full shot spec |
| `contact_sheet.png`, `qa.json` | one 540×960 still per shot and automated QA flags |
| `thumbnail.jpg`, `metadata.json/.txt` | title, TikTok caption, YouTube Shorts title, description and hashtags |
| `credits.txt` | every third-party asset (all CC0) |

Nothing is posted or uploaded anywhere.

## Stages (each one is cached and resumable)

1. **setup**: checks ffmpeg, Blender and Python packages, installs whatever is
   missing, and fetches CC0 HDRIs (Poly Haven) and PBR textures (ambientCG) into
   `assets/`. Blender can be the installed binary (`winget install
   BlenderFoundation.Blender`, run as `blender -b -P`) or the `bpy` pip module.
2. **story**: brainstorms 10 premises, scores them, picks one, outlines, drafts,
   critiques and rewrites. Authored films live in `stories/*.py`. A new idea uses
   the free local LLM when Ollama is installed, otherwise the built-in rule-archetype
   template writer.
3. **voice**: Piper neural TTS. The narrator is pitched down; each character has
   a distinct voice. Real line lengths drive every cut.
4. **stills**: preview pass at 540×960 with one still per shot. Builds the contact
   sheet and flags shots that are dark, clipping, crushed, flat, muddy, cut too
   short or too long, or static.
5. **final**: parallel Blender processes, hash-cached per shot. It prints the time
   per shot and steps quality down automatically when a shot runs over budget.
   * GPU (OptiX/CUDA/HIP/Metal detected): native 1080×1920, every frame, 16 samples.
   * CPU only: 432×768 rendered on twos (brick-film cadence), upscaled in compose.
6. **audio**: procedural score that follows the tension curve, with risers,
   hits, braams, drops and a major-key resolve. SFX are timed from render events
   (footfalls, roars, whip pans) and scripted cues (sirens, thunder, steam,
   splash). Rain and city ambience beds, voice ducking, then two-pass ffmpeg
   `loudnorm`.
7. **captions**: faster-whisper word timestamps aligned to the script, shown
   1–2 words at a time in big yellow type with a thick outline and a pop-in.
   Placement avoids faces and the monster's head, using screen boxes exported
   from Blender.
8. **compose**: grade per look, vignette, film grain, impact flashes, captions,
   then mux.
9. **deliver**: ffprobe checks (60–120 s, 1080×1920, 24 fps), thumbnail and
   metadata.

## Kit (`pipeline/blender/kit.py`)

* **Sets:** `city_block` (street grid of lit skyscrapers with a central boulevard,
  wet PBR roads, skyline), `plaza` (canal and bridge, floodlights), `rooftop`,
  `subway`, `school`, `forest`, `lab`, `bunker`.
* **Props:** police car (flashing bar plus real red/blue lights), fire truck,
  sedan, barrier, floodlight tower, fence, crane, pylon, streetlamp, water tank,
  crates, trees, rubble.
* **Characters:** blocky rigs with brows, eyes, pupils and mouth expressions
  (neutral, fear, shock, determined, angry, happy, sad, sly, scream). The action
  library covers idle, walk, run, panic_run, sneak, panic, look_up, point, fall,
  hide, grab, climb, turn, gasp, freeze, shush, cheer, kneel and talk, with
  anticipation, overshoot and follow-through.
* **Monsters:** `colossus` (biped), `stalker` (eyeless quadruped) and `warden`
  (tall statue), with glowing fissure skin and eye and rim lights. Actions are
  walk (footfall impacts), roar, stomp, swipe, reach, freeze, lurk, collapse and
  dissolve. Impacts trigger camera shake, debris bursts and volumetric dust.
* **FX:** rain, embers, dust motes, leaves, ash, sparks, hydrant spray,
  lightning, blackout and city power cuts, flicker, flood, steam and fog banks.
* **Camera** (`camera.py`): described the way a DP talks: subject, framing
  (ECU–EWS), angle (worm–top), lens, and a move (push-in, pull-out, orbit,
  crane, tilt reveal, whip pan, dolly, drone orbit, track, POV, OTS, rack focus,
  dolly zoom, handheld). Ray casts swing the camera around buildings that block
  the subject.

## Speed notes

Rendering here ran on a 4-core cloud container with no GPU, using software GL
(llvmpipe). Eevee's per-frame cost there is dominated by shadow maps, so only
the key, rim, floodlight and monster lights cast shadows. On a desktop GPU,
expect each shot to render in seconds.

## Credits / licences

All textures and HDRIs are CC0. Music and SFX are synthesised in
`pipeline/audio.py`, with no samples. Voices come from Piper (see each voice's
model card). The font is Inter (OFL). See `assets/credits.txt`.
