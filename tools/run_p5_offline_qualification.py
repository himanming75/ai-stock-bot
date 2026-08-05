from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker_integration.p5_models import default_offline_policy
from broker_integration.p5_paths import P5Paths
from broker_integration.p5_qualification import run_long_run_qualification


paths = P5Paths(ROOT)

def cycle_runner(cycle_number: int):
    return {
        "cycle_number": cycle_number,
        "status": "PASS",
        "reconciliation_passed": True,
        "new_order_submission_allowed": True,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }

result = run_long_run_qualification(
    policy=default_offline_policy(),
    cycle_runner=cycle_runner,
    checkpoint_path=paths.checkpoint,
    result_path=paths.result,
)
print(json.dumps({
    "stage": result["stage"],
    "state": result["state"],
    "status": result["status"],
    "qualified": result["qualified"],
    "successful_cycles": result["metrics"]["successful_cycles"],
    "failed_cycles": result["metrics"]["failed_cycles"],
    "fault_matrix_passed": result["fault_matrix"]["passed"],
    "actual_paper_long_run_qualified": False,
    "paper_complete": False,
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
