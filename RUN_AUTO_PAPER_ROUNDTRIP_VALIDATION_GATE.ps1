[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"

$Root = "C:\stock-bot"
$TaskName = "AIStockBot-PaperRoundtripValidationGate"
$Validator = Join-Path $Root "RUN_ACTUAL_ALPACA_PAPER_ROUNDTRIP_VALIDATION_V1.ps1"
$Result = Join-Path $Root "runtime\paper_full_auto_validation\latest_roundtrip_validation.json"
$GateDir = Join-Path $Root "runtime\paper_full_auto_validation"
$GateFile = Join-Path $GateDir "ROUNDTRIP_GATE_PASS.json"

New-Item -ItemType Directory -Path $GateDir -Force | Out-Null

# Do not rerun after PASS.
if(Test-Path $GateFile) {
    try {
        Disable-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
    } catch {}
    exit 0
}

powershell.exe `
    -NoProfile `
    -NonInteractive `
    -ExecutionPolicy Bypass `
    -File $Validator

$ValidatorExit = $LASTEXITCODE

if(Test-Path $Result) {
    try {
        $Data = Get-Content $Result -Raw | ConvertFrom-Json

        if(
            $Data.stage -eq "ROUNDTRIP_VALIDATION_PASS" -and
            $Data.status -eq "PASS" -and
            $Data.paper_only -eq $true -and
            $Data.closed_roundtrip -eq $true
        ) {
            $Gate = [ordered]@{
                gate = "PAPER_ROUNDTRIP_VALIDATION"
                status = "PASS"
                passed_at = (Get-Date).ToUniversalTime().ToString("o")
                symbol = $Data.symbol
                paper_orders_submitted = $Data.paper_orders_submitted
                live_order_submitted = $false
                etrade_live_write_enabled = $false
                next_step = "ELIGIBLE_FOR_15_25_40_RAMP_CONFIGURATION"
            }

            $Gate |
                ConvertTo-Json -Depth 5 |
                Set-Content -Path $GateFile -Encoding UTF8

            try {
                Disable-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
            } catch {}

            exit 0
        }
    } catch {
        # Leave task enabled for the next weekday attempt.
    }
}

# WAITING_FOR_MARKET_OPEN, symbol conflict, or a transient Paper error:
# leave the task enabled for the next scheduled weekday.
exit $ValidatorExit