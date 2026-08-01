$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v85_40\output"){Remove-Item "release\v85_40\output" -Recurse -Force}
Write-Host "=== V85.21-V85.40 INSTALL CHECK ==="
python tools/install_check_v85_21_to_v85_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.21-V85.40 TESTS ==="
python -m unittest tools.test_paper_broker_read_only_v85_21_to_v85_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.21-V85.40 PIPELINE (OFFLINE SAFE DEFAULT) ==="
python tools/run_v85_21_to_v85_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.21-V85.40 VERIFY ==="
python tools/verify_v85_21_to_v85_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V85.21-V85.40 PASS - READY TO COMMIT"
