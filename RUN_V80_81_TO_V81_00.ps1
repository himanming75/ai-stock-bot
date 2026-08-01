$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v81_00\output"){Remove-Item "release\v81_00\output" -Recurse -Force}
Write-Host "=== V80.81-V81.00 INSTALL CHECK ==="
python tools/install_check_v80_81_to_v81_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.81-V81.00 TESTS ==="
python -m unittest tools.test_strategy_selection_v80_81_to_v81_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.81-V81.00 PIPELINE ==="
python tools/run_v80_81_to_v81_00_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V80.81-V81.00 VERIFY ==="
python tools/verify_v80_81_to_v81_00_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V80.81-V81.00 PASS - READY TO COMMIT"
