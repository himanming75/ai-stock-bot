[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if(Test-Path ".\.venv\Scripts\python.exe") {
    $Python = ".\.venv\Scripts\python.exe"
}
else {
    $Python = "python"
}

& $Python -m unittest tools.test_phase3_etrade_live_canonicalization -v
if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$tempVerify = Join-Path $env:TEMP ("verify_phase3_etrade_live_selfcontained_" + [Guid]::NewGuid().ToString("N") + ".py")

$pythonCode = @"
import sys
from pathlib import Path

ROOT = Path(r"$PSScriptRoot").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etrade_live_audit.canonicalizer import canonicalize_etrade_live, CAPABILITIES

def rec(path, functions=(), classes=(), score=0):
    return {
        "path": path,
        "functions": list(functions),
        "classes": list(classes),
        "score": score,
        "modified_ns": 1,
        "categories": [],
        "safety_flags": {},
    }

audit = {
    "records": [
        rec("multi_broker_etrade/auth.py", ["oauth_token"]),
        rec("multi_broker_etrade/client.py", [
            "api_etrade_com", "list_accounts", "positions",
            "quote", "preview_order", "place_order",
            "list_orders", "cancel_order"
        ]),
        rec("deployment/credential_vault.py", [
            "consumer_key", "consumer_secret", "production"
        ]),
        rec("broker_safe_execution/gateway.py", [
            "duplicate_order", "daily_loss_limit", "kill_switch"
        ]),
        rec("broker_integration/actual_validation.py", [
            "reconcile_orders", "reconcile_positions"
        ]),
    ]
}

data = canonicalize_etrade_live(audit)

assert data["status"] == "PASS"
assert data["scope_locked"] is True
assert data["broker_scope"]["paper_broker"] == "ALPACA"
assert data["broker_scope"]["live_broker"] == "ETRADE"
assert data["broker_scope"]["other_brokers_enabled"] is False
assert data["etrade_live_submission_enabled"] is False
assert data["etrade_live_cancel_enabled"] is False
assert data["etrade_live_allocation_enabled"] is False
assert data["actual_live_orders_submitted"] == 0
assert data["actual_live_orders_cancelled"] == 0
assert data["missing_capabilities"] == []
assert len(data["selected"]) == len(CAPABILITIES) == 14
assert all(v["selected"] is not None for v in data["selected"].values())

print("SELF-CONTAINED RESULT CONTRACT: PASS")
print("PHASE3 CAPABILITIES:", len(data["selected"]))
"@

[System.IO.File]::WriteAllText(
    $tempVerify,
    $pythonCode,
    (New-Object System.Text.UTF8Encoding($false))
)

& $Python $tempVerify
$ExitCode = $LASTEXITCODE
Remove-Item $tempVerify -Force -ErrorAction SilentlyContinue

if($ExitCode -ne 0) { exit $ExitCode }

Write-Host "VERIFY: PASS"
Write-Host "SELF-CONTAINED: PASS"
Write-Host "PROJECT ROOT IMPORT: PASS"
Write-Host "RELEASE ARTIFACT DEPENDENCY: NONE"
Write-Host "BROKER ROLE LOCK: PASS"
Write-Host "ETRADE LIVE WRITE LOCK: PASS"
Write-Host "ZERO LIVE ORDER CONTRACT: PASS"
