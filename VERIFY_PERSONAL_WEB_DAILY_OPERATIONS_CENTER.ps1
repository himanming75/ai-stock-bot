$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tools\patch_personal_web_daily_ops_server.py
if($LASTEXITCODE -ne 0){throw "DAILY OPS SERVER PATCH FAILED"}

& $Python -m py_compile `
 .\web_controller\server.py `
 .\web_controller\daily_ops_api.py
if($LASTEXITCODE -ne 0){throw "DAILY OPS COMPILE FAILED"}

& $Python .\tests\test_personal_web_daily_ops_center.py
if($LASTEXITCODE -ne 0){throw "DAILY OPS TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.daily_ops_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); s=d['safety']; assert not s['etrade_used']; assert s['paper_orders_submitted_by_daily_ops']==0; assert s['live_orders_submitted_by_daily_ops']==0; assert not s['automatic_model_promotion']; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "DAILY OPS VERIFY FAILED"}
