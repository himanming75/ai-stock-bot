$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8890

Write-Host "=== BROKER INTEGRATION V1 DIRECT SERVER VERIFY ==="

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

 $B=$S.broker_integration_v1

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "AI ENGINE V2:" $S.trade_analytics.ai_engine_v2.development_status
 Write-Host "BROKER V1 STATUS:" $B.status
 Write-Host "DEVELOPMENT:" $B.development_status
 Write-Host "CANONICAL CONTRACT:" $B.contract_reuse.canonical_contract_module
 Write-Host "DUPLICATE CONTRACT:" $B.contracts.duplicate_broker_contract_created
 Write-Host "DUPLICATE ALPACA STACK:" $B.contracts.duplicate_alpaca_market_data_stack_created
 Write-Host "ETRADE READONLY:" $B.etrade_readonly_status
 Write-Host "ETRADE AUTH:" $B.etrade_auth_status
 Write-Host "NETWORK:" $B.network_status
 Write-Host "LIVE:" $B.live_trading_status

 if($S.visualization_status -ne "PASS"){
  throw "VISUALIZATION REGRESSION"
 }

 if($S.trade_analytics_status -ne "PASS"){
  throw "TRADE ANALYTICS REGRESSION"
 }

 if($S.trade_analytics.ai_engine_v2.development_status -ne "COMPLETE"){
  throw "AI ENGINE V2 REGRESSION"
 }

 if($B.development_status -ne "COMPLETE"){
  throw "BROKER V1 DEVELOPMENT NOT COMPLETE"
 }

 if($B.contract_reuse.canonical_contract_module -ne "broker.contracts_v77_1"){
  throw "CANONICAL BROKER CONTRACT NOT REUSED"
 }

 if($B.contracts.duplicate_broker_contract_created){
  throw "DUPLICATE BROKER CONTRACT DETECTED"
 }

 if($B.contracts.duplicate_alpaca_market_data_stack_created){
  throw "DUPLICATE ALPACA STACK DETECTED"
 }

 if($B.contracts.broker_network_used){
  throw "BROKER NETWORK CONTRACT FAILED"
 }

 if($B.contracts.broker_write_performed){
  throw "BROKER WRITE CONTRACT FAILED"
 }

 if($B.contracts.order_submission_performed){
  throw "ORDER SUBMISSION CONTRACT FAILED"
 }

 if($B.live_trading_status -ne "LOCKED"){
  throw "LIVE TRADING LOCK FAILED"
 }

 if($B.network_status -ne "LOCKED"){
  throw "NETWORK LOCK FAILED"
 }

 $G=$B.live_safety_gateway

 if(-not $G.broker_write_locked){
  throw "BROKER WRITE GATE FAILED"
 }

 if(-not $G.order_submission_locked){
  throw "ORDER SUBMIT GATE FAILED"
 }

 if(-not $G.cancel_replace_locked){
  throw "CANCEL/REPLACE GATE FAILED"
 }

 if(-not $G.live_trading_locked){
  throw "LIVE GATE FAILED"
 }

 Write-Host ""
 Write-Host "=== UTF8 BILINGUAL UI VERIFY ==="

 & $Python `
  .\dashboard\verify_broker_integration_v1_utf8.py `
  --url "http://127.0.0.1:$Port/"

 if($LASTEXITCODE -ne 0){
  throw "BROKER V1 UTF8 VERIFY FAILED"
 }

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
