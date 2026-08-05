from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification_alert_routing.service import (
    NotificationAlertRoutingService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--risk",
        default=(
            "release/v331_340_realtime_risk_monitoring/"
            "actual/risk_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--health",
        default=(
            "release/v351_360_system_health_monitoring/"
            "actual/system_health_latest.json"
        ),
    )
    parser.add_argument(
        "--performance",
        default=(
            "release/v341_350_performance_analytics/"
            "actual/performance_analytics_latest.json"
        ),
    )
    parser.add_argument(
        "--controller",
        default=(
            "release/paper_automation_controller/"
            "actual/controller_summary.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v361_370_notification_alert_routing/"
            "config/notification_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v361_370_notification_alert_routing/actual"
        ),
    )
    args = parser.parse_args()

    result = NotificationAlertRoutingService().evaluate(
        risk_path=Path(args.risk),
        health_path=Path(args.health),
        performance_path=Path(args.performance),
        controller_path=Path(args.controller),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
