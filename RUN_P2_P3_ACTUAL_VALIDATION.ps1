param(
    [Parameter(Mandatory=$true)]
    [string]$ClientOrderId,
    [int]$TimeoutSeconds = 180,
    [int]$PollSeconds = 5
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

if ($env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets") {
    throw "Only Alpaca Paper endpoint is allowed."
}
if ($env:ALPACA_PAPER_EXECUTION_NETWORK_ENABLE -ne "true") {
    throw "Paper execution network access must be enabled."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "Fresh local Paper credentials are required."
}

$env:PYTHONPATH = $Root
& $Python `
    (Join-Path $Root "tools\run_p2_p3_actual_validation.py") `
    --client-order-id $ClientOrderId `
    --timeout-seconds $TimeoutSeconds `
    --poll-seconds $PollSeconds
exit $LASTEXITCODE
