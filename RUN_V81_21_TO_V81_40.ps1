$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v81_40\output"){Remove-Item "release\v81_40\output" -Recurse -Force}
Write-Host "=== V81.21-V81.40 INSTALL CHECK ==="
python tools/install_check_v81_21_to_v81_40.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.21-V81.40 TESTS ==="
python -m unittest tools.test_multi_asset_portfolio_v81_21_to_v81_40 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.21-V81.40 PIPELINE ==="
python tools/run_v81_21_to_v81_40_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "=== V81.21-V81.40 VERIFY ==="
python tools/verify_v81_21_to_v81_40_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V81.21-V81.40 PASS - READY TO COMMIT"
