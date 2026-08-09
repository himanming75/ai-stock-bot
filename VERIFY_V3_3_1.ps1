$ErrorActionPreference="Stop"

$RunKey="HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$Name="AIStockBotOperationsDashboardV3"

Write-Host "=== V3.3.1 VERIFY USER AUTOSTART ==="

$Value=(Get-ItemProperty -Path $RunKey -Name $Name -ErrorAction Stop).$Name

if($Value -notmatch "START_DASHBOARD_V3_3.ps1"){
    throw "AUTOSTART ENTRY DOES NOT POINT TO V3.3 START SCRIPT"
}

Write-Host "AUTOSTART ENTRY: PASS"
Write-Host "VALUE:" $Value

Write-Host ""
Write-Host "=== DASHBOARD HEALTH FILE ==="

$Health="C:\stock-bot\runtime\dashboard_health_v3_3\latest_health_snapshot.json"

if(Test-Path $Health){
    $H=Get-Content $Health -Raw | ConvertFrom-Json
    Write-Host "HEALTH SNAPSHOT: PASS"
    Write-Host "ALERT SUMMARY:" ($H.summary | ConvertTo-Json -Compress)
}else{
    Write-Host "HEALTH SNAPSHOT: NOT YET PRESENT"
}

Write-Host ""
Write-Host "VERIFY: PASS"
