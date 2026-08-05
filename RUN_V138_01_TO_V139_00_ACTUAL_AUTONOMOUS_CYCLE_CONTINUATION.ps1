param([string]$ApprovalPhrase="")
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

Write-Host "=== ACTUAL SAVED-STATE AUTONOMOUS CYCLE CONTINUATION ==="
Write-Host "Local orchestration only. No broker network and no order submission."

if($env:AI_STOCK_BOT_ENABLE_ACTUAL_CYCLE_CONTINUATION -ne "YES"){
    throw "Set AI_STOCK_BOT_ENABLE_ACTUAL_CYCLE_CONTINUATION=YES"
}

if($env:AI_STOCK_BOT_ACTUAL_CYCLE_CONTINUATION_CONFIRMATION -ne "EVALUATE ACTUAL SAVED AUTONOMOUS CYCLE CONTINUATION LOCAL ONLY"){
    throw "Set exact cycle-continuation confirmation text"
}

$ArgsList = @(
    "tools/run_actual_autonomous_cycle_continuation_v138_01_to_v139_00.py",
    "--repository-root",
    "."
)

if(-not [string]::IsNullOrWhiteSpace($ApprovalPhrase)){
    $ArgsList += @(
        "--approval-phrase",
        $ApprovalPhrase
    )
}

python @ArgsList

if($LASTEXITCODE -ne 0){
    exit $LASTEXITCODE
}

Write-Host "ACTUAL SAVED-STATE AUTONOMOUS CYCLE CONTINUATION COMPLETE"
