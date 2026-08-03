from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.multi_day_paper_validation_v83_77_80 import (
    run_multi_day_paper_validation,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed-at", default="")
    parser.add_argument("--validation-date", default="")
    parser.add_argument("--minimum-days", type=int, default=3)
    parser.add_argument("--reset-ledger", action="store_true")
    args = parser.parse_args()

    root = ROOT
    actual = root / "release/v83_77_to_v83_80/actual"
    result = run_multi_day_paper_validation(
        autonomous_result_path=(
            root / "release/v83_73_to_v83_76/actual/"
            "paper_autonomous_mode_result.json"
        ),
        policy_path=(
            root / "release/v83_77_to_v83_80/input/"
            "multi_day_paper_validation_policy.json"
        ),
        daily_ledger_path=actual / "multi_day_paper_validation_daily.jsonl",
        summary_path=actual / "multi_day_paper_validation_summary.json",
        dashboard_path=(
            actual / "multi_day_paper_validation_dashboard_state.json"
        ),
        result_path=actual / "multi_day_paper_validation_result.json",
        observed_at_override=args.observed_at,
        validation_date_override=args.validation_date,
        minimum_days=args.minimum_days,
        reset_ledger=args.reset_ledger,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
