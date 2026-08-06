param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8773
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_ai_signal_scoring_dashboard.py `
  --host $HostAddress `
  --port $Port
