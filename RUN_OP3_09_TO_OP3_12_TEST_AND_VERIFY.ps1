$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python tools/install_check_op3_09_to_op3_12.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m unittest `
  tools.test_paper_order_lifecycle_op3_09_to_op3_12 `
  -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP3_09_TO_OP3_12_PAPER_LIFECYCLE.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python tools/verify_paper_order_lifecycle_op3_09_to_op3_12.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP3.09-OP3.12 TEST AND VERIFY PASS"
