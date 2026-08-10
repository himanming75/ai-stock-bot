$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_personal_web_strategy_comparison.py
if($LASTEXITCODE -ne 0){throw "STRATEGY COMPARISON TEST FAILED"}

& $Python -m py_compile .\web_controller\backtest_api.py
if($LASTEXITCODE -ne 0){throw "BACKTEST API COMPILE FAILED"}

& $Python -c "from pathlib import Path; from web_controller.backtest_api import get_payload; d=get_payload(Path(r'C:\stock-bot')); c=d['comparison']; assert 'current_strategy' in c; assert 'candidate' in c; assert 'ai' in c; assert c['recommendation']['automatic_strategy_change'] is False; assert c['recommendation']['automatic_threshold_change'] is False; assert c['recommendation']['automatic_risk_change'] is False; assert c['recommendation']['automatic_paper_execution_change'] is False; assert c['recommendation']['automatic_live_execution_change'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "STRATEGY COMPARISON VERIFY FAILED"}
