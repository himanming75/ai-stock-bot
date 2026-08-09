$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

Write-Host "Unified Dashboard URL: http://127.0.0.1:8765"
Write-Host "Stop any older dashboard using port 8765 first with Ctrl+C."

& $Python .\dashboard\operations_dashboard_v3_2.py `
    --root C:\stock-bot `
    --host 127.0.0.1 `
    --port 8765
