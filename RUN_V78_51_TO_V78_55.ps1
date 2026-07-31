$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_execution_coordinator_v78_51_to_v78_55 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_51_to_v78_55_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_51_to_v78_55_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.51-V78.55 PASS - READY TO COMMIT"
