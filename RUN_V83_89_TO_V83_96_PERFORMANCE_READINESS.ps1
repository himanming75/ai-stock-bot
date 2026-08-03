param(
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.89-V83.96 PERFORMANCE AND PRODUCTION READINESS ==="
Write-Host "Pending is valid until stability certification and paper metrics are ready."

$argsList = @()
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_performance_production_readiness_v83_89_to_v83_96.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.89-V83.96 COMPLETE"
