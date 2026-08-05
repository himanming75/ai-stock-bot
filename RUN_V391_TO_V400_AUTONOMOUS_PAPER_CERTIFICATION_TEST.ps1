$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v391_to_v400_autonomous_paper_certification `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PAPER SUBMISSION: OFF"
Write-Host "LIVE SUBMISSION: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
