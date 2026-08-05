$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

if ($env:ALPACA_PAPER_READ_ENABLE -ne "true") {
    throw "Set ALPACA_PAPER_READ_ENABLE=true explicitly."
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw "APCA_API_KEY_ID and APCA_API_SECRET_KEY are required."
}
if ($env:APCA_API_BASE_URL -and $env:APCA_API_BASE_URL -ne "https://paper-api.alpaca.markets") {
    throw "Only https://paper-api.alpaca.markets is allowed."
}

$OldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $Root
    & $Python (Join-Path $Root "tools\run_v461_to_v470.py") --actual-read
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $OldPythonPath
}
