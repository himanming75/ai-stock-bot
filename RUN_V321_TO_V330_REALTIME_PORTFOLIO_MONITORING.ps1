param(
    [int]$IntervalSeconds=10,
    [int]$MaxCycles=2
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if(
    $env:APCA_API_BASE_URL `
    -ne "https://paper-api.alpaca.markets"
){
    throw "NON-PAPER ENDPOINT BLOCKED"
}

python `
    .\tools\run_v321_to_v330_realtime_portfolio_monitoring.py `
    --interval-seconds $IntervalSeconds `
    --max-cycles $MaxCycles

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
