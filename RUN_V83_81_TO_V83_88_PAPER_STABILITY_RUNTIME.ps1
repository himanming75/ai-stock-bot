param(
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.81-V83.88 PAPER STABILITY AND RUNTIME READINESS ==="
Write-Host "Certification remains pending until three unique validation days exist."

$argsList = @()
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_paper_stability_runtime_v83_81_to_v83_88.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.81-V83.88 COMPLETE"
