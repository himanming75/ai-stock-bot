param([string]$TaskName = "AIStockBot-ReadOnly-Collector")
$ErrorActionPreference = "Stop"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "TASK_NOT_FOUND=$TaskName"
    exit 0
}
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "TASK_REMOVED=$TaskName"
