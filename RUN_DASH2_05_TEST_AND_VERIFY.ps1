$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

python tools/install_check_dash2_05.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python -m unittest `
  tools.test_current_paper_snapshot_hotfix_dash2_05 `
  -v
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

powershell -ExecutionPolicy Bypass `
  -File .\RUN_DASH2_05_REFRESH_ACTUAL_PAPER_SNAPSHOT.ps1
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

python tools/verify_current_paper_snapshot_hotfix_dash2_05.py
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}

Write-Host "DASH2.05 TEST AND VERIFY PASS"
