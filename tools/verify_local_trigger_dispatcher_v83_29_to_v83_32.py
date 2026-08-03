from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXPECTED_WAIT_STATES = {
    "LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER",
    "LOCAL_TRIGGER_DISPATCH_DRY_RUN_READY",
}

EXPECTED_ABSENT_TRIGGER_ISSUES = {
    "TRIGGER_PLAN_NOT_FOUND",
    "TRIGGER_LOCK_NOT_ACTIVE",
}


def evaluate_verification(result: dict[str, Any]) -> dict[str, Any]:
    state = str(result.get("state", ""))
    status = str(result.get("status", ""))
    issues = result.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    issue_codes = {
        str(item.get("code", ""))
        for item in issues
        if isinstance(item, dict) and item.get("code")
    }

    normal_pass = status == "PASS"
    expected_wait = (
        state in EXPECTED_WAIT_STATES
        and status == "PASS"
        and not issue_codes
    )
    expected_absent_trigger_block = (
        state == "LOCAL_TRIGGER_DISPATCH_SAFE_MODE"
        and status == "BLOCKED"
        and bool(issue_codes)
        and issue_codes.issubset(EXPECTED_ABSENT_TRIGGER_ISSUES)
    )

    operational_status_accepted = (
        normal_pass or expected_wait or expected_absent_trigger_block
    )

    checks = {
        "stage_range": result.get("stage_range") == "V83.29-V83.32",
        "operational_status_accepted": operational_status_accepted,
        "paper_only": result.get("paper_only") is True,
        "broker_write_disabled": result.get("broker_write_enabled") is False,
        "order_submission_disabled": (
            result.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": result.get("live_trading_enabled") is False,
        "external_network_unused": (
            result.get("actual_external_network_used") is False
        ),
        "network_requests_zero": (
            result.get("network_requests_executed") == 0
        ),
        "write_requests_zero": result.get("write_requests_executed") == 0,
        "paper_orders_zero": (
            result.get("actual_paper_orders_submitted") == 0
        ),
        "live_orders_zero": result.get("live_orders_submitted") == 0,
    }

    failed = [name for name, passed in checks.items() if not passed]
    return {
        "verification_stage": "V83.32A",
        "verification_status": "PASS" if not failed else "FAIL",
        "source_state": state,
        "source_status": status,
        "issue_codes": sorted(issue_codes),
        "accepted_as": (
            "EXPECTED_TRIGGER_ABSENCE"
            if expected_absent_trigger_block
            else "EXPECTED_WAIT_STATE"
            if expected_wait
            else "NORMAL_PASS"
            if normal_pass
            else "UNACCEPTED_STATE"
        ),
        "checks": checks,
        "failed": failed,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_result.json"
    )
    if not path.exists():
        print(json.dumps({
            "verification_stage": "V83.32A",
            "verification_status": "FAIL",
            "error": "RESULT_NOT_FOUND",
            "path": str(path),
        }, indent=2))
        return 1

    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "verification_stage": "V83.32A",
            "verification_status": "FAIL",
            "error": "INVALID_RESULT_FILE",
            "detail": str(exc),
        }, indent=2))
        return 1

    if not isinstance(result, dict):
        print(json.dumps({
            "verification_stage": "V83.32A",
            "verification_status": "FAIL",
            "error": "RESULT_NOT_OBJECT",
        }, indent=2))
        return 1

    verification = evaluate_verification(result)
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0 if verification["verification_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
