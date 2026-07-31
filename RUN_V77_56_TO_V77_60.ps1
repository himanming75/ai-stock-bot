$ErrorActionPreference = "Stop"
python -m unittest tools.test_portfolio_reconciliation_v77_56_to_v77_60 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_56_to_v77_60_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_56_to_v77_60_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.56-V77.60 PASS - READY TO COMMIT"
