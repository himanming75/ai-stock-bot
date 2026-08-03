from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.paper_stability_runtime_v83_81_88 import (
    run_paper_stability_runtime_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed-at", default="")
    args = parser.parse_args()

    root = ROOT
    actual = root / "release/v83_81_to_v83_88/actual"
    result = run_paper_stability_runtime_readiness(
        multi_day_result_path=(
            root / "release/v83_77_to_v83_80/actual/"
            "multi_day_paper_validation_result.json"
        ),
        daily_ledger_path=(
            root / "release/v83_77_to_v83_80/actual/"
            "multi_day_paper_validation_daily.jsonl"
        ),
        policy_path=(
            root / "release/v83_81_to_v83_88/input/"
            "paper_stability_runtime_policy.json"
        ),
        certificate_path=actual / "paper_stability_certificate.json",
        runtime_policy_path=actual / "extended_paper_runtime_policy.json",
        audit_path=actual / "paper_stability_runtime_audit.json",
        dashboard_path=actual / "paper_stability_runtime_dashboard_state.json",
        result_path=actual / "paper_stability_runtime_result.json",
        observed_at_override=args.observed_at,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
