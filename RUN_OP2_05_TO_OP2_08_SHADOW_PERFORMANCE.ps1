$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP2.05-OP2.08 SHADOW PERFORMANCE EVALUATION ==="
Write-Host "Local Shadow trade evaluation only. No broker network or orders."
python tools/run_shadow_performance_evaluation_op2_05_to_op2_08.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP2.05-OP2.08 COMPLETE"
