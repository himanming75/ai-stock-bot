$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v80_20\output"){Remove-Item "release\v80_20\output" -Recurse -Force}
Write-Host "=== V80.06-V80.20 INSTALL CHECK ==="
python tools/install_check_v80_06_to_v80_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.06-V80.20 TESTS ==="
python -m unittest tools.test_paper_session_engine_v80_06_to_v80_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.06-V80.20 PIPELINE ==="
python tools/run_v80_06_to_v80_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.06-V80.20 VERIFY ==="
python tools/verify_v80_06_to_v80_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V80.06-V80.20 PASS - READY TO COMMIT"
