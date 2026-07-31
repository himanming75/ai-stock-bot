$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_audit_reconciliation_v78_66_to_v78_70 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/run_v78_66_to_v78_70_pipeline.py --repository-root . --clean
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python tools/verify_v78_66_to_v78_70_pipeline.py --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "V78.66-V78.70 PASS - READY TO COMMIT"
