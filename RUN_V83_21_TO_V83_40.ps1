$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v83_40\output"){Remove-Item "release\v83_40\output" -Recurse -Force}
Write-Host "=== V83.21-V83.40 INSTALL CHECK ==="
python tools/install_check_v83_21_to_v83_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.21-V83.40 TESTS ==="
python -m unittest tools.test_paper_order_authorization_v83_21_to_v83_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.21-V83.40 PIPELINE ==="
python tools/run_v83_21_to_v83_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V83.21-V83.40 VERIFY ==="
python tools/verify_v83_21_to_v83_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V83.21-V83.40 PASS - READY TO COMMIT"
