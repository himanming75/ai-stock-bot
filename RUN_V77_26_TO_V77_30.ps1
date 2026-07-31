$ErrorActionPreference = "Stop"
python -m unittest tools.test_market_data_v77_26_to_v77_30 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_26_to_v77_30_pipeline.py --repository-root . --clean --symbol SPY --bar-count 30 --interval-seconds 60
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_26_to_v77_30_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.26-V77.30 PASS - READY TO COMMIT"
