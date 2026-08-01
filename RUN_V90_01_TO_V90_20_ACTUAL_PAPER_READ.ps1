$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if($env:AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ=YES"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)){throw "APCA_API_KEY_ID is required"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)){throw "APCA_API_SECRET_KEY is required"}
python tools/run_v90_01_to_v90_20_actual_read.py
exit $LASTEXITCODE
