$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "This can submit automated orders to the Alpaca PAPER account only."
$answer=Read-Host "Type AUTO PAPER to continue"
if($answer-ne "AUTO PAPER"){throw "CANCELLED"}
if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_API_KEY)){throw "PAPER KEY MISSING"}
if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_SECRET_KEY)){throw "PAPER SECRET MISSING"}
$oldNet=$env:ALPACA_ALLOW_REAL_PAPER_NETWORK
$oldOrder=$env:ALPACA_ALLOW_AUTOMATED_PAPER_ORDERS
try{
 $env:ALPACA_ALLOW_REAL_PAPER_NETWORK="YES"
 $env:ALPACA_ALLOW_AUTOMATED_PAPER_ORDERS="YES"
 python tools\run_v124_01_to_v126_64.py --real-network --submit-paper
 if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
}finally{
 if($null-eq$oldNet){Remove-Item Env:\ALPACA_ALLOW_REAL_PAPER_NETWORK -ErrorAction SilentlyContinue}else{$env:ALPACA_ALLOW_REAL_PAPER_NETWORK=$oldNet}
 if($null-eq$oldOrder){Remove-Item Env:\ALPACA_ALLOW_AUTOMATED_PAPER_ORDERS -ErrorAction SilentlyContinue}else{$env:ALPACA_ALLOW_AUTOMATED_PAPER_ORDERS=$oldOrder}
}
