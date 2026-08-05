param(
    [int]$IntervalSeconds=5,
    [int]$MaxCycles=12
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
    throw "NON-PAPER ENDPOINT BLOCKED"
}

python .\tools\run_paper_order_lifecycle_monitor.py `
    --interval-seconds $IntervalSeconds `
    --max-cycles $MaxCycles

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
