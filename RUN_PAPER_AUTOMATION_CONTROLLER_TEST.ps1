$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest tools.test_paper_automation_controller -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "ACTUAL PAPER SUBMISSION: OFF"
Write-Host "LIVE SUBMISSION: OFF"
