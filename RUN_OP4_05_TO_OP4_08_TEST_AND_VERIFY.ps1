$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_op4_05_to_op4_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_paper_session_monitor_op4_05_to_op4_08 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_OP4_05_TO_OP4_08_SESSION_MONITOR.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_paper_session_monitor_op4_05_to_op4_08.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "OP4.05-OP4.08 TEST AND VERIFY PASS"
