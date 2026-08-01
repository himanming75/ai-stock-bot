$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path 'release\v79_75\output'){Remove-Item 'release\v79_75\output' -Recurse -Force}
python tools/install_check_v79_71_to_v79_75.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_historical_signal_engine_v79_71_to_v79_75 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/run_v79_71_to_v79_75_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v79_71_to_v79_75_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V79.71-V79.75 PASS - READY TO COMMIT'
