[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$TaskName = "AIStockBot-PaperAutonomousDailySession"

Disable-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction Stop | Out-Null

Write-Host "TASK DISABLE: PASS"
