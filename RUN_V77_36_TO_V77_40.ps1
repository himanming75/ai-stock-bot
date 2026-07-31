$ErrorActionPreference = "Stop"
python -m unittest tools.test_risk_management_v77_36_to_v77_40 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\run_v77_36_to_v77_40_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools\verify_v77_36_to_v77_40_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.36-V77.40 PASS - READY TO COMMIT"
