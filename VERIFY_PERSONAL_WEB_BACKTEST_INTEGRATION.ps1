$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_personal_web_backtest_integration.py
if($LASTEXITCODE -ne 0){throw "BACKTEST WEB TEST FAILED"}

& $Python -m py_compile .\web_controller\server.py .\web_controller\backtest_api.py
if($LASTEXITCODE -ne 0){throw "BACKTEST WEB COMPILE FAILED"}

& $Python -c "from pathlib import Path; from web_controller.backtest_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); s=d['safety']; assert s['existing_backtest_engine_reused']; assert not s['new_backtest_engine_created']; assert not s['new_strategy_created']; assert not s['broker_write_enabled']; assert not s['order_submission_enabled']; assert not s['live_trading_enabled']; assert s['actual_orders_submitted']==0; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "BACKTEST WEB VERIFY FAILED"}
