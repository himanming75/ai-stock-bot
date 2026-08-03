param(
    [switch]$Certify,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.65-V83.68 END-TO-END PAPER CERTIFICATION ==="
Write-Host "Certification only. No broker or network write."

$argsList = @()
if ($Certify) { $argsList += "--certify" }
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.65-V83.68 COMPLETE"
