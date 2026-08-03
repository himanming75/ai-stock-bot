from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime.performance_production_readiness_v83_89_96 import (
    run_performance_production_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed-at", default="")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    actual = root / "release/v83_89_to_v83_96/actual"
    result = run_performance_production_readiness(
        stability_result_path=(
            root / "release/v83_81_to_v83_88/actual/"
            "paper_stability_runtime_result.json"
        ),
        performance_snapshot_path=(
            root / "release/v83_89_to_v83_96/input/"
            "paper_performance_snapshot.json"
        ),
        policy_path=(
            root / "release/v83_89_to_v83_96/input/"
            "performance_production_readiness_policy.json"
        ),
        performance_report_path=actual / "paper_performance_report.json",
        performance_certificate_path=actual / "paper_performance_certificate.json",
        risk_gate_path=actual / "production_risk_gate.json",
        readiness_certificate_path=actual / "production_readiness_certificate.json",
        dashboard_path=(
            actual / "performance_production_readiness_dashboard_state.json"
        ),
        result_path=actual / "performance_production_readiness_result.json",
        observed_at_override=args.observed_at,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result['result_path']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
