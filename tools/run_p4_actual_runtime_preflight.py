from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.p4_health import health_check
from broker_integration.p4_runtime_models import default_policy


policy = default_policy()
kill_switch_path = (
    ROOT
    / "release/p1_broker_consolidation/actual/kill_switch.json"
)
p2_validation_path = (
    ROOT
    / "release/p2_actual_paper_execution/actual/"
      "p2_actual_validation.json"
)
p3_validation_path = (
    ROOT
    / "release/p3_order_fill_portfolio_sync/actual/"
      "p3_actual_validation.json"
)

kill_switch = json.loads(
    kill_switch_path.read_text(encoding="utf-8-sig")
)
p2_validated = (
    p2_validation_path.exists()
    and json.loads(
        p2_validation_path.read_text(encoding="utf-8-sig")
    ).get("validated") is True
)
p3_validated = (
    p3_validation_path.exists()
    and json.loads(
        p3_validation_path.read_text(encoding="utf-8-sig")
    ).get("validated") is True
)

result = {
    "stage": "P4_ACTUAL_PREFLIGHT",
    "status": "PASS",
    "actual_runtime_allowed": (
        kill_switch.get("kill_switch_active") is False
        and p2_validated
        and p3_validated
    ),
    "kill_switch_inactive": (
        kill_switch.get("kill_switch_active") is False
    ),
    "p2_actual_validated": p2_validated,
    "p3_actual_validated": p3_validated,
    "policy": {
        "cycle_interval_seconds": policy.cycle_interval_seconds,
        "maximum_cycles_per_session": (
            policy.maximum_cycles_per_session
        ),
        "require_market_open": policy.require_market_open,
        "fail_closed": policy.fail_closed,
    },
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0)
