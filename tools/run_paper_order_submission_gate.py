from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_submission_gate.service import PaperSubmissionService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument(
        "--tickets",
        default="release/order_ticket_generator/actual/order_ticket_snapshot.json",
    )
    parser.add_argument(
        "--policy",
        default="release/paper_submission_gate/config/submission_policy.json",
    )
    parser.add_argument(
        "--token",
        default="release/paper_submission_gate/actual/paper_submission_token.json",
    )
    parser.add_argument(
        "--output",
        default="release/paper_submission_gate/actual/submission_result.json",
    )
    args = parser.parse_args()

    result = PaperSubmissionService().submit(
        ticket_snapshot_path=Path(args.tickets),
        policy_path=Path(args.policy),
        token_path=Path(args.token),
        nonce=args.nonce,
        output_path=Path(args.output),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
