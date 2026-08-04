param(
    [string]$TaskName="AI Stock Bot Daily Paper Trading"
)
$ErrorActionPreference="Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "TASK REMOVED: $TaskName"
