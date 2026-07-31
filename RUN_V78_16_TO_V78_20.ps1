$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_paper_session_v78_16_to_v78_20 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_16_to_v78_20_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_16_to_v78_20_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.16-V78.20 PASS - READY TO COMMIT"
