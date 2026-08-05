$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python .\tools\create_paper_submission_approval_token.py
if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
