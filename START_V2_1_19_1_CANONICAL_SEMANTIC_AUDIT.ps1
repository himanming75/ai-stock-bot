$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.canonical_paper_gate_semantic_audit_cli_v2_1_19_1 `
 --root C:\stock-bot
