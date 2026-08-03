param(
    [string]$ValidationDate = "",
    [string]$ObservedAt = "",
    [int]$MinimumDays = 3,
    [switch]$ResetLedger
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.77-V83.80 MULTI-DAY PAPER VALIDATION ==="
Write-Host "Manual date advancement only. No wait loop, scheduler, network, or broker write."

$argsList = @("--minimum-days", "$MinimumDays")
if ($ValidationDate) {
    $argsList += "--validation-date"
    $argsList += $ValidationDate
}
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}
if ($ResetLedger) {
    $argsList += "--reset-ledger"
}

python tools/run_multi_day_paper_validation_v83_77_to_v83_80.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.77-V83.80 COMPLETE"
