$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op1_17_to_op1_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_windows_scheduled_read_only_collection_op1_17_to_op1_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP1_17_TO_OP1_20_WINDOWS_SCHEDULE_PLAN.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_windows_scheduled_read_only_collection_op1_17_to_op1_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP1.17-OP1.20 TEST AND VERIFY PASS"
