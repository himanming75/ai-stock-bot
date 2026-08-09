$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$env:PYTHONPATH="C:\stock-bot"
C:\stock-bot\.venv\Scripts\python.exe -m broker_integration_v1.session_crash_network_restart_recovery_cli_v2_1_30 --root C:\stock-bot --local-plan
