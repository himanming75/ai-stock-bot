$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root `
  "release\validation_support_mega_bundle\actual"

Write-Host "=== VALIDATION SUPPORT RESULT ==="
Get-Content (
    Join-Path $Actual "validation_support_result.json"
)

Write-Host ""
Write-Host "=== VALIDATION SUPPORT REPORT ==="
Get-Content (
    Join-Path $Actual "validation_support_report.json"
)
