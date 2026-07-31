from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.sandbox_broker_adapter_v77_2 import digest, load_json, summary_from


def verify_output(output_dir: Path) -> dict:
    result = load_json(output_dir / "sandbox_broker_adapter_verification_v77_2.json")
    summary = load_json(output_dir / "sandbox_broker_adapter_summary_v77_2.json")
    errors: list[str] = []

    expected_hash = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    if result.get("verification_sha256") != expected_hash:
        errors.append("verification self-hash mismatch")
    if summary != summary_from(result):
        errors.append("summary mismatch")

    vr = result.get("verification_result", {})
    checks = (
        (result.get("status") == "PASS", "status is not PASS"),
        (
            result.get("decision") == "sandbox_broker_adapter_established",
            "decision mismatch",
        ),
        (vr.get("failed_gate_count") == 0, "failed gate count must be zero"),
        (vr.get("failed_gate_ids") == [], "failed gate IDs must be empty"),
        (result.get("environment") == "offline", "environment mismatch"),
        (result.get("network_allowed") is False, "network must be disabled"),
        (result.get("broker_connected") is False, "broker must be disconnected"),
        (result.get("actual_orders_submitted") == 0, "actual orders must be zero"),
        (result.get("fills_created") == 0, "fills must be zero"),
        (
            result.get("live_trading_authorized") is False,
            "live trading must be unauthorized",
        ),
        (
            result.get("next_phase") == "V77_3_ORDER_LIFECYCLE_SIMULATOR",
            "next phase mismatch",
        ),
    )
    for passed, message in checks:
        if not passed:
            errors.append(message)

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "sandbox_broker_adapter_sha256": result.get("sandbox_broker_adapter_sha256"),
        "verification_sha256": result.get("verification_sha256"),
        "next_phase": result.get("next_phase"),
    }


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    checked = verify_output(Path(args.output_dir))
    print(json.dumps(checked, indent=2))
    return 0 if checked["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(cli())
