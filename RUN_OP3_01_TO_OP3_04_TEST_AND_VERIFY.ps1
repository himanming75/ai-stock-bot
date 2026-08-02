$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_op3_01_to_op3_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest tools.test_controlled_paper_order_preparation_op3_01_to_op3_04 -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP3_01_TO_OP3_04_PAPER_ORDER_PREPARATION.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_controlled_paper_order_preparation_op3_01_to_op3_04.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP3.01-OP3.04 TEST AND VERIFY PASS"
