param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V85.01-V85.08 DASHBOARD V2 ==="
Write-Host "Open: http://127.0.0.1:$Port"
Write-Host "Press Ctrl+C to stop."

python dashboard_v2\server.py --host 127.0.0.1 --port $Port
