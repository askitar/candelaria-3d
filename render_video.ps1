# Renders the La Candelaria drone flight: Blender (EEVEE) frames, then an H.264 video with ffmpeg.
# Usage:  powershell -ExecutionPolicy Bypass -File render_video.ps1 [-Start 1] [-End 0] [-Nombre La_Candelaria_dron] [-Blender "path\to\blender.exe"]
param([int]$Start = 0, [int]$End = 0, [string]$Nombre = 'La_Candelaria_dron', [int]$Fps = 30,
      [string]$Blender = $(if ($env:BLENDER_EXE) { $env:BLENDER_EXE } else { 'blender' }))

$proj = $PSScriptRoot
$frames = Join-Path $proj 'render\frames'
$log = Join-Path $proj 'render\render.log'
$out = Join-Path $proj ("render\" + $Nombre + ".mp4")
New-Item -ItemType Directory -Force $frames | Out-Null

$t0 = Get-Date
$argsB = @('-b', (Join-Path $proj 'candelaria.blend'))
if ($Start -gt 0) { $argsB += @('-s', "$Start") }
if ($End -gt 0) { $argsB += @('-e', "$End") }
$argsB += '-a'
& $Blender @argsB *> $log
$n = (Get-ChildItem $frames -Filter 'dron_*.png' -ErrorAction SilentlyContinue | Measure-Object).Count
"Frames rendered: $n in $([math]::Round(((Get-Date) - $t0).TotalMinutes, 1)) min"

if ($n -gt 10) {
    $first = (Get-ChildItem $frames -Filter 'dron_*.png' | Sort-Object Name | Select-Object -First 1).BaseName -replace 'dron_', ''
    & ffmpeg -hide_banner -loglevel error -y -framerate $Fps -start_number ([int]$first) -i (Join-Path $frames 'dron_%04d.png') `
        -vf "noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset slow -crf 15 -movflags +faststart $out
    if (Test-Path $out) { "Video: $out ($([math]::Round((Get-Item $out).Length / 1MB, 1)) MB)" } else { "ERROR: ffmpeg did not produce the video" }
} else {
    "ERROR: not enough frames, check $log"
}
[console]::beep(880, 600); [console]::beep(1175, 800)
"DONE $(Get-Date -Format 'HH:mm:ss')"
