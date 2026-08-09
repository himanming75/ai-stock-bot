$ErrorActionPreference="Stop"
$Repo="C:\stock-bot";$Port=8766;$Python="$Repo\.venv\Scripts\python.exe"
Set-Location $Repo
$Old=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
foreach($L in $Old){Stop-Process -Id $L.OwningProcess -Force -ErrorAction SilentlyContinue}
Start-Sleep -Seconds 2
$P=Start-Process -FilePath $Python -ArgumentList @("$Repo\dashboard\operations_dashboard_v3_2.py","--root","$Repo","--host","127.0.0.1","--port","$Port") -WorkingDirectory $Repo -PassThru
Start-Sleep -Seconds 6
$S=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/status"
$V=$S.broker_integration_v1.v2_etrade_readonly_oauth.sandbox_order_v2_1
Write-Host "DASHBOARD PID:" $P.Id
Write-Host "V2.1:" $V.status
Write-Host "ENVIRONMENT:" $V.environment
Write-Host "PROD ORDER POST:" $V.production_order_post_allowed
Write-Host "DASHBOARD RUNTIME: PASS"
