$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v85_20\output"){Remove-Item "release\v85_20\output" -Recurse -Force}
Write-Host "=== V85.01-V85.20 INSTALL CHECK ==="
python tools/install_check_v85_01_to_v85_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.01-V85.20 TESTS ==="
python -m unittest tools.test_paper_broker_network_foundation_v85_01_to_v85_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.01-V85.20 PIPELINE ==="
python tools/run_v85_01_to_v85_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V85.01-V85.20 VERIFY ==="
python tools/verify_v85_01_to_v85_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V85.01-V85.20 PASS - READY TO COMMIT"
