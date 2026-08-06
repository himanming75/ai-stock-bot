param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8770
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_trading_configuration_gui.py `
  --host $HostAddress `
  --port $Port
