$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_monte_carlo_v77_81_to_v77_85 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v77_81_to_v77_85_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v77_81_to_v77_85_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.81-V77.85 PASS - READY TO COMMIT"
