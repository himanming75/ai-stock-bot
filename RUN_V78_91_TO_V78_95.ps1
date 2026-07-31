$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_final_system_certification_v78_91_to_v78_95 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_91_to_v78_95_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_91_to_v78_95_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.91-V78.95 PASS - READY TO COMMIT"
