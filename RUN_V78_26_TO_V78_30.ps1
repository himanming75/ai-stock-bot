$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_market_clock_v78_26_to_v78_30 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_26_to_v78_30_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_26_to_v78_30_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.26-V78.30 PASS - READY TO COMMIT"
