$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.evidence_qualification_sandbox_readiness_gate_cli_v2_1_17 `
 --root C:\stock-bot
