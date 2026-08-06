param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8771
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_phase1_premarket_dashboard.py `
  --host $HostAddress `
  --port $Port
