$ErrorActionPreference = "Stop"
python -m unittest tools.test_scheduled_runtime_v77_21_to_v77_25 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_21_to_v77_25_pipeline.py --repository-root . --clean --run-count 5 --interval-seconds 60
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_21_to_v77_25_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.21-V77.25 PASS - READY TO COMMIT"
