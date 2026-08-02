$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op4_01_to_op4_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_controlled_paper_pilot_op4_01_to_op4_04 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP4_01_TO_OP4_04_PILOT.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_controlled_paper_pilot_op4_01_to_op4_04.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.01-OP4.04 TEST AND VERIFY PASS"
