param(
    [string]$HostAddress="127.0.0.1",
    [int]$Port=8768,
    [string]$PortalPath="release/actual_multi_broker_sync/actual/multi_broker_portal_snapshot.json",
    [string]$SyncResultPath="release/actual_multi_broker_sync/actual/broker_sync_result.json"
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_unified_trading_portal.py `
  --host $HostAddress `
  --port $Port `
  --portal-path $PortalPath `
  --sync-result-path $SyncResultPath
