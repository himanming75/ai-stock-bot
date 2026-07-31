$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_runtime_scheduler_v78_21_to_v78_25 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_21_to_v78_25_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_21_to_v78_25_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.21-V78.25 PASS - READY TO COMMIT"
