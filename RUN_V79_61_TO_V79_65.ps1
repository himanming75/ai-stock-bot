$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path 'release\v79_65\output'){Remove-Item 'release\v79_65\output' -Recurse -Force}
python tools/install_check_v79_61_to_v79_65.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_historical_feature_store_v79_61_to_v79_65 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/run_v79_61_to_v79_65_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v79_61_to_v79_65_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V79.61-V79.65 PASS - READY TO COMMIT'
