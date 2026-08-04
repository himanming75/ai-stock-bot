from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paper_qualification.engine import evaluate

r = evaluate(ROOT)
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "sessions_completed": r["sessions_completed"],
    "cycles_completed": r["cycles_completed"],
    "reconciliation_passed": r["reconciliation"]["passed"],
    "reconciliation_pass_rate_pct": r["reconciliation_pass_rate_pct"],
    "order_state_coverage_pct": r["order_state_coverage"]["coverage_pct"],
    "win_rate_pct": r["performance_metrics"]["win_rate_pct"],
    "profit_factor": r["performance_metrics"]["profit_factor"],
    "maximum_drawdown_pct": r["performance_metrics"]["maximum_drawdown_pct"],
    "failed_check_count": len(r["failed"]),
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
