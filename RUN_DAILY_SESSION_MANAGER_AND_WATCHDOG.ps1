$ErrorActionPreference = "Stop"
Set-Location "C:\stock-bot"

$Python = "C:\stock-bot\.venv\Scripts\python.exe"
$LogDirectory = "C:\stock-bot\release\daily_session_manager_startup_autorun\actual"
$LogPath = Join-Path $LogDirectory "scheduled_task_run.log"

New-Item `
    -ItemType Directory `
    -Path $LogDirectory `
    -Force | Out-Null

Start-Transcript `
    -Path $LogPath `
    -Append `
    -Force

try {
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "VENV PYTHON NOT FOUND: $Python"
    }

    . .\IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1 -Mode paper

    if ($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets") {
        throw "NON-PAPER ENDPOINT BLOCKED"
    }

    & $Python `
        .\tools\run_daily_session_manager.py `
        --execute-watchdog

    if ($LASTEXITCODE -ne 0) {
        throw "Daily Session Manager failed with exit code $LASTEXITCODE"
    }

    Write-Host "DAILY SESSION TASK: PASS"
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Stop-Transcript
}