$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path 'release\v79_70\output'){Remove-Item 'release\v79_70\output' -Recurse -Force}
python tools/install_check_v79_66_to_v79_70.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_historical_indicator_library_v79_66_to_v79_70 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/run_v79_66_to_v79_70_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v79_66_to_v79_70_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V79.66-V79.70 PASS - READY TO COMMIT'
