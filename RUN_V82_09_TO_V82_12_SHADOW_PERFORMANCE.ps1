
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.09-V82.12 SHADOW PERFORMANCE ANALYTICS ==="
Write-Host "Local analytics only. No network or broker orders."

python tools/run_shadow_performance_v82_09_to_v82_12.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.09-V82.12 COMPLETE"
