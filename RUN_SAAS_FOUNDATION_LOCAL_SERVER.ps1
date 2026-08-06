param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8765
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_saas_foundation_server.py `
    --host $HostAddress `
    --port $Port
