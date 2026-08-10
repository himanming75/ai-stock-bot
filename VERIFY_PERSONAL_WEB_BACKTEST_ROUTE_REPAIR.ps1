$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$env:PYTHONPATH=$Repo
$Python="$Repo\.venv\Scripts\python.exe"

if(-not (Test-Path ".\web_controller\backtest_api.py")){
    throw "BACKTEST API MISSING - REINSTALL ORIGINAL BACKTEST INTEGRATION FILES FIRST"
}
if(-not (Test-Path ".\web_controller\static\index.html")){
    throw "WEB INDEX MISSING"
}
if(-not (Test-Path ".\web_controller\static\app.js")){
    throw "WEB APP JS MISSING"
}

& $Python .\tools\repair_personal_web_backtest_route.py
if($LASTEXITCODE -ne 0){throw "SERVER ROUTE REPAIR FAILED"}

& $Python -m py_compile .\web_controller\server.py .\web_controller\backtest_api.py
if($LASTEXITCODE -ne 0){throw "PYTHON COMPILE FAILED"}

& $Python -c "from pathlib import Path; p=Path(r'C:\stock-bot\web_controller\server.py'); t=p.read_text(encoding='utf-8'); assert 'from web_controller.backtest_api import get_payload as get_backtest,action_payload as run_backtest_action' in t; assert '\"/api/backtest\":lambda:get_backtest(self.root)' in t; assert 'elif p==\"/api/backtest/action\":r=run_backtest_action(self.root,b)' in t; print('ROUTE VERIFY: PASS')"
if($LASTEXITCODE -ne 0){throw "ROUTE VERIFY FAILED"}

& $Python .\tests\test_personal_web_backtest_route_repair.py
if($LASTEXITCODE -ne 0){throw "REPAIR TEST FAILED"}

Write-Host "VERIFY: PASS"
