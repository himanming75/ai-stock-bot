from __future__ import annotations
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

module = importlib.import_module("autonomous_risk_governor.io")

checks = {
    "project_root_on_sys_path": str(ROOT) in sys.path,
    "package_imported": module.__name__ == "autonomous_risk_governor.io",
    "read_json_present": callable(getattr(module, "read_json", None)),
    "write_json_present": callable(getattr(module, "write_json", None)),
    "append_jsonl_present": callable(getattr(module, "append_jsonl", None)),
}

result = {
    "hotfix": "V391.03A2",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "project_root": str(ROOT),
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}

print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
