$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "THIS SCRIPT CAN SUBMIT EXACTLY ONE REAL ALPACA PAPER ORDER."
Write-Host "It requires explicit environment opt-ins, Paper credentials, kill switch clear, and exact confirmation."
python tools/run_v95_01_to_v96_00_actual_single_order.py @args
exit $LASTEXITCODE
