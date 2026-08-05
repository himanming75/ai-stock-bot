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

python .\tools\run_p3_micro_paper_validation.py --nonce $Nonce

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
