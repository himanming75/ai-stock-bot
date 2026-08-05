$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Python=Join-Path $Root ".venv\Scripts\python.exe"
$env:PYTHONPATH=$Root
& $Python (Join-Path $Root "tools\run_ai_strategy_risk_portfolio_execution_v4.py")
exit $LASTEXITCODE
