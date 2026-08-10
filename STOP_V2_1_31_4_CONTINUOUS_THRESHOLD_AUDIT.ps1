$ErrorActionPreference="Stop"
$Path="C:\stock-bot\runtime\threshold_sensitivity_shadow_audit_v2_1_31_4\STOP_CONTINUOUS_AUDIT"
New-Item -ItemType Directory -Force (Split-Path -Parent $Path) | Out-Null
Set-Content -Path $Path -Value "STOP_REQUESTED" -Encoding ASCII
Write-Host "V2.1.31.4 CONTINUOUS AUDIT STOP REQUESTED"
