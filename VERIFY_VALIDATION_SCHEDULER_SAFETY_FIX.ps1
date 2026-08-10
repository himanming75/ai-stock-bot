$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m py_compile .\validation_automation\scheduler.py
if($LASTEXITCODE -ne 0){throw "SCHEDULER SAFETY COMPILE FAILED"}

& $Python .\tests\test_validation_scheduler_safety_fix.py
if($LASTEXITCODE -ne 0){throw "SCHEDULER SAFETY TEST FAILED"}

& $Python -c "from pathlib import Path; from validation_automation.scheduler import load_config,scheduler_status; r=Path(r'C:\stock-bot'); c=load_config(r); assert c['catch_up_missed_runs'] is False; s=scheduler_status(r); assert s['paper_engine_started'] is False; assert s['broker_network_used'] is False; assert s['orders_submitted']==0; assert s['live_trading'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "SCHEDULER SAFETY VERIFY FAILED"}

Write-Host ""
Write-Host "VALIDATION SCHEDULER SAFETY FIX: PASS"
