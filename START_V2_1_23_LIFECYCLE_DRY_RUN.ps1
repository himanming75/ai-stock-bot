$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.alpaca_paper_order_position_lifecycle_cli_v2_1_23 --root C:\stock-bot
