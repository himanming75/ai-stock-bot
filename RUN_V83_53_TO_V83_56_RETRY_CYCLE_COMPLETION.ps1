param(
    [switch]$Finalize,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.53-V83.56 RETRY CYCLE COMPLETION ==="
Write-Host "Classification and certificate only. No broker write."

$argsList = @()
if ($Finalize) { $argsList += "--finalize" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_retry_cycle_completion_v83_53_to_v83_56.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.53-V83.56 COMPLETE"
