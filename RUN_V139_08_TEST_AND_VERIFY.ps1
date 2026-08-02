$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_submitted_order_acceptance_verification_v139_08 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_08_SUBMITTED_ORDER_ACCEPTANCE_VERIFICATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_submitted_order_acceptance_verification_v139_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.08 TEST AND VERIFY PASS"
