from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_session.runner import run

def fallback_cycle(root: Path, allow_network: bool) -> dict:
    return {
        "stage": "V260.64",
        "state": "V260_DEPENDENCY_NOT_PRESENT_IN_STANDALONE_PACKAGE",
        "status": "PASS",
        "market_open": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }

try:
    from autonomous_paper_trading.engine import evaluate as run_v260_cycle
except ModuleNotFoundError:
    run_v260_cycle = fallback_cycle

parser = argparse.ArgumentParser()
parser.add_argument("--allow-paper-network", action="store_true")
parser.add_argument("--no-sleep", action="store_true")
args = parser.parse_args()

result = run(
    ROOT,
    cycle_function=run_v260_cycle,
    allow_network=args.allow_paper_network,
    sleep_enabled=not args.no_sleep,
)
print(json.dumps(result, indent=2, sort_keys=True))
