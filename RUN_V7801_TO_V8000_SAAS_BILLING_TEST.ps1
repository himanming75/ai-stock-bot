$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python -m unittest `
    tools.test_v7801_to_v8000_saas_billing `
    -v

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "TEST: PASS"
Write-Host "SAAS BILLING FOUNDATION: READY"
Write-Host "PLAN AND USAGE LIMITS: READY"
Write-Host "PRODUCTION DEPLOYMENT TEMPLATES: READY"
Write-Host "STRIPE EXTERNAL CHARGES: OFF"
Write-Host "CLOUD DEPLOYMENT: NOT PERFORMED"
Write-Host "BROKER WRITE: OFF"
Write-Host "PAPER ORDERS: 0"
Write-Host "LIVE ORDERS: 0"
