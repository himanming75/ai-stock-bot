$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_paper_event_v78_6_to_v78_10 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_6_to_v78_10_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_6_to_v78_10_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.6-V78.10 PASS - READY TO COMMIT"
