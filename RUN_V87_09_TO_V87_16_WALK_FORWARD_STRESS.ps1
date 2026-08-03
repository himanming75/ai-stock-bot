$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V87.09-V87.16 WALK-FORWARD AND STRESS VALIDATION ==="
Write-Host "Local robustness validation only. No API, network, broker write, or order submission."

python tools\run_walk_forward_stress_v87_09_to_v87_16.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V87.09-V87.16 COMPLETE"
