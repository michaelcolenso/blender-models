$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Find-Blender {
    if ($env:BLENDER_BIN -and (Test-Path $env:BLENDER_BIN)) { return $env:BLENDER_BIN }
    $cmd = Get-Command blender -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $base = Join-Path $env:ProgramFiles "Blender Foundation"
    if (Test-Path $base) {
        $found = Get-ChildItem $base -Directory | Sort-Object Name -Descending | ForEach-Object {
            $p = Join-Path $_.FullName "blender.exe"
            if (Test-Path $p) { $p }
        } | Select-Object -First 1
        if ($found) { return $found }
    }
    return $null
}

$Blender = Find-Blender
if (-not $Blender) { throw "Blender executable not found. Set BLENDER_BIN to blender.exe and rerun." }

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    & $Python.Source (Join-Path $Root "scripts\preflight.py") | Tee-Object -FilePath (Join-Path $Root "logs\preflight.log")
} else {
    & $Blender --background --factory-startup --python (Join-Path $Root "scripts\preflight.py") 2>&1 | Tee-Object -FilePath (Join-Path $Root "logs\preflight.log")
}
if ($LASTEXITCODE -ne 0) { throw "Preflight failed." }

Write-Host "Using Blender: $Blender"
& $Blender --version | Select-Object -First 3 | Tee-Object -FilePath (Join-Path $Root "logs\blender_version.log")

$extra = $args
& $Blender --background --factory-startup --python (Join-Path $Root "scripts\run_build_and_verify.py") -- --fail-on-warning @extra 2>&1 |
    Tee-Object -FilePath (Join-Path $Root "logs\build.log")
if ($LASTEXITCODE -ne 0) { throw "Blender build/validation failed. See logs\build.log" }

$Blend = Join-Path $Root "output\Meydenbauer_B101_Demolition_v4.blend"
& $Blender --background $Blend --python (Join-Path $Root "scripts\verify_saved_blend.py") -- --fail-on-warning 2>&1 |
    Tee-Object -FilePath (Join-Path $Root "logs\verify_saved_blend.log")
if ($LASTEXITCODE -ne 0) { throw "Saved-blend verification failed. See logs\verify_saved_blend.log" }

Write-Host ""
Write-Host "Handoff verification complete."
Write-Host "Blend:   $Blend"
Write-Host "Reports: $(Join-Path $Root 'output\build_validation_report.json')"
Write-Host "         $(Join-Path $Root 'output\saved_blend_verification.json')"
