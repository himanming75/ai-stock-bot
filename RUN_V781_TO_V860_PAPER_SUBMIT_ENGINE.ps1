$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v781_to_v860_paper_submit_engine.py

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
