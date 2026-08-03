from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_orchestrator.engine import run_orchestrator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed-at", default="")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--fail-after-step", default="")
    args = parser.parse_args()

    result = run_orchestrator(
        ROOT,
        observed_at_override=args.observed_at,
        resume=not args.no_resume,
        fail_after_step=args.fail_after_step,
    )
    summary = {
        "stage": result["stage"],
        "stage_range": result["stage_range"],
        "state": result["state"],
        "status": result["status"],
        "run_id": result["run_id"],
        "completed_step_count": result["completed_step_count"],
        "total_step_count": result["total_step_count"],
        "safe_mode": result["safe_mode"],
        "failed_step": result["failed_step"],
        "paper_only": result["paper_only"],
        "broker_write_enabled": result["broker_write_enabled"],
        "order_submission_enabled": result["order_submission_enabled"],
        "live_trading_enabled": result["live_trading_enabled"],
        "external_network_enabled": result["external_network_enabled"],
        "next_phase": result["next_phase"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v88_09_to_v88_16/actual/"
                "paper_orchestrator_result.json"
            ).resolve()
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
