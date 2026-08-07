[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

$env:APCA_API_KEY_ID=[Environment]::GetEnvironmentVariable("APCA_API_KEY_ID","User")
$env:APCA_API_SECRET_KEY=[Environment]::GetEnvironmentVariable("APCA_API_SECRET_KEY","User")

& $Python .\tools\ingest_alpaca_real_historical.py --root $PSScriptRoot
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

& $Python .\tools\run_existing_offline_engine_on_real_history.py --root $PSScriptRoot
exit $LASTEXITCODE
