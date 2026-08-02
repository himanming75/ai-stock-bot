$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP1.17-OP1.20 WINDOWS SCHEDULED READ-ONLY COLLECTION ==="
Write-Host "Builds and validates a Windows schedule plan only. It does not install the task."
python tools/run_windows_scheduled_read_only_collection_op1_17_to_op1_20.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP1.17-OP1.20 COMPLETE"
