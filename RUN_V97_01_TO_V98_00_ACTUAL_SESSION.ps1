$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "This starts one controlled Alpaca PAPER session. It does not submit an order by itself."
python tools/run_v97_01_to_v98_00_actual_session.py @args
exit $LASTEXITCODE
