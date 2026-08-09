$ErrorActionPreference="Stop"
Set-Location C:\stock-bot
$Python="C:\stock-bot\.venv\Scripts\python.exe"
$env:PYTHONPATH="C:\stock-bot"
$Port=8891

$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}

$P=Start-Process -FilePath $Python -ArgumentList @(
 "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
 "--root","C:\stock-bot","--host","127.0.0.1","--port","$Port"
) -WorkingDirectory "C:\stock-bot" -PassThru

try{
 Start-Sleep -Seconds 6
 $S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status" -TimeoutSec 30
 $V=$S.broker_integration_v1.v2_etrade_readonly_oauth

 Write-Host "BROKER V1:" $S.broker_integration_v1.status
 Write-Host "BROKER V2:" $V.status
 Write-Host "DEVELOPMENT:" $V.development_status
 Write-Host "OAUTH STATUS:" $V.etrade_oauth_status
 Write-Host "SIGNATURE VECTOR:" $V.official_signature_vector_pass
 Write-Host "TOKEN PERSISTENCE:" $V.token_persistence
 Write-Host "LIVE:" $V.live_trading_status
 Write-Host "ORDER SUBMISSION:" $V.order_submission_status
 Write-Host "CANCEL/REPLACE:" $V.cancel_replace_status

 if($V.development_status -ne "COMPLETE"){throw "V2 DEVELOPMENT FAILED"}
 if(-not $V.official_signature_vector_pass){throw "OAUTH SIGNATURE VECTOR FAILED"}
 if($V.token_persistence -ne "DISABLED"){throw "TOKEN PERSISTENCE CONTRACT FAILED"}
 if($V.live_trading_status -ne "LOCKED"){throw "LIVE LOCK FAILED"}
 if($V.order_submission_status -ne "LOCKED"){throw "ORDER LOCK FAILED"}
 if($V.cancel_replace_status -ne "LOCKED"){throw "CANCEL/REPLACE LOCK FAILED"}
 if($V.contracts.duplicate_broker_contract_created){throw "DUPLICATE CONTRACT"}
 if($V.contracts.duplicate_etrade_readonly_adapter_created){throw "DUPLICATE ETRADE ADAPTER"}
 if($V.contracts.new_credential_vault_created){throw "DUPLICATE CREDENTIAL VAULT"}

 & $Python .\dashboard\verify_broker_integration_v2_utf8.py --url "http://127.0.0.1:$Port/"
 if($LASTEXITCODE -ne 0){throw "V2 UTF8 VERIFY FAILED"}

 Write-Host "VERIFY: PASS"
}
finally{
 Stop-Process -Id $P.Id -Force -ErrorAction SilentlyContinue
}
