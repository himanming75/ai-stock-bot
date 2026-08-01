$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if($env:AI_STOCK_BOT_ENABLE_PAPER_LIFECYCLE_READ -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_PAPER_LIFECYCLE_READ=YES"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)){throw "Missing APCA_API_KEY_ID"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)){throw "Missing APCA_API_SECRET_KEY"}
if([string]::IsNullOrWhiteSpace($env:AI_STOCK_BOT_PAPER_ORDER_ID) -and [string]::IsNullOrWhiteSpace($env:AI_STOCK_BOT_PAPER_CLIENT_ORDER_ID)){throw "Set order ID or client order ID"}
python tools/run_v86_21_to_v86_40_pipeline.py --repository-root . --clean --enable-network
python tools/verify_v86_21_to_v86_40_pipeline.py
