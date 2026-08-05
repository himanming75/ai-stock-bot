from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from realtime_risk_monitoring.service import (
    RealtimeRiskMonitoringService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--portfolio-snapshot",
        default=(
            "release/v321_330_realtime_portfolio_monitoring/"
            "actual/portfolio_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--portfolio-metrics-ledger",
        default=(
            "release/v321_330_realtime_portfolio_monitoring/"
            "actual/portfolio_metrics_ledger.jsonl"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v331_340_realtime_risk_monitoring/"
            "config/risk_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v331_340_realtime_risk_monitoring/actual"
        ),
    )
    args = parser.parse_args()

    result = RealtimeRiskMonitoringService().evaluate(
        portfolio_snapshot_path=Path(args.portfolio_snapshot),
        portfolio_metrics_ledger_path=Path(
            args.portfolio_metrics_ledger
        ),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
