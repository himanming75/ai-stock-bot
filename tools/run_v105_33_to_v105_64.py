from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from final_release.engine import evaluate

def main() -> int:
    result = evaluate(ROOT)
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "release_id": result.get("release_id"),
        "release_version": result.get("release_version"),
        "base_commit": result.get("base_commit"),
        "project_complete": result.get("project_complete"),
        "production_release_created": result.get(
            "production_release_created"
        ),
        "paper_trading_ready": result.get("paper_trading_ready"),
        "live_trading_ready": result.get("live_trading_ready"),
        "readiness_passed": result.get("readiness", {}).get("passed"),
        "integrity_passed": result.get("integrity", {}).get("passed"),
        "acceptance_passed": result.get("acceptance", {}).get("passed"),
        "bundle_created": result.get("bundle", {}).get("created"),
        "bundle_file_count": result.get("bundle", {}).get("file_count"),
        "manual_approval_required": result.get(
            "manual_approval_required"
        ),
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
                ROOT / "release/v105_33_to_v105_64/actual/"
                "production_readiness_final_release_result.json"
            ).resolve()
        )
    )
    print(
        "FINAL_BUNDLE="
        + str(
            (
                ROOT / "release/v105_33_to_v105_64/bundle/"
                "AI_STOCK_BOT_V105_FINAL_RELEASE_BUNDLE.zip"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
