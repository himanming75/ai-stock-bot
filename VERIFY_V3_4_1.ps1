$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Python="C:\stock-bot\.venv\Scripts\python.exe"
$TestPort=8874

Write-Host "=== V3.4.1 DIRECT-SCRIPT SERVER VERIFY ==="

$Existing=@(
    Get-NetTCPConnection `
        -LocalPort $TestPort `
        -State Listen `
        -ErrorAction SilentlyContinue
)

foreach($L in $Existing){
    Stop-Process `
        -Id $L.OwningProcess `
        -Force `
        -ErrorAction SilentlyContinue
}

$Proc=Start-Process `
    -FilePath $Python `
    -ArgumentList @(
        "C:\stock-bot\dashboard\operations_dashboard_v3_2.py",
        "--root", "C:\stock-bot",
        "--host", "127.0.0.1",
        "--port", "$TestPort"
    ) `
    -WorkingDirectory "C:\stock-bot" `
    -PassThru

try{
    Start-Sleep -Seconds 3

    $Status=Invoke-RestMethod `
        -Uri "http://127.0.0.1:$TestPort/api/status" `
        -TimeoutSec 10

    Write-Host "VISUALIZATION STATUS:" $Status.visualization_status
    Write-Host "EQUITY POINTS:" $Status.visualization.summary.equity_point_count
    Write-Host "DAILY PNL POINTS:" $Status.visualization.summary.daily_realized_point_count
    Write-Host "VALIDATION SLOTS:" $Status.visualization.validation_slots.Count
    Write-Host "CURRENT UNREALIZED:" $Status.visualization.summary.current_unrealized_pnl

    if($Status.visualization_status -ne "PASS"){
        throw "VISUALIZATION STATUS IS NOT PASS"
    }

    if($Status.visualization.validation_slots.Count -ne 10){
        throw "VALIDATION SLOT COUNT IS NOT 10"
    }

    Write-Host "DIRECT SERVER VERIFY: PASS"
}
finally{
    Stop-Process `
        -Id $Proc.Id `
        -Force `
        -ErrorAction SilentlyContinue
}

Write-Host "VERIFY: PASS"
