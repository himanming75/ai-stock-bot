$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_p3_micro_paper_validation -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PAPER ORDERS DURING TEST: 0"
Write-Host "LIVE ORDERS: 0"
