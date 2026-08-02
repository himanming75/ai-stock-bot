$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== ACTUAL SAVED-PREVIEW FINAL PAPER SUBMISSION APPROVAL ==="
Write-Host "Local approval token only. No broker network and no order submission."
if($env:AI_STOCK_BOT_ENABLE_FINAL_PAPER_SUBMISSION_APPROVAL -ne "YES"){throw "Set AI_STOCK_BOT_ENABLE_FINAL_PAPER_SUBMISSION_APPROVAL=YES"}

python tools/run_actual_final_paper_submission_approval_v137_01_to_v138_00.py `
 --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "ACTUAL FINAL PAPER SUBMISSION APPROVAL COMPLETE"
