param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8769
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_paper_command_center.py `
  --host $HostAddress `
  --port $Port
