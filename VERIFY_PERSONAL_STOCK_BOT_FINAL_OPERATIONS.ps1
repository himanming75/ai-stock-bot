$ErrorActionPreference="Stop"
$Repo="C:\stock-bot"
Set-Location $Repo

$Files=@(
 "START_PERSONAL_STOCK_BOT.ps1",
 "STOP_PERSONAL_STOCK_BOT.ps1",
 "RECOVER_PERSONAL_STOCK_BOT.ps1",
 "STATUS_PERSONAL_STOCK_BOT.ps1"
)

foreach($f in $Files){
    if(-not (Test-Path (Join-Path $Repo $f))){
        throw "MISSING FILE: $f"
    }
}

$Scripts=@(
 ".\START_PERSONAL_STOCK_BOT.ps1",
 ".\STOP_PERSONAL_STOCK_BOT.ps1",
 ".\RECOVER_PERSONAL_STOCK_BOT.ps1",
 ".\STATUS_PERSONAL_STOCK_BOT.ps1"
)

# Block only actual order-submission / production-trading invocation patterns.
# Safety/status strings such as live_orders_submitted_by_launcher=0 are allowed.
$DisallowedPatterns=@(
    '\bsubmit_order\s*\(',
    '\bplace_order\s*\(',
    '\bsend_order\s*\(',
    '\bpreview_order\s*\(',
    '/orders/place',
    '/order/place',
    'ETRADE_ALLOW_LIVE_TRADING\s*=\s*["'']?YES',
    'LIVE_TRADING_ENABLED\s*=\s*["'']?TRUE',
    'PRODUCTION_ORDER_POST_ALLOWED\s*=\s*["'']?TRUE'
)

foreach($Script in $Scripts){
    $Text=Get-Content $Script -Raw
    foreach($Pattern in $DisallowedPatterns){
        if($Text -match $Pattern){
            throw "DISALLOWED TRADING INVOCATION DETECTED IN $Script : $Pattern"
        }
    }
}

# Required safety/status markers must remain present.
$Start=Get-Content .\START_PERSONAL_STOCK_BOT.ps1 -Raw
$Stop=Get-Content .\STOP_PERSONAL_STOCK_BOT.ps1 -Raw
$Recover=Get-Content .\RECOVER_PERSONAL_STOCK_BOT.ps1 -Raw

if($Start -notmatch 'paper_orders_submitted_by_launcher=0'){
    throw "START SAFETY MARKER MISSING: paper_orders_submitted_by_launcher=0"
}
if($Start -notmatch 'live_orders_submitted_by_launcher=0'){
    throw "START SAFETY MARKER MISSING: live_orders_submitted_by_launcher=0"
}
if($Recover -notmatch 'paper_orders_submitted_by_recovery'){
    throw "RECOVERY SAFETY MARKER MISSING"
}

Write-Host "VERIFY: PASS"
Write-Host "Actual order-submission invocation detected: NO"
Write-Host "Launcher Paper Orders: 0"
Write-Host "Launcher Live Orders: 0"
Write-Host "E*TRADE: DEFERRED"
