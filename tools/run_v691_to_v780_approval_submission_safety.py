from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from approval_submission_safety.service import (
    ApprovalSubmissionSafetyService,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ticket-bundle",
        default=(
            "release/v641_690_paper_order_ticket_builder/"
            "actual/paper_order_ticket_bundle.json"
        ),
    )
    parser.add_argument(
        "--token",
        default=(
            "release/v691_780_approval_submission_safety/"
            "actual/approval_token.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v691_780_approval_submission_safety/"
            "config/submission_safety_policy.json"
        ),
    )
    parser.add_argument(
        "--market",
        default=(
            "release/v691_780_approval_submission_safety/"
            "fixtures/submission_market_fixture.json"
        ),
    )
    parser.add_argument(
        "--risk",
        default=(
            "release/v331_340_realtime_risk_monitoring/"
            "actual/risk_monitor_latest.json"
        ),
    )
    parser.add_argument(
        "--nonce-registry",
        default=(
            "release/v691_780_approval_submission_safety/"
            "actual/nonce_registry.json"
        ),
    )
    parser.add_argument(
        "--idempotency-registry",
        default=(
            "release/v691_780_approval_submission_safety/"
            "actual/idempotency_registry.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v691_780_approval_submission_safety/actual"
        ),
    )
    args = parser.parse_args()

    secret = os.environ.get(
        "AI_STOCK_BOT_SUBMISSION_SECRET",
        "SAFE_DEFAULT_INVALID_SECRET",
    )

    result = ApprovalSubmissionSafetyService().evaluate(
        ticket_bundle_path=Path(args.ticket_bundle),
        token_path=Path(args.token),
        policy_path=Path(args.policy),
        market_path=Path(args.market),
        risk_path=Path(args.risk),
        nonce_registry_path=Path(args.nonce_registry),
        idempotency_registry_path=Path(args.idempotency_registry),
        output_dir=Path(args.output_dir),
        secret=secret,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
