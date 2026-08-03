from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_trading.portfolio_pnl_v81_09_12 import (
    run_shadow_portfolio,
)


def main() -> int:
    result = run_shadow_portfolio(
        execution_result_path=(
            ROOT / "release/v81_05_to_v81_08/actual/"
            "shadow_execution_result.json"
        ),
        fill_ledger_path=(
            ROOT / "release/v81_05_to_v81_08/actual/"
            "shadow_fill_ledger.jsonl"
        ),
        policy_path=(
            ROOT / "release/v81_09_to_v81_12/input/"
            "shadow_portfolio_policy.json"
        ),
        portfolio_state_path=(
            ROOT / "release/v81_09_to_v81_12/actual/"
            "shadow_portfolio_state.json"
        ),
        market_prices_path=(
            ROOT / "release/v81_09_to_v81_12/input/"
            "shadow_market_prices.json"
        ),
        equity_history_path=(
            ROOT / "release/v81_09_to_v81_12/actual/"
            "shadow_equity_history.jsonl"
        ),
        daily_report_path=(
            ROOT / "release/v81_09_to_v81_12/actual/"
            "shadow_daily_portfolio_report.json"
        ),
        dashboard_path=(
            ROOT / "release/v81_09_to_v81_12/actual/"
            "shadow_portfolio_dashboard_state.json"
        ),
        recovery_snapshot_path=(
            ROOT / "release/v81_09_to_v81_12/actual/"
            "shadow_portfolio_recovery_snapshot.json"
        ),
        result_path=(
            ROOT / "release/v81_09_to_v81_12/actual/"
            "shadow_portfolio_result.json"
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
