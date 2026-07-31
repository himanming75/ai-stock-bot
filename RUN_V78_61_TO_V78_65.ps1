$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_fill_portfolio_bridge_v78_61_to_v78_65 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_61_to_v78_65_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_61_to_v78_65_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.61-V78.65 PASS - READY TO COMMIT"
