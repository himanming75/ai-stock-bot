$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8896

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
 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth.ai_signal_decision_v2_1_5

 Write-Host "V2.1.5 STATUS:" $V.status
 Write-Host "DEVELOPMENT:" $V.development_status
 Write-Host "BUY/SELL/HOLD:" $V.buy_sell_hold_normalization
 Write-Host "CONFIDENCE GATE:" $V.confidence_gate
 Write-Host "HOLD BLOCK:" $V.hold_blocks_order
 Write-Host "MAX SIGNAL QUEUE:" $V.bounded_signal_queue_maximum
 Write-Host "PROD POST:" $V.production_order_post_allowed
 Write-Host "LIVE:" $V.live_trading_enabled
 Write-Host "PROFIT VALIDATION:" $V.profitability_validation

 if($V.development_status -ne "COMPLETE"){throw "V2.1.5 DEVELOPMENT FAILED"}
 if(-not $V.buy_sell_hold_normalization){throw "DECISION NORMALIZATION FAILED"}
 if(-not $V.confidence_gate){throw "CONFIDENCE GATE FAILED"}
 if(-not $V.hold_blocks_order){throw "HOLD GATE FAILED"}
 if($V.bounded_signal_queue_maximum -ne 3){throw "SIGNAL QUEUE LIMIT FAILED"}
 if($V.production_order_post_allowed){throw "PROD ORDER POST UNLOCKED"}
 if($V.live_trading_enabled){throw "LIVE TRADING ENABLED"}
 if($V.profitability_validation){throw "PROFITABILITY VALIDATION INCORRECT"}
 if($V.contracts.duplicate_order_engine_created){throw "DUPLICATE ORDER ENGINE"}
 if(-not $V.contracts.ai_engine_v2_not_modified){throw "AI ENGINE V2 MODIFIED"}

 & $Python .\dashboard\verify_etrade_ai_signal_decision_v2_1_5_utf8.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V2.1.5 UTF8 VERIFY FAILED"}

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
