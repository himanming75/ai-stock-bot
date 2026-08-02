param(
    [string]$ApprovalPhrase = "",
    [switch]$EnableSubmission
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== V139.07 AUTONOMOUS PAPER ORDER LAUNCH PREPARATION ==="
Write-Host "Local preview and approval gate only. No credentials, broker network, or order submission."

$arguments = @(
    "tools/run_autonomous_paper_order_launch_v139_07.py",
    "--repository-root", "."
)

if (-not [string]::IsNullOrWhiteSpace($ApprovalPhrase)) {
    $arguments += @("--approval-phrase", $ApprovalPhrase)
}

if ($EnableSubmission) {
    $arguments += "--enable-submission"
}

python @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "V139.07 AUTONOMOUS PAPER ORDER LAUNCH PREPARATION COMPLETE"
