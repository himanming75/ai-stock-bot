$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper
if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){throw "NON-PAPER ENDPOINT BLOCKED"}
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.alpaca_paper_order_position_lifecycle_cli_v2_1_23 --root C:\stock-bot --monitor --interval-seconds 5 --max-cycles 12
