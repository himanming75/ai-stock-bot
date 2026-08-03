from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_production_release.engine import build_release


def main() -> int:
    result = build_release(ROOT)
    summary = {
        "stage": result["stage"],
        "stage_range": result["stage_range"],
        "state": result["state"],
        "status": result["status"],
        "technical_ready": result["technical_ready"],
        "production_ready": result["production_ready"],
        "blocking_prerequisites": result["blocking_prerequisites"],
        "time_based_pending": result["time_based_pending"],
        "system_based_pending": result["system_based_pending"],
        "indicator_layout": result["layout"]["indicator_layout"],
        "integrity_passed": result["integrity"]["integrity_passed"],
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
                ROOT / "release/v88_17_to_v88_24/actual/"
                "paper_production_release_result.json"
            ).resolve()
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
