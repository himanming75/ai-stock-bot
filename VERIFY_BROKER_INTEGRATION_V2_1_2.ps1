$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8893

Write-Host "=== V2.1.2 DIRECT SERVER VERIFY ==="

$Old=@(
 Get-NetTCPConnection `
  -LocalPort $Port `
  -State Listen `
  -ErrorAction SilentlyContinue
)

foreach($L in $Old){
 Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue
}

$P=Start-Process `
 -FilePath $Python `
 -ArgumentList @(
  "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
  "--root","C:\stock-bot",
  "--host","127.0.0.1",
  "--port","$Port"
 ) `
 -WorkingDirectory "C:\stock-bot" `
 -PassThru

try{
 Start-Sleep -Seconds 6

 $S=Invoke-RestMethod `
  -Uri "http://127.0.0.1:$Port/api/status" `
  -TimeoutSec 30

 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth.place_ledger_v2_1_2

 Write-Host "V2.1.2 STATUS:" $V.status
 Write-Host "DEVELOPMENT:" $V.development_status
 Write-Host "SANDBOX PLACE:" $V.sandbox_place_supported
 Write-Host "PLACE CONFIRMATION:" $V.explicit_place_confirmation_required
 Write-Host "ORDER LEDGER:" $V.order_ledger_supported
 Write-Host "RECONCILIATION:" $V.status_reconciliation_supported
 Write-Host "PROD POST:" $V.production_order_post_allowed
 Write-Host "LIVE:" $V.live_trading_enabled
 Write-Host "PROFIT VALIDATION:" $V.profitability_validation

 if($V.development_status -ne "COMPLETE"){
  throw "V2.1.2 DEVELOPMENT FAILED"
 }

 if(-not $V.sandbox_place_supported){
  throw "SANDBOX PLACE NOT READY"
 }

 if(-not $V.explicit_place_confirmation_required){
  throw "PLACE CONFIRMATION GATE FAILED"
 }

 if(-not $V.order_ledger_supported){
  throw "ORDER LEDGER NOT READY"
 }

 if(-not $V.status_reconciliation_supported){
  throw "RECONCILIATION NOT READY"
 }

 if($V.production_order_post_allowed){
  throw "PROD ORDER POST UNLOCKED"
 }

 if($V.live_trading_enabled){
  throw "LIVE TRADING ENABLED"
 }

 if($V.profitability_validation){
  throw "SANDBOX MISLABELED AS PROFIT VALIDATION"
 }

 if($V.contracts.duplicate_order_engine_created){
  throw "DUPLICATE ORDER ENGINE"
 }

 if($V.contracts.account_id_stored_raw){
  throw "RAW ACCOUNT ID STORAGE DETECTED"
 }

 & $Python `
  .\dashboard\verify_etrade_sandbox_order_v2_1_2_utf8.py `
  --url "http://127.0.0.1:$Port/"

 if($LASTEXITCODE -ne 0){
  throw "V2.1.2 UTF8 VERIFY FAILED"
 }

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
