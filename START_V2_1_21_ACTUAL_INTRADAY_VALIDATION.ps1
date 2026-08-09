$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.actual_intraday_canonical_e2e_validation_cli_v2_1_21 --root C:\stock-bot --symbols AAPL,MSFT,SPY --quantity 1
