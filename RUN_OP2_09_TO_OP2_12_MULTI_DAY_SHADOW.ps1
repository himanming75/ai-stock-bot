$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP2.09-OP2.12 MULTI-DAY SHADOW VALIDATION ==="
Write-Host "Local multi-day Shadow validation only. No broker network or orders."
python tools/run_multi_day_shadow_validation_op2_09_to_op2_12.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP2.09-OP2.12 COMPLETE"
