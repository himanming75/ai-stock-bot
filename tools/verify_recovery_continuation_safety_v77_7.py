from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.recovery_continuation_safety_v77_7 import digest, load_json, summary


def verify_output(output_dir: Path) -> dict:
    result = load_json(
        output_dir/"recovery_continuation_safety_verification_v77_7.json"
    )
    saved_summary = load_json(
        output_dir/"recovery_continuation_safety_summary_v77_7.json"
    )
    errors: list[str] = []

    expected_hash = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    if result.get("verification_sha256") != expected_hash:
        errors.append("verification self-hash mismatch")
    if saved_summary != summary(result):
        errors.append("summary mismatch")

    vr = result.get("verification_result", {})
    report = result.get("continuation_report", {})
    checks = report.get("checks", {})
    required_checks = (
        "duplicate_client_order_rejected",
        "new_order_id_unique",
        "new_fill_id_unique",
        "new_order_sequence_contiguous",
        "new_fill_sequence_contiguous",
        "new_event_sequence_contiguous",
        "source_order_ids_preserved",
        "source_fill_ids_preserved",
        "reconciliation_pass",
        "continued_checkpoint_valid",
        "continued_checkpoint_changed",
        "order_count_incremented",
        "fill_count_incremented",
        "event_count_incremented",
        "actual_orders_submitted_zero",
        "network_unused",
    )
    for key in required_checks:
        if checks.get(key) is not True:
            errors.append(f"continuation check failed: {key}")

    validations = (
        (result.get("status") == "PASS", "status is not PASS"),
        (result.get("decision") == "recovery_continuation_safety_established",
         "decision mismatch"),
        (vr.get("failed_gate_count") == 0, "failed gate count must be zero"),
        (vr.get("failed_gate_ids") == [], "failed gate IDs must be empty"),
        (report.get("status") == "PASS", "continuation status is not PASS"),
        (result.get("network_allowed") is False, "network must remain disabled"),
        (result.get("broker_connected") is False, "broker must remain disconnected"),
        (result.get("actual_orders_submitted") == 0, "actual orders must remain zero"),
        (result.get("live_trading_authorized") is False,
         "live trading must remain unauthorized"),
        (result.get("next_phase") == "V77_8_MULTI_ORDER_CONTINUATION_STRESS",
         "next phase mismatch"),
    )
    for passed, message in validations:
        if not passed:
            errors.append(message)

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "recovery_continuation_safety_sha256":
            result.get("recovery_continuation_safety_sha256"),
        "continued_checkpoint_sha256":
            report.get("continued_checkpoint_sha256"),
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
