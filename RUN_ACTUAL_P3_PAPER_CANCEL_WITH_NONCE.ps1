param(
    [Parameter(Mandatory=$true)]
    [string]$Nonce
)

$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

. .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

if($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets"){
    throw "NON-PAPER ENDPOINT BLOCKED"
}

python .\tools\run_p3_paper_cancel_validation.py `
    --nonce $Nonce `
    --poll-interval-seconds 1 `
    --max-poll-cycles 20

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
