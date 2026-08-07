[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if(Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}
else {
    $Python = "python"
}

& $Python .\tools\run_market_open_auto_validation.py `
    --repository-root $PSScriptRoot `
    --poll-seconds 10 `
    --timeout-minutes 1 `
    --dry-run

exit $LASTEXITCODE
