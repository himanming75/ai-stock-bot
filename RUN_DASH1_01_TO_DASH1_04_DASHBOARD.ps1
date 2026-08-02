param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8501
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "=== DASH1.01-DASH1.04 DASHBOARD FOUNDATION ==="
Write-Host "Local read-only dashboard. No broker network or order submission."
python -m dashboard.server `
  --repository-root . `
  --host $HostAddress `
  --port $Port
