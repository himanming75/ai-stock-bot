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


def _stage_summary(name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "result_hash": canonical_hash(result),
    }


def build_cycle_report(
    risk_result: dict[str, Any],
    authorization_result: dict[str, Any],
    dispatch_result: dict[str, Any],
    simulator_result: dict[str, Any],
    accounting_result: dict[str, Any],
    reconciliation_result: dict[str, Any],
    cycle_id: str,
    completed_cycle_ids: set[str],
) -> dict[str, Any]:
    cycle_id = str(cycle_id).strip()

    stages = {
        "risk": risk_result,
        "authorization": authorization_result,
        "dispatch": dispatch_result,
        "simulation": simulator_result,
        "accounting": accounting_result,
        "reconciliation": reconciliation_result,
    }

    checks = {
        "cycle_id_present": bool(cycle_id),
        "cycle_not_completed": cycle_id not in completed_cycle_ids,

        "risk_status_pass": risk_result.get("status") == "PASS",
        "risk_operations_allowed": (
            risk_result.get("risk_operations_allowed") is True
        ),

        "authorization_status_pass": authorization_result.get("status") == "PASS",
        "authorization_stage_valid": authorization_result.get("stage") == "V392.09A",
        "dispatch_context_created": (
            authorization_result.get("dispatch_context_created") is True
        ),

        "dispatch_status_pass": dispatch_result.get("status") == "PASS",
        "dispatch_stage_valid": dispatch_result.get("stage") == "V392.10A",
        "dispatch_ready": (
            dispatch_result.get("state") == "LOCAL_PAPER_DISPATCH_ENGINE_READY"
        ),
        "dispatch_accepted": dispatch_result.get("local_dispatch_accepted") is True,

        "simulator_status_pass": simulator_result.get("status") == "PASS",
        "simulator_stage_valid": simulator_result.get("stage") == "V392.11A",
        "simulator_ready": (
            simulator_result.get("state") == "PAPER_EXECUTION_SIMULATOR_READY"
        ),
        "simulated_fill_created": (
            simulator_result.get("simulated_fill_created") is True
        ),

        "accounting_status_pass": accounting_result.get("status") == "PASS",
        "accounting_stage_valid": accounting_result.get("stage") == "V392.12A",
        "accounting_ready": (
            accounting_result.get("state")
            == "FILL_ACCOUNTING_POSITION_UPDATE_READY"
        ),
        "portfolio_updated": accounting_result.get("portfolio_updated") is True,

        "reconciliation_status_pass": (
            reconciliation_result.get("status") == "PASS"
        ),
        "reconciliation_stage_valid": (
            reconciliation_result.get("stage") == "V392.13A"
        ),
        "reconciliation_ready": (
            reconciliation_result.get("state")
            == "PAPER_PORTFOLIO_RECONCILIATION_READY"
        ),
        "portfolio_reconciled": (
            reconciliation_result.get("portfolio_reconciled") is True
        ),

        "broker_write_disabled": all(
            result.get("broker_write_enabled") is False
            for result in stages.values()
            if "broker_write_enabled" in result
        ),
        "paper_submission_disabled": all(
            result.get("paper_submission_enabled") is False
            for result in stages.values()
            if "paper_submission_enabled" in result
        ),
        "live_submission_disabled": all(
            result.get("live_submission_enabled") is False
            for result in stages.values()
            if "live_submission_enabled" in result
        ),
        "paper_orders_zero": all(
            result.get("actual_paper_orders_submitted", 0) == 0
            for result in stages.values()
        ),
        "live_orders_zero": all(
            result.get("actual_live_orders_submitted", 0) == 0
            for result in stages.values()
        ),
    }

    approved = all(checks.values())

    stage_summaries = [
        _stage_summary("risk", risk_result),
        _stage_summary("authorization", authorization_result),
        _stage_summary("dispatch", dispatch_result),
        _stage_summary("simulation", simulator_result),
        _stage_summary("accounting", accounting_result),
        _stage_summary("reconciliation", reconciliation_result),
    ]

    cycle_core = {
        "cycle_version": "V392.14A",
        "cycle_id": cycle_id,
        "stage_summaries": stage_summaries,
        "portfolio_hash": (
            reconciliation_result.get("evaluation", {}).get("portfolio_hash")
        ),
        "registry_hash": (
            reconciliation_result.get("evaluation", {}).get("registry_hash")
        ),
        "accounting_event_hash": (
            reconciliation_result.get("evaluation", {}).get(
                "accounting_event_hash"
            )
        ),
        "target_environment": "LOCAL_PAPER",
        "broker_adapter": "NONE",
    }

    cycle_hash = canonical_hash(cycle_core)

    report = {
        **cycle_core,
        "cycle_hash": cycle_hash,
        "cycle_state": (
            "AUTONOMOUS_PAPER_CYCLE_COMPLETED"
            if approved
            else "AUTONOMOUS_PAPER_CYCLE_BLOCKED"
        ),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": (
            "AUTONOMOUS_PAPER_CYCLE_ACCEPTED"
            if approved
            else "AUTONOMOUS_PAPER_CYCLE_REJECTED"
        ),
        "approved": approved,
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "replay_detected": not checks["cycle_not_completed"],
        "cycle_report": report,
        "cycle_hash": cycle_hash,
        "required_action": (
            "ALLOW_FULL_AUTONOMOUS_PAPER_QUALIFICATION"
            if approved
            else "BLOCK_FULL_AUTONOMOUS_PAPER_QUALIFICATION"
        ),
    }
