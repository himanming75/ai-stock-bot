$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_operation_runtime_v78_86_to_v78_90 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_86_to_v78_90_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_86_to_v78_90_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.86-V78.90 PASS - READY TO COMMIT"
