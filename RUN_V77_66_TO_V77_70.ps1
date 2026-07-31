$ErrorActionPreference = "Stop"
python -m unittest tools.test_reporting_v77_66_to_v77_70 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_66_to_v77_70_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_66_to_v77_70_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.66-V77.70 PASS - READY TO COMMIT"
