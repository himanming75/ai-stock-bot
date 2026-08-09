$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.manual_approval_record_expiration_guard_cli_v2_1_19 `
 --root C:\stock-bot `
 --expires-minutes 15
