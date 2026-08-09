$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.daily_risk_budget_kill_switch_cli_v2_1_29 --root C:\stock-bot --evaluate
