param(
    [int]$Port = 8601
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V88.01-V88.08 WEB UI V2 ==="
Write-Host "Open: http://127.0.0.1:$Port"
Write-Host "Press Ctrl+C to stop."

python web_ui_v2\app.py --host 127.0.0.1 --port $Port
