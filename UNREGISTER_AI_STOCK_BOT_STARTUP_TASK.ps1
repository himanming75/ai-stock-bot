param(
    [string]$TaskName="AI Stock Bot Daily Session"
)

$ErrorActionPreference="Stop"

$Task=Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

if($null -eq $Task){
    Write-Host "TASK NOT FOUND: $TaskName"
    exit 0
}

Unregister-ScheduledTask `
    -TaskName $TaskName `
    -Confirm:$false

Write-Host "STARTUP TASK REMOVED"
Write-Host "Task Name: $TaskName"
