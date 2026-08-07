[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$StopFile = Join-Path `
    $PSScriptRoot `
    "runtime\paper_autonomous_daily_session\STOP"

New-Item `
    -ItemType File `
    -Path $StopFile `
    -Force | Out-Null

Write-Host "STOP REQUEST: WRITTEN"
Write-Host "THE SESSION WILL STOP ON THE NEXT POLL"
