$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path 'release\v79_85\output'){Remove-Item 'release\v79_85\output' -Recurse -Force}
python tools/install_check_v79_81_to_v79_85.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_historical_risk_engine_v79_81_to_v79_85 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/run_v79_81_to_v79_85_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v79_81_to_v79_85_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V79.81-V79.85 PASS - READY TO COMMIT'
