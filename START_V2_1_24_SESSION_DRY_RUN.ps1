$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.paper_intraday_autonomous_session_cli_v2_1_24 `
 --root C:\stock-bot `
 --mode DRY `
 --max-cycles 3 `
 --interval-seconds 5 `
 --lifecycle-cycles 3
