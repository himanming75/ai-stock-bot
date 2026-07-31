$ErrorActionPreference = "Stop"
python -m unittest tools.test_recovery_release_v77_11_to_v77_15 -v
python tools\run_v77_11_to_v77_15_pipeline.py --repository-root . --clean
python tools\verify_v77_11_to_v77_15_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.11-V77.15 PASS - READY TO COMMIT"
