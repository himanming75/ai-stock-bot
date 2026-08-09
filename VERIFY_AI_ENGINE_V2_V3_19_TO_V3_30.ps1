$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8889

Write-Host "=== AI ENGINE V2 DIRECT SERVER VERIFY ==="

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

 $A=$S.trade_analytics.ai_engine_v2

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "AI ENGINE V2 STATUS:" $A.status
 Write-Host "DEVELOPMENT STATUS:" $A.development_status
 Write-Host "REAL EVIDENCE STATUS:" $A.real_evidence_status
 Write-Host "LIVE TRADING STATUS:" $A.live_trading_status
 Write-Host "AUTO PROMOTION STATUS:" $A.automatic_promotion_status
 Write-Host "STAGE COUNT:" $A.stage_count

 foreach($Key in @("V3.19","V3.20","V3.21","V3.22","V3.23","V3.24","V3.25","V3.26","V3.27","V3.28","V3.29")){
   $Stage=$A.stages.$Key
   Write-Host $Key ":" $Stage.status
 }

 if($S.visualization_status -ne "PASS"){
   throw "VISUALIZATION REGRESSION"
 }
 if($S.trade_analytics_status -ne "PASS"){
   throw "TRADE ANALYTICS NOT PASS"
 }
 if($A.development_status -ne "COMPLETE"){
   throw "AI ENGINE V2 DEVELOPMENT NOT COMPLETE"
 }
 if($A.live_trading_status -ne "LOCKED"){
   throw "LIVE TRADING LOCK FAILED"
 }
 if($A.automatic_promotion_status -ne "LOCKED"){
   throw "AUTOMATIC PROMOTION LOCK FAILED"
 }
 if(-not $A.contracts.synthetic_fixture_validates_software_not_profitability){
   throw "SYNTHETIC FIXTURE CONTRACT FAILED"
 }
 if($A.contracts.broker_write_performed){
   throw "BROKER WRITE CONTRACT FAILED"
 }
 if($A.contracts.order_submission_performed){
   throw "ORDER SUBMISSION CONTRACT FAILED"
 }
 if($A.contracts.live_trading_enabled){
   throw "LIVE ENABLE CONTRACT FAILED"
 }
 if($A.contracts.automatic_promotion){
   throw "AUTO PROMOTION CONTRACT FAILED"
 }

 $Safety=$A.stages.'V3.29'
 if(-not $Safety.locks.live_trading_locked){
   throw "SAFETY LIVE LOCK FAILED"
 }
 if(-not $Safety.locks.broker_write_locked){
   throw "SAFETY BROKER WRITE LOCK FAILED"
 }
 if(-not $Safety.locks.automatic_strategy_change_locked){
   throw "SAFETY STRATEGY CHANGE LOCK FAILED"
 }

 Write-Host ""
 Write-Host "=== UTF8 BILINGUAL UI VERIFY ==="

 & $Python `
  .\dashboard\verify_ai_engine_v2_utf8.py `
  --url "http://127.0.0.1:$Port/"

 if($LASTEXITCODE -ne 0){
   throw "AI ENGINE V2 UTF8 VERIFY FAILED"
 }

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
