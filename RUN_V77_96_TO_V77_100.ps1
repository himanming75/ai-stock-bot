$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_broker_integration_v77_96_to_v77_100 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v77_96_to_v77_100_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v77_96_to_v77_100_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V77.96-V77.100 PASS - READY TO COMMIT"
