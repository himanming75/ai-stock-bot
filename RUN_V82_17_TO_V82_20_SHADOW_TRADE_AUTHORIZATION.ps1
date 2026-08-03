
param(
    [switch]$MarketSessionClosed
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V82.17-V82.20 SHADOW TRADE AUTHORIZATION ==="
Write-Host "Local authorization only. No network or broker orders."

$argsList = @()
if ($MarketSessionClosed) {
    $argsList += "--market-session-closed"
}

python tools/run_shadow_trade_authorization_v82_17_to_v82_20.py @argsList
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "V82.17-V82.20 COMPLETE"
