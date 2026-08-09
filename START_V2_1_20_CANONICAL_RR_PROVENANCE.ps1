$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.canonical_reward_risk_provenance_cli_v2_1_20 `
 --root C:\stock-bot
