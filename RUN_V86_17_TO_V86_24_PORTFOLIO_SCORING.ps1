param(
    [string]$InputPath = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V86.17-V86.24 PORTFOLIO SCORING ENGINE ==="
Write-Host "Local portfolio ranking only. No API, network, broker write, or order submission."

$argsList = @()
if ($InputPath) {
    $argsList += "--input"
    $argsList += $InputPath
}

python tools\run_portfolio_scoring_v86_17_to_v86_24.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.17-V86.24 COMPLETE"
