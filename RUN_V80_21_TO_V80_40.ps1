$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v80_40\output"){Remove-Item "release\v80_40\output" -Recurse -Force}
Write-Host "=== V80.21-V80.40 INSTALL CHECK ==="
python tools/install_check_v80_21_to_v80_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.21-V80.40 TESTS ==="
python -m unittest tools.test_paper_order_fill_engine_v80_21_to_v80_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.21-V80.40 PIPELINE ==="
python tools/run_v80_21_to_v80_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.21-V80.40 VERIFY ==="
python tools/verify_v80_21_to_v80_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V80.21-V80.40 PASS - READY TO COMMIT"
