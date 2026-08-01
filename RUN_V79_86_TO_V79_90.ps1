$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path 'release\v79_90\output'){Remove-Item 'release\v79_90\output' -Recurse -Force}
python tools/install_check_v79_86_to_v79_90.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python -m unittest tools.test_historical_performance_analytics_v79_86_to_v79_90 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/run_v79_86_to_v79_90_pipeline.py --repository-root . --clean
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v79_86_to_v79_90_pipeline.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host 'V79.86-V79.90 PASS - READY TO COMMIT'
