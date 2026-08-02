$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP1.09-OP1.12 WEEKLY OBSERVATION REVIEW ==="
Write-Host "Local weekly review only. No broker network and no orders."
python tools/run_weekly_observation_review_op1_09_to_op1_12.py --repository-root .
if ($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP1.09-OP1.12 COMPLETE"
