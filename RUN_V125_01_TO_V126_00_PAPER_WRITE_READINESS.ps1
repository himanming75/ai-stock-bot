$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== PAPER WRITE READINESS CERTIFICATION ==="
Write-Host "This certifies readiness only. It does not submit any order."

if ($env:AI_STOCK_BOT_ENABLE_PAPER_WRITE_READINESS -ne "YES") {
    throw "Set AI_STOCK_BOT_ENABLE_PAPER_WRITE_READINESS=YES"
}
if ($env:AI_STOCK_BOT_PAPER_WRITE_READINESS_CONFIRMATION -ne "AUTHORIZE PAPER WRITE READINESS ONLY NO ORDER SUBMISSION") {
    throw "Set the exact Paper write readiness confirmation text."
}

python tools/run_paper_write_readiness_v125_01_to_v126_00.py `
    --repository-root .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "PAPER WRITE READINESS CERTIFIED - NO ORDER WAS SUBMITTED"
