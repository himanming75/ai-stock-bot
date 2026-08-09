$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.continuous_bounded_paper_session_cli_v2_1_28 `
 --root C:\stock-bot `
 --rollover-plan
