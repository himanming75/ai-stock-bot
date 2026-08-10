$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo
$Poll=60
$MaxSeconds=28800
$Start=Get-Date
$StopFile="$Repo\runtime\threshold_sensitivity_shadow_audit_v2_1_31_4\STOP_CONTINUOUS_AUDIT"

New-Item -ItemType Directory -Force (Split-Path -Parent $StopFile) | Out-Null
if(Test-Path $StopFile){Remove-Item $StopFile -Force}

Write-Host "V2.1.31.4 CONTINUOUS THRESHOLD SHADOW AUDIT"
Write-Host "Poll: 60 sec | Max: 8 hours"
Write-Host "Actual execution threshold remains 0.75"
Write-Host "Orders from audit: NONE"

while($true){
    if(Test-Path $StopFile){
        Write-Host "STOP FILE DETECTED"
        break
    }
    if(((Get-Date)-$Start).TotalSeconds -ge $MaxSeconds){
        Write-Host "MAX RUNTIME REACHED"
        break
    }

    powershell -NoProfile -ExecutionPolicy Bypass `
      -File "$Repo\START_V2_1_31_4_CAPTURE_AND_AUDIT.ps1"

    Start-Sleep -Seconds $Poll
}
