
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_runtime.performance_analytics_v82_09_12 import (
    run_shadow_performance_analytics,
)

result = run_shadow_performance_analytics(
    equity_history_path=(
        ROOT / "release/v81_09_to_v81_12/actual/"
        "shadow_equity_history.jsonl"
    ),
    portfolio_state_path=(
        ROOT / "release/v81_09_to_v81_12/actual/"
        "shadow_portfolio_state.json"
    ),
    cycle_ledger_path=(
        ROOT / "release/v82_01_to_v82_04/actual/"
        "autonomous_shadow_cycle_ledger.jsonl"
    ),
    policy_path=(
        ROOT / "release/v82_09_to_v82_12/input/"
        "shadow_performance_policy.json"
    ),
    analytics_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_performance_analytics.json"
    ),
    health_report_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_cycle_health_report.json"
    ),
    dashboard_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_performance_dashboard_state.json"
    ),
    result_path=(
        ROOT / "release/v82_09_to_v82_12/actual/"
        "shadow_performance_result.json"
    ),
)

print(json.dumps(result, indent=2, sort_keys=True))
print("RESULT_FILE=" + result["result_path"])
raise SystemExit(0 if result["status"] == "PASS" else 2)
