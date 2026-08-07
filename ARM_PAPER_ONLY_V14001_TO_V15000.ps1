[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python .\tools\create_paper_arm_token.py
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

Write-Host "PAPER ONLY: ARMED"
Write-Host "LIVE SUBMISSION: OFF"
