param(
    [switch]$DryRun
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\stock-bot"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$RuntimeFolder = Join-Path $ProjectRoot "runtime\market_open_auto_validation"
$TaskLog = Join-Path $RuntimeFolder "task_scheduler_execution.log"

New-Item `
    -ItemType Directory `
    -Path $RuntimeFolder `
    -Force | Out-Null

Set-Location $ProjectRoot

function Write-TaskLog {
    param([string]$Message)

    $Line = (
        (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") +
        " " +
        $Message
    )

    Add-Content `
        -Path $TaskLog `
        -Value $Line `
        -Encoding UTF8
}

try {
    Write-TaskLog "TASK WRAPPER START"

    if(-not (Test-Path $VenvPython)) {
        throw "VENV PYTHON NOT FOUND: $VenvPython"
    }

    # Load persistent User environment variables explicitly.
    $env:APCA_API_KEY_ID = [Environment]::GetEnvironmentVariable(
        "APCA_API_KEY_ID",
        "User"
    )

    $env:APCA_API_SECRET_KEY = [Environment]::GetEnvironmentVariable(
        "APCA_API_SECRET_KEY",
        "User"
    )

    $env:LIVE_TRADING_ENABLED = "false"
    $env:ETRADE_LIVE_WRITE_ENABLED = "false"
    $env:ETRADE_LIVE_SUBMISSION_ENABLED = "false"
    $env:BROKER_WRITE_ENABLED = "false"

    if([string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID)) {
        throw "APCA_API_KEY_ID IS MISSING"
    }

    if([string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)) {
        throw "APCA_API_SECRET_KEY IS MISSING"
    }

    # Reproduce the activated virtual-environment process state.
    $env:VIRTUAL_ENV = Join-Path $ProjectRoot ".venv"
    $env:PATH = (
        (Join-Path $ProjectRoot ".venv\Scripts") +
        ";" +
        $env:PATH
    )

    Remove-Item Env:PYTHONHOME `
        -ErrorAction SilentlyContinue

    $Arguments = @(
        (Join-Path $ProjectRoot "tools\run_market_open_auto_validation.py"),
        "--repository-root",
        $ProjectRoot,
        "--poll-seconds",
        "30",
        "--timeout-minutes",
        "480"
    )

    if($DryRun) {
        $Arguments += "--dry-run"
        Write-TaskLog "MODE: DRY RUN"
    }
    else {
        Write-TaskLog "MODE: CONTROLLED PAPER VALIDATION"
    }

    Write-TaskLog "PYTHON: $VenvPython"
    Write-TaskLog "WORKING DIRECTORY: $ProjectRoot"
    Write-TaskLog "PAPER KEY PRESENT: $([bool]$env:APCA_API_KEY_ID)"
    Write-TaskLog "PAPER SECRET PRESENT: $([bool]$env:APCA_API_SECRET_KEY)"
    Write-TaskLog "LIVE TRADING: $env:LIVE_TRADING_ENABLED"
    Write-TaskLog "ETRADE WRITE: $env:ETRADE_LIVE_WRITE_ENABLED"

    & $VenvPython @Arguments 2>&1 |
    Tee-Object `
        -FilePath $TaskLog `
        -Append

    $ExitCode = $LASTEXITCODE

    Write-TaskLog "RUNNER EXIT CODE: $ExitCode"

    exit $ExitCode
}
catch {
    Write-TaskLog ("TASK WRAPPER ERROR: " + $_.Exception.Message)
    exit 2
}