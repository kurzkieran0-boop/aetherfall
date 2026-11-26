SIX STORY VIDEOS - render on your Windows 11 PC
================================================

What is in this folder
  run_all.ps1      the one command (installs tools, renders, assembles, verifies, prints the table)
  kit\             shared kit: Blender town/avatars/counters, TTS wrapper, shot planner, renderer, ffmpeg assembler, verify
  <slug>\          one folder per video: config.py, story.py (verbatim script + shot beats), scene.py (set dressing),
                   shots.json (every shot: duration, location, characters, camera move, emotion, caption words),
                   script.txt, build\timeline.json (word timestamps), build\voice.flac (narration), build\test_still\
  videos: quiet_rule, mailman, five_thousand_words, thousand_bites, two_thousand_doors, three_thousand_hours

Steps
  1. Unzip videos_package.zip anywhere, e.g. C:\stories  (you get C:\stories\videos\...)
  2. Open PowerShell in that folder:  in File Explorer open C:\stories\videos, click the address bar, type
     powershell  and press Enter.
  3. Quick check of all six first (540x960, minimum samples, ~30-60 min on a GPU):
        powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -Preview
     -> each folder gets final_preview.mp4 + contact_sheet_preview.png + sync_check_preview.png
  4. Full render (1080x1920, 30 fps):
        powershell -ExecutionPolicy Bypass -File .\run_all.ps1
     -> each folder gets final.mp4 + contact_sheet.png + sync_check.png, then a table is printed:
        path, duration, shot count, words per second, flaws
  One video only:   powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -Only mailman
  Check without rendering:   powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -DryRun

What run_all.ps1 does
  * installs anything missing, silently: Python 3, ffmpeg, Blender (winget) and the pip packages
    (numpy, pillow, piper-tts, faster-whisper, edge-tts). The first run needs internet.
  * prints the GPU Blender picked (OPTIX, then CUDA, then HIP, then METAL, else CPU). Eevee renders on the GPU.
  * narration is already included (build\voice.flac + timeline.json). It is only regenerated if you edit a
    story.py or the voice settings in config.py (then Piper voices are downloaded automatically).
  * renders every shot, one Blender render at a time, shortest video first. It is resume-safe: stop it any time
    (Ctrl+C or close the window) and run the same command again - finished shots are skipped.
  * assembles each video with ffmpeg (captions burned in, ambient bed, whooshes, heartbeat, stone thuds) and runs
    the checklist (kit\verify.py): duration >= 2:15, 1080x1920, 30 fps, audio, words/sec in range, no silence over
    0.4 s, no frozen/repeated footage, no black frames mid-video (except the intentional blind scenes in
    three_thousand_hours), >= 80 shots (90 for mailman), none over 3 s, counters match the spoken countdown numbers,
    one caption per spoken word.
  * progress is kept in videos\progress.json and videos\<slug>\status.json.

Expected time (27,309 frames in total, 1080x1920, Eevee 8 samples)
  * typical gaming GPU (RTX 3060 / RX 6700 class, ~0.3-0.5 s per frame): about 2.5-4 hours for all six.
    -Preview (540x960, 1 sample, 15 fps doubled to 30): about 30-45 minutes for all six.
  * this build machine (4-core CPU, no GPU, ~2.8 s per frame): about 21 hours. Use the GPU.

If something fails
  * "winget is not available": install "App Installer" from the Microsoft Store and re-run.
  * a tool was just installed but is "not found": close PowerShell, open a new one, run the command again.
  * Blender somewhere unusual:  .\run_all.ps1 -Blender "D:\Blender\blender.exe"
  * logs: videos\<slug>\build\render_progress.log
