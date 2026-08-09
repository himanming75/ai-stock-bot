$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

$Obsolete="INSTALL_DASHBOARD_AUTOSTART_V3_3.ps1"

Write-Host "=== V3.4 SAFE OBSOLETE FILE CLEANUP ==="

if(Test-Path $Obsolete){
    $Tracked=git ls-files -- "$Obsolete"
    if($Tracked){
        Write-Host "KEEP TRACKED FILE:" $Obsolete
    }else{
        Remove-Item $Obsolete -Force
        Write-Host "REMOVED OBSOLETE UNTRACKED FILE:" $Obsolete
    }
}else{
    Write-Host "OBSOLETE FILE ALREADY ABSENT"
}
