$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
  tools.test_v8801_to_v9000_paper_command_center `
  -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "PAPER COMMAND CENTER: READY"
Write-Host "COMMAND PLANS: DRY RUN ONLY"
Write-Host "PROCESS START/STOP: OFF"
Write-Host "BROKER WRITE: OFF"
Write-Host "ORDER SUBMISSION: OFF"
