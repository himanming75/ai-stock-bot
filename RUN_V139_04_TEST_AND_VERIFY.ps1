$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_v139_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_recovery_validation_v139_04 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_V139_04_RECOVERY_VALIDATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_recovery_validation_v139_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.04 TEST AND VERIFY PASS"
