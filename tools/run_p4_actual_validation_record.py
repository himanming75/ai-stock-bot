from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.actual_validation import validation_status
from broker_integration.io import write_json

status = validation_status(ROOT)
kill_switch = json.loads(
    (
        ROOT / "release/p1_broker_consolidation/actual/"
               "kill_switch.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "p2_actual_validated": status["p2_actual_validated"],
    "p3_actual_validated": status["p3_actual_validated"],
    "kill_switch_inactive": (
        kill_switch.get("kill_switch_active") is False
    ),
    "runtime_offline_qualified": (
        ROOT / "release/p4_autonomous_paper_runtime/actual/"
               "p4_runtime_result.json"
    ).exists(),
}
validated = all(checks.values())
result = {
    "stage": "P4_ACTUAL_VALIDATION",
    "validated": validated,
    "status": "PASS" if validated else "BLOCKED",
    "checks": checks,
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "actual_live_orders_submitted": 0,
    "note": (
        "This records actual broker connectivity and prerequisite "
        "validation. Multi-cycle autonomous order execution remains "
        "part of P5 actual qualification."
    ),
}
write_json(
    ROOT / "release/p4_autonomous_paper_runtime/actual/"
           "p4_actual_validation.json",
    result,
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if validated else 1)
