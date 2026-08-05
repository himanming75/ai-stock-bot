$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "R2 graceful stop preparation"
Write-Host "No process is terminated automatically."

$Marker = Join-Path $Root `
  "release\r2_windows_scheduler_service_preparation\actual\operator_stop_request.json"

@{
    stage = "R2_OPERATOR_STOP_REQUEST"
    requested_at = [DateTimeOffset]::UtcNow.ToString("o")
    automatic_process_termination_enabled = $false
    automatic_order_replay_enabled = $false
    operator_review_required = $true
} |
ConvertTo-Json -Depth 5 |
Set-Content $Marker -Encoding UTF8

Write-Host "Stop request marker written:"
Write-Host $Marker
