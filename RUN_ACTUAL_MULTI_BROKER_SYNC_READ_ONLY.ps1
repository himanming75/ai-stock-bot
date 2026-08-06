param(
    [string]$AlpacaPath="release/v8201_8400_broker_abstraction/actual/broker_unified_snapshot_fixture.json",
    [string]$ETradePath="release/etrade_sandbox_live_read/actual/etrade_sandbox_read_only_validation.json",
    [double]$StaleAfterSeconds=900
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
  .\tools\run_actual_multi_broker_sync.py `
  --alpaca $AlpacaPath `
  --etrade $ETradePath `
  --stale-after-seconds $StaleAfterSeconds

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "ACTUAL MULTI BROKER SYNC: PASS"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
Write-Host "ORDER CANCEL: OFF"
