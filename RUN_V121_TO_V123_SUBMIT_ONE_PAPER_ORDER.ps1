$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== ALPACA PAPER ONE-ORDER TEST ==="
Write-Host "This can submit ONE order to the Alpaca PAPER account."
Write-Host "The Live Alpaca API domain is not used."
Write-Host "Policy file will NOT be modified."

if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_API_KEY)){
    throw "ALPACA_PAPER_API_KEY is not set."
}
if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_SECRET_KEY)){
    throw "ALPACA_PAPER_SECRET_KEY is not set."
}

$Answer=Read-Host "Type PAPER to continue"
if($Answer-ne "PAPER"){
    throw "CANCELLED"
}

$PreviousNetworkOverride=$env:ALPACA_ALLOW_REAL_PAPER_NETWORK
$PreviousOrderOverride=$env:ALPACA_ALLOW_ONE_PAPER_ORDER
try {
    $env:ALPACA_ALLOW_REAL_PAPER_NETWORK="YES"
    $env:ALPACA_ALLOW_ONE_PAPER_ORDER="YES"
    python tools\run_v121_01_to_v123_64.py `
        --real-network `
        --submit-paper-order
    if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
}
finally {
    if($null -eq $PreviousNetworkOverride){
        Remove-Item Env:\ALPACA_ALLOW_REAL_PAPER_NETWORK -ErrorAction SilentlyContinue
    } else {
        $env:ALPACA_ALLOW_REAL_PAPER_NETWORK=$PreviousNetworkOverride
    }

    if($null -eq $PreviousOrderOverride){
        Remove-Item Env:\ALPACA_ALLOW_ONE_PAPER_ORDER -ErrorAction SilentlyContinue
    } else {
        $env:ALPACA_ALLOW_ONE_PAPER_ORDER=$PreviousOrderOverride
    }
}
