$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_API_KEY)){throw "PAPER KEY MISSING"}
if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_SECRET_KEY)){throw "PAPER SECRET MISSING"}
$old=$env:ALPACA_ALLOW_REAL_PAPER_NETWORK
try{
 $env:ALPACA_ALLOW_REAL_PAPER_NETWORK="YES"
 python tools\run_v124_01_to_v126_64.py --real-network
 if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
}finally{
 if($null-eq$old){Remove-Item Env:\ALPACA_ALLOW_REAL_PAPER_NETWORK -ErrorAction SilentlyContinue}
 else{$env:ALPACA_ALLOW_REAL_PAPER_NETWORK=$old}
}
