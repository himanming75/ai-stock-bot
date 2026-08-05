from __future__ import annotations
import importlib
import json

module = importlib.import_module("autonomous_risk_governor.io")

checks = {
    "read_json_present": callable(getattr(module, "read_json", None)),
    "write_json_present": callable(getattr(module, "write_json", None)),
    "append_jsonl_present": callable(getattr(module, "append_jsonl", None)),
}

result = {
    "hotfix": "V391.03A1",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
