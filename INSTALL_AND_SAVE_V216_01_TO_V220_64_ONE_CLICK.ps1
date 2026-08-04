param([string]$ProjectPath="C:\stock-bot",[switch]$SkipPush)
$ErrorActionPreference="Stop";$SourceRoot=$PSScriptRoot
Write-Host "=== V216.01-V220.64 FINAL PRODUCTION RELEASE FIX V2 ONE-CLICK INSTALL ==="
Get-ChildItem -LiteralPath $SourceRoot -Force | ForEach-Object {
  Copy-Item -LiteralPath $_.FullName -Destination $ProjectPath -Recurse -Force
}
Set-Location $ProjectPath

$IgnoreLine="release/v216_01_to_v220_64/bundle/AI_STOCK_BOT_V220_FINAL_PRODUCTION.zip"
$GitIgnorePath=Join-Path $ProjectPath ".gitignore"
if(-not (Test-Path $GitIgnorePath)){
  New-Item -ItemType File -Path $GitIgnorePath -Force | Out-Null
}
$ExistingIgnore=Get-Content $GitIgnorePath -ErrorAction SilentlyContinue
if($ExistingIgnore -notcontains $IgnoreLine){
  Add-Content -Path $GitIgnorePath -Value "`n# V220 locally generated final bundle`n$IgnoreLine"
}

Write-Host "[1/7] INSTALL CHECK"
python tools\install_check_v216_01_to_v220_64.py
if($LASTEXITCODE-ne 0){throw "INSTALL FAILED"}

Write-Host "[2/7] UNIT TEST"
python -m unittest tools.test_v216_01_to_v220_64 -v
if($LASTEXITCODE-ne 0){throw "TEST FAILED"}

Write-Host "[3/7] FINAL INTEGRATION RUN"
powershell -ExecutionPolicy Bypass -File .\RUN_V216_01_TO_V220_64.ps1
if($LASTEXITCODE-ne 0){throw "RUN FAILED"}

Write-Host "[4/7] VERIFY"
python tools\verify_v216_01_to_v220_64.py
if($LASTEXITCODE-ne 0){throw "VERIFY FAILED"}

Write-Host "[5/7] PRE-COMMIT SAFETY CHECK"
$result=Get-Content .\release\v216_01_to_v220_64\actual\v220_final_production_result.json -Raw | ConvertFrom-Json
if($result.actual_live_orders_submitted -ne 0){throw "LIVE ORDER HISTORY IS NOT ZERO"}
if($result.broker_write_enabled){throw "BROKER WRITE MUST REMAIN DISABLED"}
if($result.live_submission_enabled){throw "LIVE SUBMISSION MUST REMAIN DISABLED"}

Write-Host "[6/7] GIT COMMIT"
git add final_production_release web_controller/final_release_api.py release/v216_01_to_v220_64 `
 tools/run_v216_01_to_v220_64.py tools/test_v216_01_to_v220_64.py `
 tools/install_check_v216_01_to_v220_64.py tools/verify_v216_01_to_v220_64.py `
 RUN_V216_01_TO_V220_64.ps1 RUN_V216_01_TO_V220_64_TEST_AND_VERIFY.ps1 `
 INSTALL_AND_SAVE_V216_01_TO_V220_64_ONE_CLICK.ps1 `
 V216_01_TO_V220_64_MANIFEST.json GIT_COMMIT_V216_01_TO_V220_64.txt `
 GIT_COMMIT_V216_01_TO_V220_64_FIX_V2.txt `
 .gitignore

# Never commit the generated final ZIP.
git reset -- release/v216_01_to_v220_64/bundle/AI_STOCK_BOT_V220_FINAL_PRODUCTION.zip 2>$null

$staged=git diff --cached --name-only
if($staged){git commit -m "V216.01-V220.64 fix V160 inventory path"}

Write-Host "[7/7] GIT PUSH"
if(-not $SkipPush){git push origin main}
git log -1 --oneline
Write-Host "V216.01-V220.64 FIX V2 ONE-CLICK COMPLETE"
Write-Host "Final offline bundle:"
Write-Host "$ProjectPath\release\v216_01_to_v220_64\bundle\AI_STOCK_BOT_V220_FINAL_PRODUCTION.zip"
