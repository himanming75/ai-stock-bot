from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = {
    "p2_actual_validation": (
        ROOT
        / "release/p2_actual_paper_execution/actual/"
          "p2_actual_validation.json"
    ),
    "p3_actual_validation": (
        ROOT
        / "release/p3_order_fill_portfolio_sync/actual/"
          "p3_actual_validation.json"
    ),
    "p4_actual_validation": (
        ROOT
        / "release/p4_autonomous_paper_runtime/actual/"
          "p4_actual_validation.json"
    ),
}

checks = {}
for name, path in required.items():
    checks[name] = (
        path.exists()
        and json.loads(path.read_text(encoding="utf-8-sig"))
        .get("validated") is True
    )

result = {
    "stage": "P5_ACTUAL_PREFLIGHT",
    "status": "PASS",
    "actual_long_run_allowed": all(checks.values()),
    "checks": checks,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
