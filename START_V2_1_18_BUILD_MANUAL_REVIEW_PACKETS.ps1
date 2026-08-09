$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.manual_sandbox_review_packet_builder_cli_v2_1_18 `
 --root C:\stock-bot
