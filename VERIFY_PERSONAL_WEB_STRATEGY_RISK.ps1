$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_personal_web_strategy_risk.py
if($LASTEXITCODE -ne 0){throw "PERSONAL WEB STRATEGY/RISK TEST FAILED"}

& $Python -c "from pathlib import Path; from strategy_manager.config import load,validate; r=Path(r'C:\stock-bot'); c=load(r); v=validate(c); assert v['valid']; assert v['normalized']['paper_only'] is True; assert v['normalized']['live_submission_enabled'] is False; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "PERSONAL WEB STRATEGY/RISK VERIFY FAILED"}
