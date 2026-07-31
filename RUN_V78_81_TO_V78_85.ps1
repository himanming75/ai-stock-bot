$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_deployment_v78_81_to_v78_85 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_81_to_v78_85_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_81_to_v78_85_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.81-V78.85 PASS - READY TO COMMIT"
