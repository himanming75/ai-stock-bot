$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v86_60\output"){Remove-Item "release\v86_60\output" -Recurse -Force}
Write-Host "=== V86.41-V86.60 INSTALL CHECK ==="
python tools/install_check_v86_41_to_v86_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.41-V86.60 TESTS ==="
python -m unittest tools.test_position_account_reconciliation_v86_41_to_v86_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.41-V86.60 PIPELINE (OFFLINE SAFE DEFAULT) ==="
python tools/run_v86_41_to_v86_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V86.41-V86.60 VERIFY ==="
python tools/verify_v86_41_to_v86_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V86.41-V86.60 PASS - READY TO COMMIT"
