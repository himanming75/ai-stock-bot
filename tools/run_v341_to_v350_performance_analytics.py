from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from performance_analytics.service import (
    PerformanceAnalyticsService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--portfolio-metrics-ledger",
        default=(
            "release/v321_330_realtime_portfolio_monitoring/"
            "actual/portfolio_metrics_ledger.jsonl"
        ),
    )
    parser.add_argument(
        "--portfolio-snapshot",
        default=(
            "release/v321_330_realtime_portfolio_monitoring/"
            "actual/portfolio_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--risk-snapshot",
        default=(
            "release/v331_340_realtime_risk_monitoring/"
            "actual/risk_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v341_350_performance_analytics/actual"
        ),
    )
    parser.add_argument(
        "--annualization-periods",
        type=int,
        default=252,
    )
    parser.add_argument(
        "--risk-free-rate-percent",
        default="0",
    )
    args = parser.parse_args()

    result = PerformanceAnalyticsService().evaluate(
        portfolio_metrics_ledger_path=Path(
            args.portfolio_metrics_ledger
        ),
        portfolio_snapshot_path=Path(
            args.portfolio_snapshot
        ),
        risk_snapshot_path=Path(args.risk_snapshot),
        output_dir=Path(args.output_dir),
        annualization_periods=max(
            1, args.annualization_periods
        ),
        risk_free_rate_percent=args.risk_free_rate_percent,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return (
        0
        if result["status"] in {
            "PASS",
            "PASS_WITH_WARNINGS",
        }
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
