from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_submit_engine.service import PaperSubmitEngineService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--approved-queue",
        default=(
            "release/v691_780_approval_submission_safety/"
            "actual/approved_submission_queue.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v781_860_paper_submit_engine/"
            "config/paper_submit_engine_policy.json"
        ),
    )
    parser.add_argument(
        "--simulated-response",
        default=(
            "release/v781_860_paper_submit_engine/"
            "fixtures/simulated_broker_responses.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v781_860_paper_submit_engine/actual"
        ),
    )
    args = parser.parse_args()

    result = PaperSubmitEngineService().evaluate(
        approved_queue_path=Path(args.approved_queue),
        policy_path=Path(args.policy),
        simulated_response_path=Path(args.simulated_response),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
