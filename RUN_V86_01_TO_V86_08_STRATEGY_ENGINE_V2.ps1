param(
    [string]$InputPath = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V86.01-V86.08 AI STRATEGY ENGINE V2 ==="
Write-Host "Local decision engine only. No API, network, broker write, or order submission."

$argsList = @()
if ($InputPath) {
    $argsList += "--input"
    $argsList += $InputPath
}

python tools\run_strategy_engine_v2_v86_01_to_v86_08.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.01-V86.08 COMPLETE"
