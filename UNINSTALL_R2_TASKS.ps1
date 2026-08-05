$ErrorActionPreference = "Stop"

$TaskNames = @(
    "AIStockBot-Runtime-DISABLED",
    "AIStockBot-HealthMonitor-DISABLED",
    "AIStockBot-DailyReport-DISABLED"
)

Write-Host "=== R2 TASK UNINSTALL PREVIEW ==="
Write-Host "No Windows tasks will be deleted automatically."

foreach ($TaskName in $TaskNames) {
    Write-Host ('schtasks /Delete /TN "' + $TaskName + '" /F')
}
