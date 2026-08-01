$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "This script performs READ-ONLY validation of one existing Alpaca PAPER order."
python tools/run_v96_01_to_v97_00_actual_validation.py @args
exit $LASTEXITCODE
