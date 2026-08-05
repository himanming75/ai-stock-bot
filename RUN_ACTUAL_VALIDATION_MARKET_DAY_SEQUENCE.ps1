param(
    [Parameter(Mandatory=$true)]
    [string]$ClientOrderId,
    [int]$TimeoutSeconds = 180,
    [int]$PollSeconds = 5
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== MARKET DAY ACTUAL VALIDATION SEQUENCE ==="
Write-Host "This script does NOT create the first Paper order."
Write-Host "It validates an explicitly submitted Paper order by ClientOrderId."

& (Join-Path $Root "RUN_ACTUAL_VALIDATION_MARKET_DAY_PREFLIGHT.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "Market day preflight failed."
}

& (Join-Path $Root "RUN_P2_P3_ACTUAL_VALIDATION.ps1") `
    -ClientOrderId $ClientOrderId `
    -TimeoutSeconds $TimeoutSeconds `
    -PollSeconds $PollSeconds
if ($LASTEXITCODE -ne 0) {
    throw "P2/P3 actual validation failed."
}

& (Join-Path $Root "RUN_ACTUAL_VALIDATION_CONTROL_STATUS.ps1")
Write-Host ""
Write-Host "P2/P3 validation completed."
Write-Host "Next: run P4 actual runtime, then RUN_P4_ACTUAL_VALIDATION_RECORD.ps1."
