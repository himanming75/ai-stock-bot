$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v691_to_v780_approval_submission_safety.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
