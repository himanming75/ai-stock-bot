$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op4_17_to_op4_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_paper_pilot_automation_op4_17_to_op4_20 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP4_17_TO_OP4_20_AUTOMATION.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_paper_pilot_automation_op4_17_to_op4_20.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.17-OP4.20 TEST AND VERIFY PASS"
