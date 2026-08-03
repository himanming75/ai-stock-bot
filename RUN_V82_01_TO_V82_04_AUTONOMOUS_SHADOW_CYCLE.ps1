param([switch]$ExecuteCycle)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== V82.01-V82.04 AUTONOMOUS SHADOW CYCLE FOUNDATION ==="
Write-Host "Single local cycle only. No network or broker orders."
$args=@()
if($ExecuteCycle){$args += "--execute-cycle"}
python tools/run_autonomous_shadow_cycle_v82_01_to_v82_04.py @args
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
Write-Host "V82.01-V82.04 COMPLETE"
