$ErrorActionPreference = "Stop"
python -m unittest tools.test_performance_analytics_v77_61_to_v77_65 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_61_to_v77_65_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_61_to_v77_65_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.61-V77.65 PASS - READY TO COMMIT"
