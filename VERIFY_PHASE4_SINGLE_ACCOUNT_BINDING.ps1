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

& $Python -m unittest tools.test_phase4_single_account_binding -v
if($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$tempVerify = Join-Path $env:TEMP ("verify_phase4_single_account_selfcontained_" + [Guid]::NewGuid().ToString("N") + ".py")

$pythonCode = @"
import sys
from pathlib import Path

ROOT = Path(r"$PSScriptRoot").resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from single_account_audit.canonicalizer import canonicalize_single_account, CAPABILITIES

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
        rec("deployment/credential_vault.py", [
            "alpaca_paper_account",
            "etrade_live_account",
            "account_id_allowlist",
            "credential_account_match",
        ]),
        rec("broker_safe_execution/gateway.py", [
            "broker_account_role_lock",
            "pre_order_account_validation",
            "wrong_account_hard_block",
            "account_switch_prohibition",
        ]),
        rec("broker_integration/actual_validation.py", [
            "restart_account_revalidation",
            "account_reconciliation",
        ]),
        rec("paper_automation_controller/checkpoint.py", [
            "checkpoint_account_identity",
        ]),
        rec("system_health_monitoring/service.py", [
            "dashboard_account_broker_mode",
        ]),
        rec("paper_automation_controller/controller.py", [
            "single_account_runtime_lock",
        ]),
    ]
}

data = canonicalize_single_account(audit)

assert data["status"] == "PASS"
assert data["scope_locked"] is True
assert data["multi_account_enabled"] is False
assert data["account_roles"]["alpaca"]["mode"] == "PAPER_ONLY"
assert data["account_roles"]["alpaca"]["allowed_account_count"] == 1
assert data["account_roles"]["etrade"]["mode"] == "LIVE_ONLY"
assert data["account_roles"]["etrade"]["allowed_account_count"] == 1
assert data["runtime_account_switch_enabled"] is False
assert data["automatic_account_discovery_enabled"] is False
assert data["live_submission_enabled"] is False
assert data["actual_paper_orders_submitted"] == 0
assert data["actual_live_orders_submitted"] == 0
assert data["missing_capabilities"] == []
assert len(data["selected"]) == len(CAPABILITIES) == 12
assert all(v["selected"] is not None for v in data["selected"].values())

print("SELF-CONTAINED RESULT CONTRACT: PASS")
print("PHASE4 CAPABILITIES:", len(data["selected"]))
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
Write-Host "SINGLE ACCOUNT ROLE LOCK: PASS"
Write-Host "ACCOUNT SWITCH OFF: PASS"
Write-Host "ZERO ORDER CONTRACT: PASS"
