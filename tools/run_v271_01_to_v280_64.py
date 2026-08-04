from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from multi_timeframe_strategy.engine import evaluate

r = evaluate(ROOT)
c = r["final_candidate"]
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "strategy_count": len(r["strategy_rows"]),
    "eligible_strategy_count": len([x for x in r["strategy_rows"] if x.get("eligible")]),
    "final_symbol": c.get("symbol"),
    "final_action": c.get("action"),
    "ensemble_score": c.get("ensemble_score"),
    "total_projected_risk_pct": r["allocation"]["total_projected_risk_pct"],
    "execution_authorized": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
