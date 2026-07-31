$ErrorActionPreference = "Stop"
python -m unittest tools.test_backtesting_integration_v77_46_to_v77_50 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_46_to_v77_50_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_46_to_v77_50_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.46-V77.50 PASS - READY TO COMMIT"
