$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tools\patch_personal_web_validation_lab_server.py
if($LASTEXITCODE -ne 0){throw "VALIDATION LAB SERVER PATCH FAILED"}

& $Python -m py_compile `
 .\web_controller\server.py `
 .\web_controller\validation_lab_api.py
if($LASTEXITCODE -ne 0){throw "VALIDATION LAB COMPILE FAILED"}

& $Python .\tests\test_personal_web_validation_lab.py
if($LASTEXITCODE -ne 0){throw "VALIDATION LAB TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.validation_lab_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); s=d['safety']; assert not s['etrade_used']; assert not s['broker_network_used_by_validation_lab']; assert not s['paper_engine_started_by_validation_lab']; assert s['paper_orders_submitted_by_validation_lab']==0; assert s['live_orders_submitted_by_validation_lab']==0; assert not s['automatic_model_promotion']; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "VALIDATION LAB VERIFY FAILED"}
