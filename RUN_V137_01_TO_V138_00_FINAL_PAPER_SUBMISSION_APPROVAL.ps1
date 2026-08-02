$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
if(Test-Path "release\v138_00\output"){Remove-Item "release\v138_00\output" -Recurse -Force}
if(Test-Path "release\v138_00\approval"){Remove-Item "release\v138_00\approval" -Recurse -Force}

Write-Host "=== V137.01-V138.00 INSTALL CHECK ==="
python tools/install_check_v137_01_to_v138_00.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V137.01-V138.00 REAL UNIT TESTS ==="
python -m unittest tools.test_final_paper_submission_approval_v137_01_to_v138_00 -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V137.01-V138.00 FINAL APPROVAL GATE DEMO ==="
python tools/run_final_paper_submission_approval_v137_01_to_v138_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "=== V137.01-V138.00 VERIFY ==="
python tools/verify_final_paper_submission_approval_v137_01_to_v138_00.py --repository-root .
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "V137.01-V138.00 FINAL PAPER SUBMISSION APPROVAL PASS - READY TO COMMIT"
