$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

if(
    [string]::IsNullOrWhiteSpace(
        $env:AI_STOCK_BOT_SUBMISSION_SECRET
    )
){
    throw "AI_STOCK_BOT_SUBMISSION_SECRET is required."
}

python `
    .\tools\create_v691_to_v780_approval_token.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
