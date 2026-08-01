$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v84_40\output"){Remove-Item "release\v84_40\output" -Recurse -Force}
Write-Host "=== V84.21-V84.40 INSTALL CHECK ==="
python tools/install_check_v84_21_to_v84_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.21-V84.40 TESTS ==="
python -m unittest tools.test_live_order_gate_v84_21_to_v84_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.21-V84.40 PIPELINE ==="
python tools/run_v84_21_to_v84_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V84.21-V84.40 VERIFY ==="
python tools/verify_v84_21_to_v84_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V84.21-V84.40 PASS - READY TO COMMIT"
