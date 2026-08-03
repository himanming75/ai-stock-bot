param(
    [string]$InputPath = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V86.09-V86.16 INDICATOR ENGINE ==="
Write-Host "Local OHLCV calculations only. No API, network, broker write, or order submission."

$argsList = @()
if ($InputPath) {
    $argsList += "--input"
    $argsList += $InputPath
}

python tools\run_indicator_engine_v86_09_to_v86_16.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V86.09-V86.16 COMPLETE"
