$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Actual = Join-Path $Root "release\p2_actual_paper_broker_read\actual"

Write-Host "=== P2 RESULT ==="
Get-Content (Join-Path $Actual "p2_actual_broker_read_result.json")

Write-Host ""
Write-Host "=== P2 CERTIFICATE ==="
Get-Content (Join-Path $Actual "p2_actual_broker_read_certificate.json")
