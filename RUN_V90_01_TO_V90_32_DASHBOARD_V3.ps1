param([int]$Port=8602)
$ErrorActionPreference="Stop";Set-Location $PSScriptRoot
Write-Host "=== V90.01-V90.32 DASHBOARD ANALYTICS V3 ==="
Write-Host "Open: http://127.0.0.1:$Port"
python dashboard_analytics_v3\app.py --host 127.0.0.1 --port $Port
