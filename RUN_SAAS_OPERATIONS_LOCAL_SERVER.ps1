param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8767,
    [string]$RuntimeRoot="runtime",
    [string]$DatabasePath="runtime/saas/saas.db"
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_saas_operations_server.py `
    --host $HostAddress `
    --port $Port `
    --runtime-root $RuntimeRoot `
    --database $DatabasePath
