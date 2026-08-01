$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v81_20\output"){Remove-Item "release\v81_20\output" -Recurse -Force}
Write-Host "=== V81.01-V81.20 INSTALL CHECK ==="
python tools/install_check_v81_01_to_v81_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.01-V81.20 TESTS ==="
python -m unittest tools.test_portfolio_optimization_v81_01_to_v81_20 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.01-V81.20 PIPELINE ==="
python tools/run_v81_01_to_v81_20_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.01-V81.20 VERIFY ==="
python tools/verify_v81_01_to_v81_20_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.01-V81.20 PASS - READY TO COMMIT"
