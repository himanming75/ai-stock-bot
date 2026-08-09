$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.fresh_eligible_signal_evidence_capture_cli_v2_1_16 `
 --root C:\stock-bot
