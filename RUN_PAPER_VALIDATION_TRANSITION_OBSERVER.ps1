[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$env:APCA_API_KEY_ID=[Environment]::GetEnvironmentVariable("APCA_API_KEY_ID","User")
$env:APCA_API_SECRET_KEY=[Environment]::GetEnvironmentVariable("APCA_API_SECRET_KEY","User")
$env:LIVE_TRADING_ENABLED="false"
$env:ETRADE_LIVE_WRITE_ENABLED="false"
$env:ETRADE_LIVE_SUBMISSION_ENABLED="false"
$env:BROKER_WRITE_ENABLED="false"

$Python=if(Test-Path ".\.venv\Scripts\python.exe"){".\.venv\Scripts\python.exe"}else{"python"}

& $Python .\tools\paper_validation_transition_observer.py --root $PSScriptRoot
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}

& $Python .\tools\paper_first_session_start_confirmation.py --root $PSScriptRoot
exit $LASTEXITCODE
