$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Result = Join-Path $Root `
  "release\bundle_c_r14_to_r15_final_operations\actual\bundle_c_result.json"
$Gate = Join-Path $Root `
  "release\bundle_c_r14_to_r15_final_operations\actual\final_release_gate.json"

if (-not (Test-Path $Result)) {
    throw "Bundle C result is missing."
}

Write-Host "=== FINAL PROJECT STATUS ==="
Get-Content $Result
Write-Host ""
Write-Host "=== FINAL RELEASE GATE ==="
Get-Content $Gate
