param(
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V88.09-V88.16 PAPER AUTOMATION ORCHESTRATOR ==="
Write-Host "Manual local cycle only. No scheduler, external network, broker write, or order submission."

$argsList = @()
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools\run_paper_orchestrator_v88_09_to_v88_16.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V88.09-V88.16 COMPLETE"
