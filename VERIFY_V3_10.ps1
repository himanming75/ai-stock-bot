$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$Port=8880

Write-Host "=== V3.10 DIRECT SERVER VERIFY ==="

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

$P=Start-Process -FilePath $Python -ArgumentList @(
 "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
 "--root","C:\stock-bot","--host","127.0.0.1","--port","$Port"
) -WorkingDirectory "C:\stock-bot" -PassThru

try{
 Start-Sleep -Seconds 5
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 20
 $A=$S.trade_analytics
 $Details=@($A.trade_details)

 Write-Host "VISUALIZATION STATUS:" $S.visualization_status
 Write-Host "TRADE ANALYTICS STATUS:" $S.trade_analytics_status
 Write-Host "CANONICAL STATUS:" $A.canonical_lifecycle_discovery.status
 Write-Host "TRADE DETAIL ROWS:" $Details.Count
 Write-Host "CANONICAL NUMERIC TRADES:" $A.historical.numeric_trade_count

 if($Details.Count -gt 0){
   $First=$Details[0]
   Write-Host "FIRST SYMBOL:" $First.symbol
   Write-Host "FIRST ENTRY PRICE:" $First.entry_price
   Write-Host "FIRST EXIT PRICE:" $First.exit_price
   Write-Host "FIRST REALIZED PNL:" $First.pnl
   Write-Host "FIRST EXIT REASON:" $First.reason
   Write-Host "FIRST ORDER ID:" $First.exit_order_id
 }

 if($S.visualization_status -ne "PASS"){throw "VISUALIZATION REGRESSION"}
 if($S.trade_analytics_status -ne "PASS"){throw "TRADE ANALYTICS NOT PASS"}
 if($Details.Count -ne $A.historical.numeric_trade_count){throw "TRADE DETAIL COUNT DOES NOT MATCH CANONICAL NUMERIC TRADE COUNT"}

 if($Details.Count -gt 0){
   foreach($Row in $Details){
     if($null -eq $Row.entry_price){throw "TRADE DETAIL ENTRY PRICE MISSING"}
     if($null -eq $Row.exit_price){throw "TRADE DETAIL EXIT PRICE MISSING"}
     if($null -eq $Row.pnl){throw "TRADE DETAIL PNL MISSING"}
   }
 }

 Write-Host ""
 Write-Host "=== UTF8 UI VERIFY ==="

 & $Python .\dashboard\verify_trade_detail_utf8_v3_10.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V3.10 UTF8 UI VERIFY FAILED"}

 Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
