param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8766,
    [string]$DatabasePath="runtime/saas/security.db"
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_saas_security_server.py `
    --host $HostAddress `
    --port $Port `
    --database $DatabasePath
