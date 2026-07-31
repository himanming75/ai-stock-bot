$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_live_readiness_v77_91_to_v77_95 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v77_91_to_v77_95_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v77_91_to_v77_95_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.91-V77.95 PASS - READY TO COMMIT"
