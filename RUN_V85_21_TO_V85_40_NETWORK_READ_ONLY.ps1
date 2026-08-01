$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if($env:AI_STOCK_BOT_ENABLE_PAPER_READ_ONLY -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_PAPER_READ_ONLY=YES explicitly."}
if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)){throw "Missing APCA_API_KEY_ID"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)){throw "Missing APCA_API_SECRET_KEY"}
python tools/run_v85_21_to_v85_40_pipeline.py --repository-root . --clean --enable-network
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v85_21_to_v85_40_pipeline.py --repository-root .
