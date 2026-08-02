$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP1.05-OP1.08 DAILY READ-ONLY OBSERVATION ==="
Write-Host "Local snapshot comparison only. No broker network and no orders."
python tools/run_daily_read_only_observation_op1_05_to_op1_08.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "OP1.05-OP1.08 COMPLETE"
