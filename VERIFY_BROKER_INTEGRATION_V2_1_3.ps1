$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8894

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
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

 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth.autonomous_cycle_v2_1_3

 Write-Host "V2.1.3 STATUS:" $V.status
 Write-Host "DEVELOPMENT:" $V.development_status
 Write-Host "ONE CYCLE:" $V.one_cycle_supported
 Write-Host "AUTO REPEAT:" $V.automatic_repeat_enabled
 Write-Host "PROD POST:" $V.production_order_post_allowed
 Write-Host "LIVE:" $V.live_trading_enabled
 Write-Host "PROFIT VALIDATION:" $V.profitability_validation

 if($V.development_status -ne "COMPLETE"){throw "V2.1.3 DEVELOPMENT FAILED"}
 if(-not $V.one_cycle_supported){throw "ONE CYCLE NOT READY"}
 if($V.automatic_repeat_enabled){throw "AUTO REPEAT MUST REMAIN DISABLED"}
 if($V.production_order_post_allowed){throw "PROD ORDER POST UNLOCKED"}
 if($V.live_trading_enabled){throw "LIVE TRADING ENABLED"}
 if($V.profitability_validation){throw "SANDBOX MISLABELED AS PROFIT VALIDATION"}
 if($V.contracts.duplicate_order_engine_created){throw "DUPLICATE ORDER ENGINE"}
 if($V.contracts.duplicate_ledger_created){throw "DUPLICATE LEDGER"}
 if($V.contracts.duplicate_reconciliation_engine_created){throw "DUPLICATE RECONCILIATION ENGINE"}

 & $Python .\dashboard\verify_etrade_sandbox_autonomous_cycle_v2_1_3_utf8.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V2.1.3 UTF8 VERIFY FAILED"}

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
