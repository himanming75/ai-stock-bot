$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.alpaca_paper_exit_execution_recovery_cli_v2_1_25 `
 --root C:\stock-bot
