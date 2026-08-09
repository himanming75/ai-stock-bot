$ErrorActionPreference="Stop"
Set-Location C:\stock-bot

Write-Host "=== V2.9.1 SAFE FAILED-INTERMEDIATE CLEANUP REPAIR ==="

$Targets=@(
    "RUN_V2_8.ps1",
    "RUN_V2_8_1.ps1",
    "VERIFY_V2_8.ps1",
    "VERIFY_V2_8_1.ps1",
    "release/v2_8_1_exact_paper_loop_shadow_hook",
    "release/v2_8_shadow_orchestration_integration",
    "tests/test_exact_paper_loop_shadow_v2_8_1.py",
    "tests/test_shadow_orchestration_v2_8.py",
    "tools/integrate_exact_paper_loop_shadow_v2_8_1.py",
    "tools/integrate_shadow_orchestration_v2_8.py",
    "tools/summarize_shadow_v2_8.py"
)

foreach($Target in $Targets){
    if(-not(Test-Path -LiteralPath $Target)){
        Write-Host "SKIP MISSING: $Target"
        continue
    }

    # Safe tracked-path check using output-only git ls-files.
    # For untracked paths git ls-files returns no output and exit code 0.
    $Tracked = @(git ls-files -- "$Target")
    if($Tracked.Count -gt 0){
        throw "REFUSING TO REMOVE TRACKED PATH: $Target"
    }

    Remove-Item -LiteralPath $Target -Recurse -Force
    Write-Host "REMOVED UNTRACKED FAILED INTERMEDIATE: $Target"
}

Write-Host ""
Write-Host "CLEANUP STATUS:"
git status --short
