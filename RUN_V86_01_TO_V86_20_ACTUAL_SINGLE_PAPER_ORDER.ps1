$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if($env:AI_STOCK_BOT_ENABLE_PAPER_NETWORK -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_PAPER_NETWORK=YES"}
if($env:AI_STOCK_BOT_ENABLE_SINGLE_PAPER_ORDER -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_SINGLE_PAPER_ORDER=YES"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)){throw "Missing APCA_API_KEY_ID"}
if([string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)){throw "Missing APCA_API_SECRET_KEY"}
python tools/run_v86_01_to_v86_20_pipeline.py --repository-root . --clean --enable-network --enable-order
python tools/verify_v86_01_to_v86_20_pipeline.py --repository-root .
