$ErrorActionPreference = "Stop"
python -m unittest tools.test_portfolio_management_v77_41_to_v77_45 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_41_to_v77_45_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_41_to_v77_45_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.41-V77.45 PASS - READY TO COMMIT"
