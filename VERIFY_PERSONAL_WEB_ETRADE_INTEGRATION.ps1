$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tools\patch_personal_web_etrade_server.py
if($LASTEXITCODE -ne 0){throw "ETRADE SERVER PATCH FAILED"}

& $Python -m py_compile .\web_controller\server.py .\web_controller\etrade_api.py
if($LASTEXITCODE -ne 0){throw "ETRADE WEB COMPILE FAILED"}

& $Python .\tests\test_personal_web_etrade_integration.py
if($LASTEXITCODE -ne 0){throw "ETRADE WEB TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.etrade_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); assert not d['credentials']['credential_values_exposed']; assert not d['safety']['production_order_post_allowed']; assert not d['safety']['live_trading_enabled']; assert not d['safety']['web_live_order_action_available']; assert d['safety']['actual_live_orders_submitted']==0; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "ETRADE WEB VERIFY FAILED"}
