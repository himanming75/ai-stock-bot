from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .market_clock import MarketClock, SchedulerPolicy
from .monitor import OrderLifecycleMonitor
from .order_queue import SafeOrderQueue
from .session import PaperSessionCoordinator
from .sync import AccountPositionSyncPreview


def run_r16_to_r20(root: Path) -> dict[str, Any]:
    actual = root / "release/r16_to_r20_realtime_paper_ops/actual"
    actual.mkdir(parents=True, exist_ok=True)

    runtime_session = json.loads(
        (
            root / "release/r6_runtime_session_manager/actual/"
                   "last_session_preview.json"
        ).read_text(encoding="utf-8-sig")
    )
    bundle_b = json.loads(
        (
            root / "release/bundle_b_r11_to_r13_broker_multi_account/"
                   "actual/bundle_b_result.json"
        ).read_text(encoding="utf-8-sig")
    )

    market_clock = MarketClock().evaluate(
        observed_at=datetime(
            2026, 8, 5, 15, 0, tzinfo=timezone.utc
        ),
        holiday=False,
        early_close=False,
    )
    scheduler = SchedulerPolicy().evaluate(
        market_clock=market_clock,
        p2_validated=False,
        p3_validated=False,
    )
    paper_session = PaperSessionCoordinator().create(
        runtime_session=runtime_session,
        market_state=market_clock,
    )

    sync = AccountPositionSyncPreview().reconcile(
        local_account={
            "cash": "100000",
            "equity": "100000",
            "buying_power": "200000",
        },
        broker_account_fixture={
            "cash": "100000",
            "equity": "100000",
            "buying_power": "200000",
        },
        local_positions=[],
        broker_positions_fixture=[],
    )

    routed = None
    for result in bundle_b.get("routing_results", []):
        for route in result.get("routes", []):
            if route.get("route_allowed") is True:
                routed = route
                break
        if routed:
            break
    if routed is None:
        raise ValueError("NO_ALLOWED_OFFLINE_ROUTE")

    queue_path = actual / "safe_order_queue.jsonl"
    if queue_path.exists():
        queue_path.unlink()
    queue = SafeOrderQueue(queue_path)
    queued = queue.enqueue(routed_order=routed)

    ledger_path = actual / "order_lifecycle_ledger.jsonl"
    if ledger_path.exists():
        ledger_path.unlink()
    monitor = OrderLifecycleMonitor(ledger_path)
    transitions = [
        monitor.transition(
            queue_id=queued.queue_id,
            previous_state="QUEUED_PREVIEW",
            new_state="VALIDATED_PREVIEW",
            reason="OFFLINE_POLICY_VALIDATION",
        ),
        monitor.transition(
            queue_id=queued.queue_id,
            previous_state="VALIDATED_PREVIEW",
            new_state="MONITORED_PREVIEW",
            reason="OFFLINE_MONITORING_FIXTURE",
        ),
        monitor.transition(
            queue_id=queued.queue_id,
            previous_state="MONITORED_PREVIEW",
            new_state="COMPLETED_PREVIEW",
            reason="OFFLINE_LIFECYCLE_COMPLETE",
        ),
    ]

    checks = {
        "paper_session_pass": paper_session["status"] == "PASS",
        "market_clock_created": bool(market_clock["market_phase"]),
        "automatic_start_disabled": (
            market_clock["automatic_runtime_start_enabled"] is False
        ),
        "scheduler_blocked_without_actuals": (
            scheduler["cycle_preview_allowed"] is False
        ),
        "sync_preview_created": sync["account_in_sync"] is True,
        "broker_read_not_performed": (
            sync["actual_broker_read_performed"] is False
        ),
        "queue_created": queued.state == "QUEUED_PREVIEW",
        "dispatch_disabled": queued.dispatch_allowed is False,
        "lifecycle_completed": (
            transitions[-1]["new_state"] == "COMPLETED_PREVIEW"
        ),
        "automatic_retry_disabled": all(
            row["automatic_retry_enabled"] is False
            for row in transitions
        ),
        "automatic_replay_disabled": all(
            row["automatic_order_replay_enabled"] is False
            for row in transitions
        ),
    }

    result = {
        "stage": "R16_TO_R20_REALTIME_PAPER_OPERATIONS_PREPARATION",
        "state": "REALTIME_PAPER_OPERATIONS_OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "r16_paper_session_coordinator": "READY",
        "r17_market_clock_scheduler": "READY",
        "r18_account_position_sync_preview": "READY",
        "r19_safe_order_queue": "READY",
        "r20_order_lifecycle_monitor": "READY",
        "paper_session": paper_session,
        "market_clock": market_clock,
        "scheduler_policy": scheduler,
        "sync_preview": sync,
        "queued_order": queued.as_json(),
        "lifecycle_transitions": transitions,
        "actual_paper_session_started": False,
        "actual_market_api_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_network_used": False,
        "actual_broker_write_used": False,
        "actual_order_dispatch_performed": False,
        "automatic_runtime_start_enabled": False,
        "automatic_order_submission_enabled": False,
        "automatic_order_replay_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_action": "P2_P3_ACTUAL_VALIDATION_THEN_R16_ACTUAL_PAPER_SESSION",
    }
    (actual / "r16_to_r20_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
