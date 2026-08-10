$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

& $Python .\tests\test_personal_web_command_center.py
if($LASTEXITCODE -ne 0){throw "COMMAND CENTER UI TEST FAILED"}

& $Python -c "from pathlib import Path; from web_controller.state import build_dashboard; d=build_dashboard(Path(r'C:\stock-bot')); assert 'ai' in d; assert d['safety']['local_bind_only']; assert d['safety']['actual_live_orders_submitted']==0; print('VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "COMMAND CENTER VERIFY FAILED"}
