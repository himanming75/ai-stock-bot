$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_op2_01_to_op2_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_shadow_decision_bootstrap_op2_01_to_op2_04 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass -File .\RUN_OP2_01_TO_OP2_04_SHADOW_DECISION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_shadow_decision_bootstrap_op2_01_to_op2_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP2.01-OP2.04 TEST AND VERIFY PASS"
