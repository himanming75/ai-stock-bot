$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8897

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

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
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 30
 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth.current_market_data_signal_v2_1_7

 Write-Host "V2.1.7 STATUS:" $V.status
 Write-Host "DEVELOPMENT:" $V.development_status
 Write-Host "MARKET ENGINE:" $V.existing_market_data_engine_reused
 Write-Host "INDICATOR ENGINE:" $V.existing_indicator_engine_reused
 Write-Host "SIGNAL ENGINE:" $V.existing_signal_engine_reused
 Write-Host "READONLY SOURCE:" $V.current_readonly_market_data_source_ready
 Write-Host "NETWORK OPT-IN:" $V.network_opt_in_required
 Write-Host "BROKER ORDER SUBMISSION:" $V.broker_order_submission_from_stage
 Write-Host "PROD POST:" $V.production_order_post_allowed
 Write-Host "LIVE:" $V.live_trading_enabled

 if($V.development_status -ne "COMPLETE"){throw "V2.1.7 DEVELOPMENT FAILED"}
 if($V.existing_market_data_engine_reused -ne "V102.01-V103.00"){throw "MARKET ENGINE REUSE FAILED"}
 if($V.existing_indicator_engine_reused -ne "V79.66-V79.70"){throw "INDICATOR ENGINE REUSE FAILED"}
 if($V.existing_signal_engine_reused -ne "V79.71-V79.75"){throw "SIGNAL ENGINE REUSE FAILED"}
 if(-not $V.current_readonly_market_data_source_ready){throw "READONLY SOURCE NOT READY"}
 if($V.broker_order_submission_from_stage){throw "V2.1.7 MUST NOT SUBMIT BROKER ORDERS"}
 if($V.production_order_post_allowed){throw "PROD ORDER POST UNLOCKED"}
 if($V.live_trading_enabled){throw "LIVE TRADING ENABLED"}
 if($V.contracts.duplicate_market_data_engine_created){throw "DUPLICATE MARKET ENGINE"}
 if($V.contracts.duplicate_indicator_engine_created){throw "DUPLICATE INDICATOR ENGINE"}
 if($V.contracts.duplicate_signal_engine_created){throw "DUPLICATE SIGNAL ENGINE"}

 & $Python .\dashboard\verify_etrade_current_market_data_signal_v2_1_7_utf8.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V2.1.7 UTF8 VERIFY FAILED"}

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
