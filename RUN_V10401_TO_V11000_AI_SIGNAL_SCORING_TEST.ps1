[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v10401_to_v11000_ai_signal_scoring `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "TEST: PASS"
Write-Host "AI ENSEMBLE SCORING: READY"
Write-Host "EXPLAINABILITY: READY"
Write-Host "BACKTEST BRIDGE: READY"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
