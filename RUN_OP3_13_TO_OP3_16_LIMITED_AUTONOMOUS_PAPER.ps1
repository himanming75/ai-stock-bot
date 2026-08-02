param(
    [switch]$EnableNetwork,
    [switch]$EnableSubmission,
    [string]$ApprovalPhrase = ""
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== OP3.13-OP3.16 LIMITED AUTONOMOUS PAPER TRADING ==="
Write-Host "Default is one local preview cycle. Continuous loop is disabled."
$argsList=@("tools/run_limited_autonomous_paper_trading_op3_13_to_op3_16.py","--repository-root",".")
if($EnableNetwork){$argsList+="--enable-network"}
if($EnableSubmission){$argsList+="--enable-submission"}
if(-not [string]::IsNullOrWhiteSpace($ApprovalPhrase)){$argsList+=@("--approval-phrase",$ApprovalPhrase)}
python @argsList
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "OP3.13-OP3.16 COMPLETE"
