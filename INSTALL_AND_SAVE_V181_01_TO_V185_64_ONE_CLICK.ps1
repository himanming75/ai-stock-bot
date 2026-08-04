param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V181.01-V185.64 PORTFOLIO BROKER ADAPTER FOUNDATION FIXED V2 ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force}
Set-Location $ProjectPath
Write-Host "[1/6] INSTALL CHECK";python tools\install_check_v181_01_to_v185_64.py;if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}
Write-Host "[2/6] TEST";python -m unittest tools.test_v181_01_to_v185_64 -v;if($LASTEXITCODE-ne 0){throw "TEST FAILED"}
Write-Host "[3/6] RUN";powershell -ExecutionPolicy Bypass -File .\RUN_V181_01_TO_V185_64.ps1;if($LASTEXITCODE-ne 0){throw "RUN FAILED"}
Write-Host "[4/6] VERIFY";python tools\verify_v181_01_to_v185_64.py;if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}
Write-Host "[5/6] GIT COMMIT"
git add portfolio_broker web_controller/portfolio_api.py release/v181_01_to_v185_64 `
 tools/run_v181_01_to_v185_64.py tools/test_v181_01_to_v185_64.py `
 tools/install_check_v181_01_to_v185_64.py tools/verify_v181_01_to_v185_64.py `
 RUN_V181_01_TO_V185_64.ps1 RUN_V181_01_TO_V185_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V181_01_TO_V185_64_ONE_CLICK.ps1 `
 V181_01_TO_V185_64_MANIFEST.json GIT_COMMIT_V181_01_TO_V185_64.txt `
 GIT_COMMIT_V181_01_TO_V185_64_FIXED_V2.txt
$staged=git diff --cached --name-only
if($staged){git commit -m "V181.01-V185.64 fix portfolio risk default policy fallback"}
Write-Host "[6/6] GIT PUSH";if(-not $SkipPush){git push origin main};git log -1 --oneline
Write-Host "V181.01-V185.64 FIXED V2 ONE-CLICK COMPLETE"
