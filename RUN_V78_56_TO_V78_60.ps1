$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_paper_broker_integration_v78_56_to_v78_60 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_56_to_v78_60_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_56_to_v78_60_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.56-V78.60 PASS - READY TO COMMIT"
