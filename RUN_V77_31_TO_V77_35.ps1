$ErrorActionPreference = "Stop"
python -m unittest tools.test_strategy_input_v77_31_to_v77_35 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_31_to_v77_35_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_31_to_v77_35_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.31-V77.35 PASS - READY TO COMMIT"
