$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_reporting_v78_76_to_v78_80 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_76_to_v78_80_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_76_to_v78_80_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.76-V78.80 PASS - READY TO COMMIT"
