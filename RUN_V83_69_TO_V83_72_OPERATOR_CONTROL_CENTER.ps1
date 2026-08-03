param(
    [ValidateSet(
        "",
        "PAUSE",
        "RESUME",
        "APPROVE_RETRY",
        "REJECT_RETRY",
        "CLEAR_STALE_LOCK",
        "END_SESSION"
    )]
    [string]$Action = "",
    [string]$Note = "",
    [switch]$ClearControlLock,
    [string]$ObservedAt = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V83.69-V83.72 OPERATOR CONTROL CENTER ==="
Write-Host "Control planning only. No automatic execution."

$argsList = @()
if ($Action) {
    $argsList += "--action"
    $argsList += $Action
}
if ($Note) {
    $argsList += "--note"
    $argsList += $Note
}
if ($ClearControlLock) {
    $argsList += "--clear-control-lock"
}
if ($ObservedAt) {
    $argsList += "--observed-at"
    $argsList += $ObservedAt
}

python tools/run_operator_control_center_v83_69_to_v83_72.py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V83.69-V83.72 COMPLETE"
