$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v85_60\output"){Remove-Item "release\v85_60\output" -Recurse -Force}
Write-Host "=== V85.41-V85.60 INSTALL CHECK ==="
python tools/install_check_v85_41_to_v85_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.41-V85.60 TESTS ==="
python -m unittest tools.test_paper_order_authorization_v85_41_to_v85_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.41-V85.60 PIPELINE ==="
python tools/run_v85_41_to_v85_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.41-V85.60 VERIFY ==="
python tools/verify_v85_41_to_v85_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V85.41-V85.60 PASS - READY TO COMMIT"
