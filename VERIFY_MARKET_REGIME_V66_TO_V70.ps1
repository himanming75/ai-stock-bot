[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$OutputEncoding=[System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$Python=Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)){ throw "VENV PYTHON NOT FOUND: $Python" }

& $Python -m unittest `
  tools.test_market_regime_v66_v70 `
  -v

if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

$Text=Get-Content .\market_regime_v66_v70\service.py -Raw
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
Write-Host "MARKET REGIME: READ ONLY"
Write-Host "ENVIRONMENT SNAPSHOT: READ ONLY"
Write-Host "TRADE CONTEXT LINKER: NON-DESTRUCTIVE"
Write-Host "REGIME PERFORMANCE: ANALYTICS ONLY"
Write-Host "AUTOMATIC REGIME WEIGHTING: OFF"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
