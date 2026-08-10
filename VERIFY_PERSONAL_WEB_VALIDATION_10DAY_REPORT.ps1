$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m py_compile .\web_controller\validation_lab_api.py
if($LASTEXITCODE -ne 0){throw "10-DAY REPORT COMPILE FAILED"}

& $Python .\tests\test_personal_web_validation_10day_report.py
if($LASTEXITCODE -ne 0){throw "10-DAY REPORT TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.validation_lab_api import get_payload; r=get_payload(Path(r'C:\stock-bot'))['report']; assert r['synthetic_days_added'] is False; assert r['interpolation_used'] is False; assert r['future_outcomes_fabricated'] is False; assert r['resolved_outcomes_target']==200; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "10-DAY REPORT VERIFY FAILED"}
