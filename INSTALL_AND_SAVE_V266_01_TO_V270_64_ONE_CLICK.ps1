param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V266.01-V270.64 WINDOWS AUTOSTART AND RECOVERY ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK"
python tools\install_check_v266_01_to_v270_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST"
python -m unittest tools.test_v266_01_to_v270_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] DRY RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V266_01_TO_V270_64_DRY_RUN.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY"
python tools\verify_v266_01_to_v270_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add windows_autostart_recovery web_controller/windows_autostart_recovery_api.py `
 release/v266_01_to_v270_64 tools/run_v266_01_to_v270_64.py `
 tools/test_v266_01_to_v270_64.py tools/install_check_v266_01_to_v270_64.py `
 tools/verify_v266_01_to_v270_64.py RUN_V266_01_TO_V270_64_DRY_RUN.ps1 `
 RUN_V266_01_TO_V270_64_SUPERVISOR.ps1 ENABLE_V266_SUPERVISOR.ps1 `
 DISABLE_V266_SUPERVISOR.ps1 REGISTER_V266_WINDOWS_AUTOSTART.ps1 `
 UNREGISTER_V266_WINDOWS_AUTOSTART.ps1 CHECK_V266_WINDOWS_AUTOSTART.ps1 `
 RUN_V266_01_TO_V270_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V266_01_TO_V270_64_ONE_CLICK.ps1 `
 V266_01_TO_V270_64_MANIFEST.json GIT_COMMIT_V266_01_TO_V270_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V266.01-V270.64 Windows autostart and recovery integrated"}
Write-Host "[6/6] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V266.01-V270.64 ONE-CLICK COMPLETE"
Write-Host "Windows Task Scheduler is NOT registered automatically."
