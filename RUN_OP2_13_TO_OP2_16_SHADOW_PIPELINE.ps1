$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP2.13-OP2.16 AUTOMATIC SHADOW SIGNAL PIPELINE ==="
Write-Host "Local automatic Shadow signal generation and queue only. No broker network or orders."
python tools/run_automatic_shadow_signal_pipeline_op2_13_to_op2_16.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP2.13-OP2.16 COMPLETE"
