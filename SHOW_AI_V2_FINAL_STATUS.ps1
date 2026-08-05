$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Result = Join-Path $Root `
  "release\ai_v2_final\actual\ai_v2_final_result.json"
$Certificate = Join-Path $Root `
  "release\ai_v2_final\actual\ai_v2_final_certificate.json"

Write-Host "=== AI V2 FINAL RESULT ==="
Get-Content $Result
Write-Host ""
Write-Host "=== AI V2 FINAL CERTIFICATE ==="
Get-Content $Certificate
