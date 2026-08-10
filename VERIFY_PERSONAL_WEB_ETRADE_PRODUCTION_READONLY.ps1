$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python -m py_compile `
  .\web_controller\etrade_api.py `
  .\tools\start_personal_control_center_etrade_readonly.py
if($LASTEXITCODE -ne 0){throw "COMPILE FAILED"}

& $Python .\tests\test_personal_web_etrade_production_readonly.py
if($LASTEXITCODE -ne 0){throw "TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.etrade_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); assert not d['production_session']['credential_values_exposed']; assert not d['safety']['production_order_post_allowed']; assert not d['safety']['live_trading_enabled']; assert d['safety']['actual_live_orders_submitted']==0; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "VERIFY FAILED"}
