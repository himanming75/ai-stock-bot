$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m py_compile .\web_controller\validation_lab_api.py
if($LASTEXITCODE -ne 0){throw "FINAL QUALIFICATION COMPILE FAILED"}

& $Python .\tests\test_personal_web_validation_final_qualification.py
if($LASTEXITCODE -ne 0){throw "FINAL QUALIFICATION TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.validation_lab_api import get_payload; q=get_payload(Path(r'C:\stock-bot'))['final_qualification']; assert q['decision'] in {'PASS','CONTINUE','FAIL'}; assert q['automatic_promotion'] is False; assert q['manual_review_required'] is True; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "FINAL QUALIFICATION VERIFY FAILED"}
