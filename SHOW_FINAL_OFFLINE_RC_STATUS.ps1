$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root "release\final_offline_release_candidate\actual"

Write-Host "=== FINAL OFFLINE RC AUDIT ==="
Get-Content (Join-Path $Actual "final_offline_rc_audit_result.json")

Write-Host ""
Write-Host "=== FINAL OFFLINE RC CERTIFICATE ==="
Get-Content (Join-Path $Actual "final_offline_rc_certificate.json")

Write-Host ""
Write-Host "=== FINAL OFFLINE RC BUNDLE ==="
Get-Content (Join-Path $Actual "final_offline_rc_bundle.json")
