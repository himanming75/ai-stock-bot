from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from continuous_service_runtime.runtime import run_runtime

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ticks", type=int, default=None)
    args = parser.parse_args()

    result = run_runtime(ROOT, max_ticks=args.max_ticks)
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "runtime_id": result.get("runtime_id"),
        "source_engine_state": result.get("source_engine_state"),
        "tick_count": result.get("tick_count"),
        "heartbeat_count": result.get("heartbeat_count"),
        "checkpoint_generation": result.get("checkpoint", {}).get("generation"),
        "recovery_required": result.get("recovery", {}).get("recovery_required"),
        "runtime_started": result.get("runtime_started"),
        "runtime_stopped_cleanly": result.get("runtime_stopped_cleanly"),
        "background_service_running": result.get("background_service_running"),
        "approval_granted": result.get("approval_granted"),
        "execution_authorized": result.get("execution_authorized"),
        "actual_orders_submitted": result.get("actual_orders_submitted"),
        "paper_only": result.get("paper_only"),
        "next_phase": result.get("next_phase"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v104_33_to_v104_64/actual/"
                "continuous_service_runtime_result.json"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
