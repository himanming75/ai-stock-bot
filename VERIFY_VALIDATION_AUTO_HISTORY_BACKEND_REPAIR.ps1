$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

Write-Host "=== BACKEND CONTENT CHECK ==="

$ApiText=Get-Content .\web_controller\validation_lab_api.py -Raw
if($ApiText -notmatch 'start_auto_scheduler'){throw "MISSING start_auto_scheduler"}
if($ApiText -notmatch '"scheduler":_scheduler_status'){throw "MISSING scheduler payload"}
if($ApiText -notmatch '"history":_history_status'){throw "MISSING history payload"}

& $Python -m py_compile `
  .\validation_automation\scheduler.py `
  .\web_controller\validation_lab_api.py
if($LASTEXITCODE -ne 0){throw "PYTHON COMPILE FAILED"}

& $Python .\tests\test_validation_auto_history_backend_repair.py
if($LASTEXITCODE -ne 0){throw "BACKEND REPAIR TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.validation_lab_api import get_payload,action_payload; r=Path(r'C:\stock-bot'); d=get_payload(r); assert 'scheduler' in d and 'history' in d; a=action_payload(r,{'action':'credential_preflight_probe'}); assert a['error']=='ACTION_NOT_ALLOWED'; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "BACKEND VERIFY FAILED"}

Write-Host ""
Write-Host "VALIDATION AUTO/HISTORY BACKEND REPAIR: PASS"
Write-Host "IMPORTANT: Stop the existing 8767 Python process completely before restarting."
