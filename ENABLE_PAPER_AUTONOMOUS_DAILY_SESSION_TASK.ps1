[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$TaskName = "AIStockBot-PaperAutonomousDailySession"

Enable-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction Stop | Out-Null

Write-Host "TASK ENABLE: PASS"
Write-Host "THE TASK WILL START AT THE NEXT WINDOWS LOGON"
