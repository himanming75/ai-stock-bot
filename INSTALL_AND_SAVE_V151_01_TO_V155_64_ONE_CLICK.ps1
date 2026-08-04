param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V151.01-V155.64 REAL ALPACA PAPER WEB OPERATIONS ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force}
Set-Location $ProjectPath
Write-Host "[1/5] INSTALL CHECK";python tools\install_check_v151_01_to_v155_64.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/5] TEST";python -m unittest tools.test_v151_01_to_v155_64 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/5] VERIFY";python tools\verify_v151_01_to_v155_64.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[4/5] GIT COMMIT"
git add paper_web_ops web_controller/paper_api.py web_controller/server.py web_controller/static `
 release/v151_01_to_v155_64 tools/test_v151_01_to_v155_64.py `
 tools/install_check_v151_01_to_v155_64.py tools/verify_v151_01_to_v155_64.py `
 RUN_V151_01_TO_V155_64_TEST_AND_VERIFY.ps1 INSTALL_AND_SAVE_V151_01_TO_V155_64_ONE_CLICK.ps1 `
 V151_01_TO_V155_64_MANIFEST.json GIT_COMMIT_V151_01_TO_V155_64.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V151.01-V155.64 real Alpaca Paper web operations integrated"}
Write-Host "[5/5] GIT PUSH";if(-not $SkipPush){git push origin main};git log -1 --oneline
Write-Host "V151.01-V155.64 ONE-CLICK COMPLETE";Write-Host "Restart the web controller to load Paper Operations."
