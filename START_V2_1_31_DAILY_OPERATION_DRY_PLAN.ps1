$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.one_click_daily_paper_operation_cli_v2_1_31 `
 --root C:\stock-bot `
 --dry-plan
