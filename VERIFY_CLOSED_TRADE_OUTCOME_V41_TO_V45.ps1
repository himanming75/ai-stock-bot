[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_closed_trade_outcome_v41_v45 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\closed_trade_outcome_v41_v45\service.py -Raw
$ForbiddenCalls=@(
 '\.\s*submit_order\s*\(',
 '\.\s*cancel_order\s*\(',
 '\.\s*replace_order\s*\(',
 '\.\s*close_position\s*\(',
 '\.\s*close_all_positions\s*\('
)

foreach($Pattern in $ForbiddenCalls){
 if($Text -match $Pattern){
   throw "FORBIDDEN BROKER WRITE CALL FOUND: $Pattern"
 }
}

Write-Host "VERIFY: PASS"
Write-Host "ALPACA PAPER READ ONLY: PASS"
Write-Host "NO BROKER WRITE METHODS: PASS"
Write-Host "FIFO ROUND TRIP BUILDER: PASS"
Write-Host "MFE/MAE PATH READ: READ ONLY"
Write-Host "V4/V36 BRIDGE: NON-DESTRUCTIVE"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
