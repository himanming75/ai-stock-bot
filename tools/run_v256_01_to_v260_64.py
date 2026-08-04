from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from autonomous_paper_trading.engine import evaluate

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
args = parser.parse_args()
r = evaluate(ROOT, allow_network=args.allow_paper_network)
print(json.dumps({
    "stage": r["stage"],
    "state": r["state"],
    "status": r["status"],
    "session_id": r["session_id"],
    "market_open": r["market_open"],
    "blocking_reasons": r["blocking_reasons"],
    "autonomous_cycle_enabled": r["autonomous_cycle_enabled"],
    "real_paper_submission_enabled": r["real_paper_submission_enabled"],
    "actual_paper_orders_submitted": r["actual_paper_orders_submitted"],
    "actual_live_orders_submitted": 0,
    "next_phase": r["next_phase"],
}, indent=2, sort_keys=True))
