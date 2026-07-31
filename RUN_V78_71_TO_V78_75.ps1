$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_performance_accounting_v78_71_to_v78_75 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_71_to_v78_75_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_71_to_v78_75_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.71-V78.75 PASS - READY TO COMMIT"
