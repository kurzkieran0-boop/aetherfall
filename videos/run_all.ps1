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
    $global:LASTEXITCODE = 0
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

function Get-PortableBlender {
    # winget's download can be refused by Blender's server (403); fetch the portable zip like a browser instead
    $dest = Join-Path $Videos "_blender"
    $exe = Get-ChildItem -Path $dest -Filter blender.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($exe) { return $exe.FullName }
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $zip = Join-Path $dest "blender.zip"
    $ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    $names = @("Blender5.3/blender-5.3.0-windows-x64.zip", "Blender5.2/blender-5.2.0-windows-x64.zip", "Blender5.1/blender-5.1.0-windows-x64.zip")
    $hosts = @("https://download.blender.org/release/", "https://mirrors.ocf.berkeley.edu/blender/release/", "https://ftp.nluug.nl/pub/graphics/blender/release/")
    $ProgressPreference = "SilentlyContinue"
    foreach ($n in $names) { foreach ($h in $hosts) {
        try {
            Write-Host "   trying $h$n"
            Invoke-WebRequest -Uri "$h$n" -OutFile $zip -UserAgent $ua -UseBasicParsing
            Expand-Archive -Path $zip -DestinationPath $dest -Force
            Remove-Item $zip -ErrorAction SilentlyContinue
            $exe = Get-ChildItem -Path $dest -Filter blender.exe -Recurse | Select-Object -First 1
            if ($exe) { return $exe.FullName }
        } catch { Write-Host "   (not available: $($_.Exception.Message))" }
    } }
    return $null
}

$bl = Find-Blender
if (-not $bl) { try { Ensure-Winget "BlenderFoundation.Blender" "" } catch { Write-Host "winget Blender install failed: $_" }; $bl = Find-Blender }
if (-not $bl) { Write-Host "== downloading portable Blender" -ForegroundColor Cyan; $bl = Get-PortableBlender }
if (-not $bl) { throw "Blender could not be installed automatically. Install it from https://www.blender.org/download/ (normal installer), then run this command again." }
Write-Host "blender: $bl"

Write-Host "== python packages" -ForegroundColor Cyan
& $py -m pip install --quiet --disable-pip-version-check --upgrade pip | Out-Null
& $py -m pip install --quiet --disable-pip-version-check numpy pillow
if ($LASTEXITCODE -ne 0) { throw "pip install of numpy/pillow failed" }
# speech tools are only needed if a story is edited (the narration ships in the package) - never fatal
foreach ($pkg in @("piper-tts", "faster-whisper", "edge-tts")) {
    & $py -m pip install --quiet --disable-pip-version-check $pkg 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "   (optional $pkg not installed for this Python; only needed to regenerate narration)" -ForegroundColor DarkYellow }
}

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
