$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v6601_to_v6800_autonomous_final_certification.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
