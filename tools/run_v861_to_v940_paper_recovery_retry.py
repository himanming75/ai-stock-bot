from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_recovery_retry.service import PaperRecoveryRetryService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--retry-queue",
        default=(
            "release/v781_860_paper_submit_engine/"
            "actual/paper_submit_retry_queue.json"
        ),
    )
    parser.add_argument(
        "--recovery-queue",
        default=(
            "release/v781_860_paper_submit_engine/"
            "actual/paper_submit_recovery_queue.json"
        ),
    )
    parser.add_argument(
        "--checkpoint",
        default=(
            "release/v861_940_paper_recovery_retry/"
            "actual/recovery_checkpoint.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=(
            "release/v861_940_paper_recovery_retry/"
            "config/recovery_retry_policy.json"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=(
            "release/v861_940_paper_recovery_retry/actual"
        ),
    )
    args = parser.parse_args()

    result = PaperRecoveryRetryService().evaluate(
        retry_queue_path=Path(args.retry_queue),
        recovery_queue_path=Path(args.recovery_queue),
        checkpoint_path=Path(args.checkpoint),
        policy_path=Path(args.policy),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
