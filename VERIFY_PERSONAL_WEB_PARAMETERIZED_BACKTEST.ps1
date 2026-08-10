$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_personal_web_parameterized_backtest.py
if($LASTEXITCODE -ne 0){throw "PARAMETERIZED BACKTEST TEST FAILED"}

& $Python -m py_compile .\web_controller\backtest_api.py
if($LASTEXITCODE -ne 0){throw "BACKTEST API COMPILE FAILED"}

& $Python -c "from pathlib import Path; from web_controller.backtest_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); assert d['options']['strategies']; assert d['options']['datasets']; assert d['options']['windows']; s=d['safety']; assert not s['original_v98_policy_persistently_modified']; assert s['selected_policy_temporary_only']; assert not s['broker_write_enabled']; assert not s['order_submission_enabled']; assert not s['live_trading_enabled']; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "PARAMETERIZED BACKTEST VERIFY FAILED"}
