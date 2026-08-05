$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v861_to_v940_paper_recovery_retry.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
