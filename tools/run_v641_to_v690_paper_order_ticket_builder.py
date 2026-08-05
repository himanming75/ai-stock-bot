from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_order_ticket_builder.service import (
    PaperOrderTicketBuilderService,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execution-planning",
        default=(
            "release/v591_640_approval_execution_planning/"
            "actual/execution_planning_latest.json"
        ),
    )
    parser.add_argument(
        "--market",
        default=(
            "release/v641_690_paper_order_ticket_builder/"
            "fixtures/ticket_market_fixture.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v641_690_paper_order_ticket_builder/"
            "config/ticket_policy.json"
        ),
    )
    parser.add_argument(
        "--prior-ticket-registry",
        default=(
            "release/v641_690_paper_order_ticket_builder/"
            "actual/prior_ticket_registry.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v641_690_paper_order_ticket_builder/actual"
        ),
    )
    args = parser.parse_args()

    result = PaperOrderTicketBuilderService().evaluate(
        execution_planning_path=Path(args.execution_planning),
        market_path=Path(args.market),
        policy_path=Path(args.policy),
        prior_ticket_registry_path=Path(
            args.prior_ticket_registry
        ),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
