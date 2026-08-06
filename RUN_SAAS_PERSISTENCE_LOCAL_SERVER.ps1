param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8765,
    [string]$DatabasePath="runtime/saas/saas.db"
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_saas_persistence_server.py `
    --host $HostAddress `
    --port $Port `
    --database $DatabasePath
