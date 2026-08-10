$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m py_compile .\web_controller\validation_lab_api.py
if($LASTEXITCODE -ne 0){throw "VALIDATION PROGRESS COMPILE FAILED"}

& $Python .\tests\test_personal_web_validation_progress.py
if($LASTEXITCODE -ne 0){throw "VALIDATION PROGRESS TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.validation_lab_api import get_payload; p=get_payload(Path(r'C:\stock-bot'))['progress']; assert p['trading_days_target']==10; assert p['resolved_outcomes_target']==200; assert p['synthetic_progress_used'] is False; assert p['future_outcomes_fabricated'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "VALIDATION PROGRESS VERIFY FAILED"}
