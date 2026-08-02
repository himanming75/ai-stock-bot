param(
    [switch]$EnableNetwork,
    [switch]$EnableSubmission,
    [string]$ApprovalPhrase = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OP3.05-OP3.08 SINGLE CONTROLLED PAPER ORDER ==="
Write-Host "Default is preview only. Live endpoint is always blocked."

$argsList = @(
    "tools/run_single_controlled_paper_order_execution_op3_05_to_op3_08.py",
    "--repository-root",
    "."
)

if ($EnableNetwork) {
    $argsList += "--enable-network"
}
if ($EnableSubmission) {
    $argsList += "--enable-submission"
}
if (-not [string]::IsNullOrWhiteSpace($ApprovalPhrase)) {
    $argsList += @("--approval-phrase", $ApprovalPhrase)
}

python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OP3.05-OP3.08 COMPLETE"
