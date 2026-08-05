$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskXmlPath = Join-Path $Root `
  "release\r2_windows_scheduler_service_preparation\actual\task_xml"

if (-not (Test-Path $TaskXmlPath)) {
    throw "R2 task XML directory is missing. Run R2 readiness first."
}

Write-Host "=== R2 TASK INSTALL PREVIEW ==="
Write-Host "No Windows tasks will be registered."
Write-Host ""

Get-ChildItem $TaskXmlPath -Filter "*.xml" |
ForEach-Object {
    Write-Host "Task XML:" $_.FullName
    Write-Host "Registration command preview:"
    Write-Host ('schtasks /Create /TN "<TASK_NAME>" /XML "' + $_.FullName + '"')
    Write-Host ""
}
