$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python tools/install_check_op1_13_to_op1_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_automatic_snapshot_collector_op1_13_to_op1_16 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
powershell -ExecutionPolicy Bypass -File .\RUN_OP1_13_TO_OP1_16_SNAPSHOT_COLLECTOR.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_automatic_snapshot_collector_op1_13_to_op1_16.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP1.13-OP1.16 TEST AND VERIFY PASS"
