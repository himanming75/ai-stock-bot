param(
    [switch]$ConfirmReadOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not $ConfirmReadOnly) {
    throw "P2 requires explicit -ConfirmReadOnly. No network call was made."
}
if (-not (Test-Path $Python)) {
    throw "Project .venv was not found."
}

$P1Certificate = Join-Path $Root `
  "release\p1_actual_environment_qualification\actual\p1_actual_environment_certificate.json"
if (-not (Test-Path $P1Certificate)) {
    throw "P1 certificate was not found."
}

$P1 = Get-Content $P1Certificate -Raw | ConvertFrom-Json
if ($P1.p1_actual_environment_validated -ne $true) {
    throw "P1 actual environment has not passed."
}
if ($P1.p2_actual_broker_read_allowed -ne $true) {
    throw "P1 certificate does not allow P2 read validation."
}

Write-Host "=== LOAD ALPACA PAPER CREDENTIAL ENVIRONMENT ==="
. (Join-Path $Root "IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1") -Mode paper

if ($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets") {
    throw "Paper endpoint enforcement failed."
}

Write-Host "=== P2 ACTUAL PAPER BROKER READ VALIDATION ==="
Write-Host "GET /v2/account"
Write-Host "GET /v2/positions"
Write-Host "GET /v2/orders?status=open"
Write-Host "GET /v2/clock"
Write-Host "NO POST / PATCH / DELETE / ORDER SUBMISSION"

$env:ALPACA_PAPER_READ_ENABLE = "true"
$env:ALPACA_PAPER_READ_TIMEOUT_SECONDS = "10"
$env:ALPACA_PAPER_READ_MAX_ATTEMPTS = "3"
$env:ALPACA_PAPER_READ_BACKOFF_SECONDS = "0.5"
$env:PYTHONPATH = $Root

try {
    & $Python (
        Join-Path $Root `
        "tools\run_p2_actual_paper_broker_read.py"
    )
    exit $LASTEXITCODE
}
finally {
    Remove-Item Env:ALPACA_PAPER_READ_ENABLE -ErrorAction SilentlyContinue
}
