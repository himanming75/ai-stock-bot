$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\create_p3_micro_approval_token.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
