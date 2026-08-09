$ErrorActionPreference="Stop"

$RunKey="HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$Name="AIStockBotOperationsDashboardV3"
$Command='powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\stock-bot\START_DASHBOARD_V3_3.ps1"'

Write-Host "=== V3.3.1 USER AUTOSTART INSTALL ==="

if(-not(Test-Path "C:\stock-bot\START_DASHBOARD_V3_3.ps1")){
    throw "START SCRIPT NOT FOUND"
}

if(-not(Test-Path $RunKey)){
    New-Item -Path $RunKey -Force | Out-Null
}

New-ItemProperty `
    -Path $RunKey `
    -Name $Name `
    -Value $Command `
    -PropertyType String `
    -Force | Out-Null

$Saved=(Get-ItemProperty -Path $RunKey -Name $Name).$Name

Write-Host "AUTOSTART METHOD: HKCU RUN"
Write-Host "ENTRY NAME:" $Name
Write-Host "ENTRY VALUE:" $Saved
Write-Host "ADMIN REQUIRED: false"
Write-Host "INSTALL: PASS"
