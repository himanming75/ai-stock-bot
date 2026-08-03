param([switch]$ApproveRetry,[switch]$CompleteReentry,[switch]$ClearApprovalLock,[string]$ObservedAt="")
$ErrorActionPreference="Stop"; Set-Location $PSScriptRoot
$argsList=@()
if($ApproveRetry){$argsList+="--approve-retry"}
if($CompleteReentry){$argsList+="--complete-reentry"}
if($ClearApprovalLock){$argsList+="--clear-approval-lock"}
if($ObservedAt){$argsList+="--observed-at";$argsList+=$ObservedAt}
python tools/run_retry_approval_supervised_reentry_v83_41_to_v83_44.py @argsList
if($LASTEXITCODE-ne 0){exit $LASTEXITCODE}
