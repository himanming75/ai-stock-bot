$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v391_to_v400_autonomous_paper_certification.py `
    --repository-root "C:\stock-bot"

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
