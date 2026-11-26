<#
  run_all.ps1 - render all six story videos on this Windows PC with ONE command:

      powershell -ExecutionPolicy Bypass -File .\run_all.ps1
      powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -Preview            # 540x960, minimum samples, quick check
      powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -Only mailman       # one video
      powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -DryRun             # everything except the real render

  What it does: installs missing tools silently (winget: Python 3, ffmpeg, Blender; pip: the kit's packages incl.
  edge-tts), detects the GPU inside Blender (OPTIX > CUDA > HIP > METAL > CPU), regenerates TTS only if missing or
  the story changed, renders every shot resume-safe (already rendered shots are skipped), one Blender render at a
  time, shortest video first, assembles with ffmpeg (captions burned in), verifies each final.mp4 and prints a table.
  Safe to stop and re-run at any time: it continues where it left off.
#>
param(
    [switch]$Preview,
    [string]$Only = "",
    [switch]$DryRun,
    [string]$Blender = ""
)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$Videos = $PSScriptRoot
if (Test-Path (Join-Path $PSScriptRoot "videos\kit")) { $Videos = Join-Path $PSScriptRoot "videos" }   # zip root
Set-Location -Path $Videos

function Refresh-Path {
    $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $u = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$m;$u"
}

function Ensure-Winget([string]$id, [string]$probe) {
    if ($probe -and (Get-Command $probe -ErrorAction SilentlyContinue)) { return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is not available. Install 'App Installer' from the Microsoft Store, then re-run."
    }
    Write-Host "== installing $id (silent)" -ForegroundColor Cyan
    winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-Path
}

function Find-Python {
    foreach ($c in @("py -3.13", "py -3.12", "py -3.11", "py -3", "python")) {
        $exe, $arg = $c.Split(" ", 2)
        if (Get-Command $exe -ErrorAction SilentlyContinue) {
            try {
                $v = & $exe $arg -c "import sys; print(sys.executable)" 2>$null
                if ($LASTEXITCODE -eq 0 -and $v -and ($v -notmatch "WindowsApps")) { return $v.Trim() }
            } catch {}
        }
    }
    return $null
}

function Find-Blender {
    if ($Blender -and (Test-Path $Blender)) { return $Blender }
    $cmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @("$env:ProgramFiles\Blender Foundation", "${env:ProgramFiles(x86)}\Blender Foundation", "$env:LOCALAPPDATA\Programs\Blender Foundation")
    foreach ($r in $roots) {
        if (Test-Path $r) {
            $b = Get-ChildItem -Path $r -Filter blender.exe -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | Select-Object -First 1
            if ($b) { return $b.FullName }
        }
    }
    return $null
}

# ---------------------------------------------------------------- tools
Refresh-Path
$py = Find-Python
if (-not $py) { Ensure-Winget "Python.Python.3.13" ""; $py = Find-Python }
if (-not $py) { throw "Python 3 not found after install. Open a new PowerShell window and re-run." }
Write-Host "python : $py"

Ensure-Winget "Gyan.FFmpeg" "ffmpeg"
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    $ff = Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ff) { $env:Path = "$($ff.DirectoryName);$env:Path" }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { throw "ffmpeg not found after install. Open a new PowerShell window and re-run." }
Write-Host "ffmpeg : $((Get-Command ffmpeg).Source)"

$bl = Find-Blender
if (-not $bl) { Ensure-Winget "BlenderFoundation.Blender" ""; $bl = Find-Blender }
if (-not $bl) { throw "Blender not found after install. Pass -Blender C:\path\to\blender.exe" }
Write-Host "blender: $bl"

Write-Host "== python packages" -ForegroundColor Cyan
& $py -m pip install --quiet --disable-pip-version-check --upgrade pip | Out-Null
& $py -m pip install --quiet --disable-pip-version-check numpy pillow piper-tts faster-whisper edge-tts
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# ---------------------------------------------------------------- GPU report (the renderer also sets it per run)
Write-Host "== GPU detection in Blender" -ForegroundColor Cyan
& $bl -b --factory-startup --python-expr "import sys; sys.path.insert(0, r'$Videos\kit'); import kit_gpu; kit_gpu.setup()" 2>&1 |
    Select-String "\[gpu\]" | ForEach-Object { Write-Host $_.Line -ForegroundColor Green }

# ---------------------------------------------------------------- pipeline
$env:PYTHONUTF8 = "1"
$env:KIT_CONCURRENCY = "1"
$argsList = @("kit\run_all.py", "--blender", $bl)
if ($Preview) { $argsList += "--preview" }
if ($DryRun)  { $argsList += "--dry-run" }
if ($Only)    { $argsList += @("--only", $Only) }
$t0 = Get-Date
& $py @argsList
$code = $LASTEXITCODE
Write-Host ("finished in {0:N1} min (exit {1})" -f ((Get-Date) - $t0).TotalMinutes, $code)
exit $code
