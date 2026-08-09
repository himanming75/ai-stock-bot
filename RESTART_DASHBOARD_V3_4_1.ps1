$ErrorActionPreference="Stop"

$Repo="C:\stock-bot"
$Port=8766
$Python="$Repo\.venv\Scripts\python.exe"

Set-Location $Repo

Write-Host "=== RESTART V3 DASHBOARD ON 8766 ==="

$Listeners=@(
    Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue
)

foreach($L in $Listeners){
    Write-Host "Stopping PID:" $L.OwningProcess
    Stop-Process `
        -Id $L.OwningProcess `
        -Force `
        -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 2

$Proc=Start-Process `
    -FilePath $Python `
    -ArgumentList @(
        "$Repo\dashboard\operations_dashboard_v3_2.py",
        "--root", "$Repo",
        "--host", "127.0.0.1",
        "--port", "$Port"
    ) `
    -WorkingDirectory $Repo `
    -PassThru

Start-Sleep -Seconds 4

$Status=Invoke-RestMethod `
    -Uri "http://127.0.0.1:$Port/api/status"

Write-Host "DASHBOARD PID:" $Proc.Id
Write-Host "VISUALIZATION STATUS:" $Status.visualization_status
Write-Host "EQUITY POINTS:" $Status.visualization.summary.equity_point_count
Write-Host "VALIDATION SLOTS:" $Status.visualization.validation_slots.Count
Write-Host "CURRENT UNREALIZED:" $Status.visualization.summary.current_unrealized_pnl

if($Status.visualization_status -ne "PASS"){
    throw "V3.4.1 DASHBOARD RUNTIME VERIFY FAILED"
}

Write-Host "DASHBOARD RUNTIME: PASS"
