$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path 'release\v79_80\output'){Remove-Item 'release\v79_80\output' -Recurse -Force}
python tools/install_check_v79_76_to_v79_80.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_historical_portfolio_simulation_v79_76_to_v79_80 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/run_v79_76_to_v79_80_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v79_76_to_v79_80_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V79.76-V79.80 PASS - READY TO COMMIT'
