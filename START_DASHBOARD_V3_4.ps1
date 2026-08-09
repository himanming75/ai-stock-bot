$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Port=8766
$Existing=@(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
)

if($Existing.Count -gt 0){
    Write-Host "V3 dashboard is already running on port 8766."
    Write-Host "Restart that dashboard process to load V3.4 visuals."
    exit 0
}

powershell -NoProfile -ExecutionPolicy Bypass -File .\START_DASHBOARD_V3_3.ps1
