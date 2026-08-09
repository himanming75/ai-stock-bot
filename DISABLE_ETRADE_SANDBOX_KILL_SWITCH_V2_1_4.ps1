$ErrorActionPreference="Stop"
$Path="C:\stock-bot\runtime\etrade_sandbox_multi_cycle_v2_1_4\KILL_SWITCH"
Remove-Item $Path -Force -ErrorAction SilentlyContinue
Write-Host "V2.1.4 KILL SWITCH: OFF"
