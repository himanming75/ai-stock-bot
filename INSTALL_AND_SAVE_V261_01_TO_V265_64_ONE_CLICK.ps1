param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V261.01-V265.64 AUTONOMOUS PAPER SESSION RUNNER ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v261_01_to_v265_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v261_01_to_v265_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] DRY RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V261_01_TO_V265_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v261_01_to_v265_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add autonomous_paper_session web_controller/autonomous_paper_session_api.py `
 release/v261_01_to_v265_64 tools/run_v261_01_to_v265_64.py `
 tools/test_v261_01_to_v265_64.py tools/install_check_v261_01_to_v265_64.py `
 tools/verify_v261_01_to_v265_64.py RUN_V261_01_TO_V265_64_DRY_RUN.ps1 `
 RUN_V261_01_TO_V265_64_REAL_PAPER_SESSION.ps1 `
 ENABLE_V261_PAPER_SESSION_RUNNER.ps1 DISABLE_V261_PAPER_SESSION_RUNNER.ps1 `
 STOP_V261_PAPER_SESSION.ps1 CLEAR_V261_PAPER_SESSION_STOP.ps1 `
 RUN_V261_01_TO_V265_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V261_01_TO_V265_64_ONE_CLICK.ps1 `
 V261_01_TO_V265_64_MANIFEST.json GIT_COMMIT_V261_01_TO_V265_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V261.01-V265.64 autonomous paper session runner integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V261.01-V265.64 ONE-CLICK COMPLETE"
Write-Host "Default state remains SAFE/BLOCKED."
