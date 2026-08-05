$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python -m unittest tools.test_ai_decision_strategy_risk_portfolio_bridge -v
python .\tools\verify_ai_decision_strategy_risk_portfolio_bridge.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
