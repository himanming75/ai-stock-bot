from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from approval_execution_planning.service import (
    ApprovalExecutionPlanningService,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allocation",
        default=(
            "release/v541_590_portfolio_risk_intelligence/"
            "actual/portfolio_risk_latest.json"
        ),
    )
    parser.add_argument(
        "--approval",
        default=(
            "release/v401_430_approval_framework/"
            "actual/approval_framework_latest.json"
        ),
    )
    parser.add_argument(
        "--market",
        default=(
            "release/v591_640_approval_execution_planning/"
            "fixtures/execution_market_fixture.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v591_640_approval_execution_planning/"
            "config/execution_planning_policy.json"
        ),
    )
    parser.add_argument(
        "--prior-plans",
        default=(
            "release/v591_640_approval_execution_planning/"
            "actual/prior_plan_registry.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v591_640_approval_execution_planning/actual"
        ),
    )
    args = parser.parse_args()

    result = ApprovalExecutionPlanningService().evaluate(
        allocation_path=Path(args.allocation),
        approval_path=Path(args.approval),
        market_path=Path(args.market),
        policy_path=Path(args.policy),
        prior_plans_path=Path(args.prior_plans),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
