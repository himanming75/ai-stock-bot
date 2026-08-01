$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if($env:AI_STOCK_BOT_ENABLE_PAPER_RECONCILIATION_READ -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_PAPER_RECONCILIATION_READ=YES"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)){throw "Missing APCA_API_KEY_ID"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)){throw "Missing APCA_API_SECRET_KEY"}
if([string]::IsNullOrWhiteSpace($env:AI_STOCK_BOT_PAPER_ORDER_ID) -and [string]::IsNullOrWhiteSpace($env:AI_STOCK_BOT_PAPER_CLIENT_ORDER_ID)){throw "Set order ID or client order ID"}
python tools/run_v86_41_to_v86_60_pipeline.py --repository-root . --clean --enable-network
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
python tools/verify_v86_41_to_v86_60_pipeline.py --repository-root .
