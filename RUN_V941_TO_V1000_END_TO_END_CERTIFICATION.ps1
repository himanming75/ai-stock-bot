$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python `
    .\tools\run_v941_to_v1000_end_to_end_certification.py `
    --repository-root "."
if($LASTEXITCODE -ne 0){
    Write-Host "CERTIFICATION BLOCKED OR INCOMPLETE"
    exit $LASTEXITCODE
}
