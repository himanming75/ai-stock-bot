$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m py_compile `
 .\validation_automation\scheduler.py `
 .\web_controller\validation_lab_api.py
if($LASTEXITCODE -ne 0){throw "VALIDATION AUTO/HISTORY COMPILE FAILED"}

& $Python .\tests\test_personal_web_validation_auto_history.py
if($LASTEXITCODE -ne 0){throw "VALIDATION AUTO/HISTORY TEST FAILED"}

& $Python -c "from pathlib import Path; from validation_automation.scheduler import scheduler_status,history_status; r=Path(r'C:\stock-bot'); s=scheduler_status(r); assert s['paper_engine_started'] is False; assert s['broker_network_used'] is False; assert s['orders_submitted']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "VALIDATION AUTO/HISTORY VERIFY FAILED"}
