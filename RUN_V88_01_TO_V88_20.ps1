$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v88_20\output"){Remove-Item "release\v88_20\output" -Recurse -Force}
Write-Host "=== V88.01-V88.20 INSTALL CHECK ==="
python tools/install_check_v88_01_to_v88_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.01-V88.20 TESTS ==="
python -m unittest tools.test_paper_scheduler_foundation_v88_01_to_v88_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.01-V88.20 PIPELINE ==="
python tools/run_v88_01_to_v88_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V88.01-V88.20 VERIFY ==="
python tools/verify_v88_01_to_v88_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V88.01-V88.20 PASS - READY TO COMMIT"
