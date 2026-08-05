$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
python .\tools\run_v1201_to_v1400_multi_strategy_ensemble.py
if($LASTEXITCODE -ne 0){
    Write-Host "ENSEMBLE BLOCKED BY UPSTREAM FEATURE INPUT"
    exit $LASTEXITCODE
}
