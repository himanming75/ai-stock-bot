from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from broker.broker_state_checkpoint_v77_5 import (
    BrokerStateCheckpointManager,
)
from tools.broker_state_checkpoint_v77_5 import digest, load_json, summary


def verify_output(output_dir: Path) -> dict:
    result = load_json(output_dir/"broker_state_checkpoint_verification_v77_5.json")
    saved_summary = load_json(output_dir/"broker_state_checkpoint_summary_v77_5.json")
    sample_path = output_dir/"sample_broker_state_checkpoint_v77_5.json"
    errors: list[str] = []

    expected_hash = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    if result.get("verification_sha256") != expected_hash:
        errors.append("verification self-hash mismatch")
    if saved_summary != summary(result):
        errors.append("summary mismatch")
    if not sample_path.is_file():
        errors.append("sample checkpoint missing")
    else:
        try:
            loaded = BrokerStateCheckpointManager().read(sample_path)
            if loaded.as_dict() != result.get("sample_checkpoint"):
                errors.append("sample checkpoint mismatch")
        except Exception as exc:
            errors.append(f"sample checkpoint invalid: {exc}")

    vr = result.get("verification_result", {})
    checks = (
        (result.get("status") == "PASS", "status is not PASS"),
        (result.get("decision") == "broker_state_checkpoint_established",
         "decision mismatch"),
        (vr.get("failed_gate_count") == 0, "failed gate count must be zero"),
        (vr.get("failed_gate_ids") == [], "failed gate IDs must be empty"),
        (result.get("sample_checkpoint", {}).get("source_reconciliation_status") == "PASS",
         "checkpoint reconciliation status mismatch"),
        (result.get("network_allowed") is False, "network must remain disabled"),
        (result.get("broker_connected") is False, "broker must remain disconnected"),
        (result.get("actual_orders_submitted") == 0, "actual orders must remain zero"),
        (result.get("live_trading_authorized") is False,
         "live trading must remain unauthorized"),
        (result.get("next_phase") == "V77_6_RESTART_RECOVERY_REPLAY",
         "next phase mismatch"),
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
        "broker_state_checkpoint_sha256":
            result.get("broker_state_checkpoint_sha256"),
        "sample_state_sha256":
            result.get("sample_checkpoint", {}).get("state_sha256"),
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
