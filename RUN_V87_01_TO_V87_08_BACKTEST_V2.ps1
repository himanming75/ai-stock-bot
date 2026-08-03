param(
    [string]$InputPath = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V87.01-V87.08 BACKTEST ENGINE V2 ==="
Write-Host "Local historical replay only. No API, network, broker write, or order submission."

$argsList = @()
if ($InputPath) {
    $argsList += "--input"
    $argsList += $InputPath
}

python tools\run_backtest_v2_v87_01_to_v87_08.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V87.01-V87.08 COMPLETE"
