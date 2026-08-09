$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"

& $Python -m py_compile `
 .\broker_integration_v1\etrade_oauth_flow_v2.py `
 .\broker_integration_v1\etrade_oauth_http_diagnostic_v2_1_2_1.py

if($LASTEXITCODE -ne 0){
 exit $LASTEXITCODE
}

& $Python `
 .\tests\test_etrade_oauth_http_diagnostic_v2_1_2_1.py

if($LASTEXITCODE -ne 0){
 exit $LASTEXITCODE
}

Write-Host "V2.1.2.1 RUN: PASS"
