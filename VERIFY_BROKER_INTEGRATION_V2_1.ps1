$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8892

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

$P=Start-Process -FilePath $Python -ArgumentList @(
 "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
 "--root","C:\stock-bot","--host","127.0.0.1","--port","$Port"
) -WorkingDirectory "C:\stock-bot" -PassThru

try{
 Start-Sleep -Seconds 6
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 30
 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth.sandbox_order_v2_1

 Write-Host "V2.1 STATUS:" $V.status
 Write-Host "ENVIRONMENT:" $V.environment
 Write-Host "PREVIEW:" $V.equity_preview_supported
 Write-Host "PLACE:" $V.equity_place_supported
 Write-Host "PROD POST:" $V.production_order_post_allowed
 Write-Host "PROFITABILITY VALIDATED:" $V.strategy_profitability_validated

 if($V.development_status -ne "COMPLETE"){throw "V2.1 DEVELOPMENT FAILED"}
 if($V.environment -ne "SANDBOX_ONLY"){throw "V2.1 ENVIRONMENT FAILED"}
 if(-not $V.equity_preview_supported){throw "PREVIEW NOT READY"}
 if(-not $V.equity_place_supported){throw "PLACE NOT READY"}
 if($V.production_order_post_allowed){throw "PROD ORDER POST UNLOCKED"}
 if($V.strategy_profitability_validated){throw "SANDBOX MISLABELED AS PROFIT VALIDATION"}
 if($V.contracts.duplicate_broker_contract_created){throw "DUPLICATE BROKER CONTRACT"}
 if($V.contracts.production_order_submission_performed){throw "PROD ORDER SUBMISSION DETECTED"}
 if($V.contracts.live_trading_enabled){throw "LIVE TRADING ENABLED"}

 & $Python .\dashboard\verify_etrade_sandbox_order_v2_1_utf8.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V2.1 UTF8 VERIFY FAILED"}

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
