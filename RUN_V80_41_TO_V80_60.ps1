$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v80_60\output"){Remove-Item "release\v80_60\output" -Recurse -Force}
Write-Host "=== V80.41-V80.60 INSTALL CHECK ==="
python tools/install_check_v80_41_to_v80_60.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.41-V80.60 TESTS ==="
python -m unittest tools.test_paper_monitoring_completion_v80_41_to_v80_60 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.41-V80.60 PIPELINE ==="
python tools/run_v80_41_to_v80_60_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.41-V80.60 VERIFY ==="
python tools/verify_v80_41_to_v80_60_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V80.41-V80.60 PASS - READY TO COMMIT"
