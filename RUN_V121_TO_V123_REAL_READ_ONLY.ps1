$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== ALPACA PAPER REAL READ-ONLY CONNECTION ==="
Write-Host "Policy file will NOT be modified."

if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_API_KEY)){
    throw "ALPACA_PAPER_API_KEY is not set."
}
if([string]::IsNullOrWhiteSpace($env:ALPACA_PAPER_SECRET_KEY)){
    throw "ALPACA_PAPER_SECRET_KEY is not set."
}

$PreviousOverride=$env:ALPACA_ALLOW_REAL_PAPER_NETWORK
try {
    $env:ALPACA_ALLOW_REAL_PAPER_NETWORK="YES"
    python tools\run_v121_01_to_v123_64.py --real-network
    if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
}
finally {
    if($null -eq $PreviousOverride){
        Remove-Item Env:\ALPACA_ALLOW_REAL_PAPER_NETWORK -ErrorAction SilentlyContinue
    } else {
        $env:ALPACA_ALLOW_REAL_PAPER_NETWORK=$PreviousOverride
    }
}
