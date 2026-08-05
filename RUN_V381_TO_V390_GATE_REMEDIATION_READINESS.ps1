$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python `
    .\tools\run_v381_to_v390_gate_remediation_readiness.py `
    --repository-root "C:\stock-bot"

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}
