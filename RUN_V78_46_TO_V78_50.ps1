$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_portfolio_runtime_v78_46_to_v78_50 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_46_to_v78_50_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_46_to_v78_50_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.46-V78.50 PASS - READY TO COMMIT"
