
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_runtime.trade_authorization_v82_17_20 import (
    run_shadow_trade_authorization,
)

parser = argparse.ArgumentParser()
parser.add_argument("--market-session-closed", action="store_true")
args = parser.parse_args()

result = run_shadow_trade_authorization(
    signal_path=(
        ROOT / "release/v81_01_to_v81_04/actual/"
        "shadow_trade_observation.json"
    ),
    risk_result_path=(
        ROOT / "release/v82_13_to_v82_16/actual/"
        "shadow_risk_controller_result.json"
    ),
    policy_path=(
        ROOT / "release/v82_17_to_v82_20/input/"
        "shadow_trade_authorization_policy.json"
    ),
    authorization_ledger_path=(
        ROOT / "release/v82_17_to_v82_20/actual/"
        "shadow_trade_authorization_ledger.jsonl"
    ),
    authorization_snapshot_path=(
        ROOT / "release/v82_17_to_v82_20/actual/"
        "shadow_trade_authorization_snapshot.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_17_to_v82_20/actual/"
        "shadow_trade_authorization_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_17_to_v82_20/actual/"
        "shadow_trade_authorization_result.json"
    ),
    market_session_open=not args.market_session_closed,
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
