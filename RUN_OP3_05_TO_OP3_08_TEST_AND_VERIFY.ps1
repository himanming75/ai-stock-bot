$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_op3_05_to_op3_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_single_controlled_paper_order_execution_op3_05_to_op3_08 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP3_05_TO_OP3_08_SINGLE_PAPER_ORDER.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python `
  tools/verify_single_controlled_paper_order_execution_op3_05_to_op3_08.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP3.05-OP3.08 TEST AND VERIFY PASS"
