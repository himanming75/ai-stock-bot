$ErrorActionPreference = "Stop"
python -m unittest tools.test_strategy_optimization_v77_71_to_v77_75 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_71_to_v77_75_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_71_to_v77_75_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.71-V77.75 PASS - READY TO COMMIT"
