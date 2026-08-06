param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8776
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_portfolio_optimizer_dashboard.py `
  --host $HostAddress `
  --port $Port
