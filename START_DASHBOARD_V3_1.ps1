$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}
Write-Host "Dashboard URL: http://127.0.0.1:8765"
Write-Host "Press Ctrl+C to stop the dashboard."
& $Python .\dashboard\operations_dashboard_v3_1.py --root C:\stock-bot --host 127.0.0.1 --port 8765
