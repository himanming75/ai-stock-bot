$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root `
  "release\p1_actual_environment_qualification\actual"

Write-Host "=== P1 ACTUAL ENVIRONMENT RESULT ==="
Get-Content (
    Join-Path $Actual "p1_actual_environment_result.json"
)

Write-Host ""
Write-Host "=== P1 ACTUAL ENVIRONMENT CERTIFICATE ==="
Get-Content (
    Join-Path $Actual "p1_actual_environment_certificate.json"
)
