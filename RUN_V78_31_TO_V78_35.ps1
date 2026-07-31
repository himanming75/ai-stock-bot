$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_market_data_v78_31_to_v78_35 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_31_to_v78_35_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_31_to_v78_35_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.31-V78.35 PASS - READY TO COMMIT"
