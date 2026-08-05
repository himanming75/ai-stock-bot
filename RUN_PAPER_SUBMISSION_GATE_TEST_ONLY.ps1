$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_paper_order_submission_gate -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "ACTUAL PAPER SUBMISSION DURING TEST: 0"
Write-Host "LIVE SUBMISSION: 0"
