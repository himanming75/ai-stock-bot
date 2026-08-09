$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Date=Read-Host "Market date YYYY-MM-DD"
if($Date -notmatch '^\d{4}-\d{2}-\d{2}$'){
 throw "INVALID DATE FORMAT"
}

$env:PYTHONPATH="C:\stock-bot"

C:\stock-bot\.venv\Scripts\python.exe `
 -m broker_integration_v1.daily_performance_operation_report_cli_v2_1_32 `
 --root C:\stock-bot `
 --market-date $Date
