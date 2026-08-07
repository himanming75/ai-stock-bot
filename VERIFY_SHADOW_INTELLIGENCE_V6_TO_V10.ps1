[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest `
  tools.test_shadow_intelligence_v6_v10 `
  -v

if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Text = Get-Content .\shadow_intelligence_v6_v10\service.py -Raw
$ForbiddenCalls = @(
  '\.\s*submit_order\s*\(',
  '\.\s*cancel_order\s*\(',
  '\.\s*replace_order\s*\(',
  '\.\s*close_position\s*\(',
  '\.\s*close_all_positions\s*\('
)

foreach($Pattern in $ForbiddenCalls) {
    if($Text -match $Pattern) {
        throw "FORBIDDEN BROKER WRITE CALL FOUND: $Pattern"
    }
}

Write-Host "VERIFY: PASS"
Write-Host "NO BROKER WRITE METHODS: PASS"
Write-Host "MULTI-TIMEFRAME: OBSERVATION ONLY"
Write-Host "MARKET REGIME: OBSERVATION ONLY"
Write-Host "POSITION QUALITY: ADVISORY ONLY"
Write-Host "CURRENT PAPER SESSION UNAFFECTED: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
