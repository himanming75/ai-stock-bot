$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_strategy_runtime_v78_36_to_v78_40 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_36_to_v78_40_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_36_to_v78_40_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.36-V78.40 PASS - READY TO COMMIT"
