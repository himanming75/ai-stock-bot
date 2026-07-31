$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_event_bus_v78_11_to_v78_15 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_11_to_v78_15_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_11_to_v78_15_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.11-V78.15 PASS - READY TO COMMIT"
