$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_paper_broker_v78_1_to_v78_5 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_1_to_v78_5_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_1_to_v78_5_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.1-V78.5 PASS - READY TO COMMIT"
