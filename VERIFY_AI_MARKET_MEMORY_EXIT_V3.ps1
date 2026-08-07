[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest `
  tools.test_ai_market_memory_exit_v3 `
  -v

if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Text = Get-Content .\ai_market_memory_v3\service.py -Raw

# Match actual method/function calls only.
# Safe report fields such as cancel_orders_submitted must not trigger.
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
Write-Host "EXIT ADVISORY ONLY: PASS"
Write-Host "CURRENT PAPER SESSION UNAFFECTED: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
