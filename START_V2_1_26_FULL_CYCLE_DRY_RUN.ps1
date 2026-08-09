$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.full_alpaca_paper_round_trip_cli_v2_1_26 `
 --root C:\stock-bot `
 --mode DRY `
 --max-cycles 3 `
 --interval-seconds 5 `
 --lifecycle-cycles 3
