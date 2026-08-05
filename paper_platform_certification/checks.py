from __future__ import annotations
from pathlib import Path

ZERO_FIELDS = (
    "actual_paper_orders_submitted",
    "actual_live_orders_submitted",
)

FALSE_FIELDS = (
    "actual_broker_write_performed",
    "actual_order_submission_performed",
)

def check_component(name: str, path: Path, payload: dict, allowed_statuses: set[str]) -> dict:
    blockers = []
    warnings = []
    if not path.exists():
        blockers.append("FILE_MISSING")
    if not payload:
        blockers.append("PAYLOAD_MISSING_OR_INVALID")
    status = payload.get("status")
    if payload and status not in allowed_statuses:
        blockers.append(f"STATUS_NOT_ALLOWED:{status}")
    for field in ZERO_FIELDS:
        if field in payload and payload.get(field) != 0:
            blockers.append(f"ZERO_ORDER_CONTRACT_FAILED:{field}")
    for field in FALSE_FIELDS:
        if field in payload and payload.get(field) is not False:
            blockers.append(f"SAFETY_CONTRACT_FAILED:{field}")
    if payload and not any(k.endswith("fingerprint") for k in payload):
        warnings.append("FINGERPRINT_NOT_PRESENT")
    return {
        "component": name,
        "path": str(path),
        "status": status,
        "passed": not blockers,
        "blockers": blockers,
        "warnings": warnings,
    }

def detect_bar_sort_hotfix(service_path: Path) -> dict:
    if not service_path.exists():
        return {
            "status": "BLOCKED",
            "blockers": ["SERVICE_FILE_MISSING"],
        }
    text = service_path.read_text(encoding="utf-8-sig")
    blockers = []
    if '"sort": "desc"' not in text:
        blockers.append("SORT_DESC_NOT_FOUND")
    if "return sorted(" not in text:
        blockers.append("CHRONOLOGICAL_RESORT_NOT_FOUND")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "blockers": blockers,
    }

def runtime_evidence(root: Path) -> dict:
    controller = root / "release/paper_automation_controller/actual/controller_cycle_ledger.jsonl"
    polling = root / "release/actual_market_polling_validation/actual/polling_ledger.jsonl"
    watchdog = root / "release/automation_watchdog_restart_recovery/actual/watchdog_summary.json"
    daily = root / "release/daily_session_manager_startup_autorun/actual/daily_session_summary.json"
    return {
        "controller_ledger_exists": controller.exists(),
        "polling_ledger_exists": polling.exists(),
        "watchdog_summary_exists": watchdog.exists(),
        "daily_session_summary_exists": daily.exists(),
        "controller_ledger_size": controller.stat().st_size if controller.exists() else 0,
        "polling_ledger_size": polling.stat().st_size if polling.exists() else 0,
    }
