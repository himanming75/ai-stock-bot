from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

def create_reject_plan(output_path: Path) -> dict:
    canonical = "SPY|buy|market|qty=0.01|notional=5|day|p3-reject"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    plan = {
        "stage": "P3_PAPER_REJECT_VALIDATION_PLAN",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "plan_id": f"p3reject_{digest[:20]}",
        "client_order_id": f"p3r-{digest[:24]}",
        "expected_http_statuses": [400, 422],
        "expected_reason": "QTY_AND_NOTIONAL_MUTUALLY_EXCLUSIVE",
        "payload": {
            "symbol": "SPY",
            "qty": "0.01",
            "notional": "5",
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "client_order_id": f"p3r-{digest[:24]}",
        },
        "blocked": False,
        "blockers": [],
        "actual_external_network_used": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan
