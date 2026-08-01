$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v82_00\output"){Remove-Item "release\v82_00\output" -Recurse -Force}
Write-Host "=== V81.81-V82.00 INSTALL CHECK ==="
python tools/install_check_v81_81_to_v82_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.81-V82.00 TESTS ==="
python -m unittest tools.test_paper_performance_analytics_v81_81_to_v82_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.81-V82.00 PIPELINE ==="
python tools/run_v81_81_to_v82_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.81-V82.00 VERIFY ==="
python tools/verify_v81_81_to_v82_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.81-V82.00 PASS - READY TO COMMIT"
