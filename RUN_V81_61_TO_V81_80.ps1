$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v81_80\output"){Remove-Item "release\v81_80\output" -Recurse -Force}
Write-Host "=== V81.61-V81.80 INSTALL CHECK ==="
python tools/install_check_v81_61_to_v81_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.61-V81.80 TESTS ==="
python -m unittest tools.test_execution_simulation_v81_61_to_v81_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.61-V81.80 PIPELINE ==="
python tools/run_v81_61_to_v81_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.61-V81.80 VERIFY ==="
python tools/verify_v81_61_to_v81_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.61-V81.80 PASS - READY TO COMMIT"
