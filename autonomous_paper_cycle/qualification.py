from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def qualify_fully_autonomous_paper_trading(
    cycle_result: dict[str, Any],
    cycle_report: dict[str, Any],
    cycle_ledger_records: list[dict[str, Any]],
    completed_cycle_registry: dict[str, Any],
    reconciliation_result: dict[str, Any],
    risk_result: dict[str, Any],
    qualification_registry: dict[str, Any],
) -> dict[str, Any]:
    cycle_id = str(cycle_report.get("cycle_id", "")).strip()
    cycle_hash = str(cycle_report.get("cycle_hash", "")).strip()
    qualification_ids = qualification_registry.get("qualified_cycle_ids", [])
    completed_ids = completed_cycle_registry.get("completed_cycle_ids", [])

    matching_ledger_records = [
        record
        for record in cycle_ledger_records
        if record.get("evaluation", {}).get("cycle_report", {}).get("cycle_id")
        == cycle_id
    ]

    stage_summaries = cycle_report.get("stage_summaries", [])
    stage_names = [
        item.get("name") for item in stage_summaries if isinstance(item, dict)
    ]

    checks = {
        "cycle_stage_valid": cycle_result.get("stage") == "V392.14A",
        "cycle_status_pass": cycle_result.get("status") == "PASS",
        "cycle_ready": (
            cycle_result.get("state")
            == "AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR_READY"
        ),
        "cycle_completed": cycle_result.get("cycle_completed") is True,
        "qualification_allowed": (
            cycle_result.get("final_qualification_allowed") is True
        ),
        "cycle_id_present": bool(cycle_id),
        "cycle_hash_present": len(cycle_hash) == 64,
        "cycle_hash_matches": cycle_hash == cycle_result.get(
            "evaluation", {}
        ).get("cycle_hash"),
        "cycle_registry_contains_id": cycle_id in set(completed_ids),
        "cycle_registry_unique": (
            isinstance(completed_ids, list)
            and len(completed_ids) == len(set(completed_ids))
        ),
        "qualification_not_repeated": cycle_id not in set(qualification_ids),
        "ledger_record_present": bool(matching_ledger_records),
        "ledger_cycle_hash_matches": (
            bool(matching_ledger_records)
            and all(
                record.get("evaluation", {}).get("cycle_hash") == cycle_hash
                for record in matching_ledger_records
            )
        ),
        "all_required_stages_present": set(stage_names) == {
            "risk",
            "authorization",
            "dispatch",
            "simulation",
            "accounting",
            "reconciliation",
        },
        "all_stage_status_pass": (
            bool(stage_summaries)
            and all(item.get("status") == "PASS" for item in stage_summaries)
        ),
        "reconciliation_stage_valid": (
            reconciliation_result.get("stage") == "V392.13A"
        ),
        "portfolio_reconciled": (
            reconciliation_result.get("portfolio_reconciled") is True
        ),
        "reconciliation_valid": (
            reconciliation_result.get("evaluation", {}).get("valid") is True
        ),
        "risk_status_pass": risk_result.get("status") == "PASS",
        "risk_operations_allowed": (
            risk_result.get("risk_operations_allowed") is True
        ),
        "risk_fail_closed_capable": (
            risk_result.get("broker_write_enabled") is False
            and risk_result.get("paper_submission_enabled") is False
            and risk_result.get("live_submission_enabled") is False
        ),
        "replay_protection_enabled": (
            cycle_result.get("single_cycle_replay_protection_enabled") is True
        ),
        "fail_closed_enabled": cycle_result.get("fail_closed_enabled") is True,
        "broker_adapter_disabled": (
            cycle_result.get("broker_adapter_enabled") is False
        ),
        "broker_network_disabled": (
            cycle_result.get("broker_network_enabled") is False
        ),
        "broker_write_disabled": cycle_result.get("broker_write_enabled") is False,
        "paper_submission_disabled": (
            cycle_result.get("paper_submission_enabled") is False
        ),
        "live_submission_disabled": (
            cycle_result.get("live_submission_enabled") is False
        ),
        "paper_orders_zero": cycle_result.get(
            "actual_paper_orders_submitted"
        ) == 0,
        "live_orders_zero": cycle_result.get(
            "actual_live_orders_submitted"
        ) == 0,
    }

    qualified = all(checks.values())

    certificate_core = {
        "certificate_version": "V392.15A",
        "cycle_id": cycle_id,
        "cycle_hash": cycle_hash,
        "portfolio_hash": cycle_report.get("portfolio_hash"),
        "registry_hash": cycle_report.get("registry_hash"),
        "accounting_event_hash": cycle_report.get("accounting_event_hash"),
        "qualification_state": (
            "FULLY_AUTONOMOUS_LOCAL_PAPER_TRADING_READY"
            if qualified
            else "FULLY_AUTONOMOUS_LOCAL_PAPER_TRADING_BLOCKED"
        ),
        "broker_mode": "LOCAL_ONLY",
        "broker_adapter": "NONE",
        "external_order_submission": False,
    }

    certificate_hash = canonical_hash(certificate_core)
    certificate = {
        **certificate_core,
        "certificate_hash": certificate_hash,
        "qualified_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": (
            "FULL_AUTONOMOUS_PAPER_QUALIFICATION_ACCEPTED"
            if qualified
            else "FULL_AUTONOMOUS_PAPER_QUALIFICATION_REJECTED"
        ),
        "qualified": qualified,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "replay_detected": not checks["qualification_not_repeated"],
        "certificate": certificate,
        "certificate_hash": certificate_hash,
        "required_action": (
            "DECLARE_FULLY_AUTONOMOUS_LOCAL_PAPER_TRADING_READY"
            if qualified
            else "KEEP_FULLY_AUTONOMOUS_PAPER_TRADING_BLOCKED"
        ),
    }
