from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.final_integrity_verification_v76_15 import digest, load_json

EXPECTED_NEXT = "V76_16_RELEASE_ARCHIVE_SEAL"


def verify_output(output_dir: Path) -> dict[str, Any]:
    result_path = output_dir / "final_integrity_verification_v76_15.json"
    summary_path = output_dir / (
        "final_integrity_verification_summary_v76_15.json"
    )
    text_path = output_dir / "final_integrity_verification_v76_15.txt"

    errors: list[str] = []
    result = load_json(result_path)
    summary = load_json(summary_path)

    stored = result.get("verification_sha256")
    calculated = digest({
        key: value
        for key, value in result.items()
        if key not in {
            "verification_sha256",
            "issued_at_utc",
            "duration_seconds",
        }
    })
    if stored != calculated:
        errors.append("verification self-hash mismatch")

    verification = result.get("verification_result", {})
    gates = verification.get("gates")
    gate_count = verification.get("gate_count")
    passed_count = verification.get("passed_gate_count")
    failed_count = verification.get("failed_gate_count")
    failed_ids = verification.get("failed_gate_ids")

    if result.get("status") != "PASS":
        errors.append("verification status is not PASS")
    if result.get("decision") != (
        "final_immutable_manifest_integrity_verified"
    ):
        errors.append("verification decision mismatch")
    if result.get("final_manifest_independently_verified") is not True:
        errors.append("final manifest independently verified flag is not true")
    if result.get("release_candidate_closed") is not True:
        errors.append("release candidate closed flag is not true")
    if failed_count != 0:
        errors.append("failed gate count must be zero")
    if failed_ids != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list):
        errors.append("gates must be a list")
    else:
        if gate_count != len(gates):
            errors.append("gate count does not equal gate list length")
        if any(gate.get("status") != "PASS" for gate in gates):
            errors.append("not all verification gates passed")
    if gate_count != passed_count:
        errors.append("gate count and passed gate count differ")

    if result.get("network_allowed") is not False:
        errors.append("network allowed must be false")
    if result.get("broker_connected") is not False:
        errors.append("broker connected must be false")
    if result.get("orders_submitted") != 0:
        errors.append("orders submitted must be zero")
    if result.get("approved_for_live") is not False:
        errors.append("approved for live must be false")
    if result.get("live_trading_authorized") is not False:
        errors.append("live trading authorized must be false")
    if result.get("next_phase") != EXPECTED_NEXT:
        errors.append("next phase mismatch")
    if not text_path.is_file():
        errors.append("text output missing")

    expected_summary = {
        "status": result.get("status"),
        "decision": result.get("decision"),
        "framework_commit_sha": result.get("repository", {}).get(
            "framework_commit_sha"
        ),
        "verification_sha256": stored,
        "final_manifest_sha256": result.get("source", {}).get(
            "final_manifest_sha256"
        ),
        "immutable_anchor_chain_sha256": result.get("source", {}).get(
            "immutable_anchor_chain_sha256"
        ),
        "artifact_set_sha256": result.get("source", {}).get(
            "artifact_set_sha256"
        ),
        "gate_count": gate_count,
        "passed_gate_count": passed_count,
        "failed_gate_count": failed_count,
        "failed_gate_ids": failed_ids,
        "final_manifest_independently_verified": result.get(
            "final_manifest_independently_verified"
        ),
        "release_candidate_closed": result.get("release_candidate_closed"),
        "network_allowed": result.get("network_allowed"),
        "orders_submitted": result.get("orders_submitted"),
        "approved_for_live": result.get("approved_for_live"),
        "live_trading_authorized": result.get("live_trading_authorized"),
        "next_phase": result.get("next_phase"),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            errors.append(f"summary {key} mismatch")

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "verification_sha256": stored,
        "artifact_set_sha256": result.get("source", {}).get(
            "artifact_set_sha256"
        ),
        "final_manifest_sha256": result.get("source", {}).get(
            "final_manifest_sha256"
        ),
        "immutable_anchor_chain_sha256": result.get("source", {}).get(
            "immutable_anchor_chain_sha256"
        ),
        "final_manifest_independently_verified": result.get(
            "final_manifest_independently_verified"
        ),
        "release_candidate_closed": result.get("release_candidate_closed"),
        "network_allowed": result.get("network_allowed"),
        "orders_submitted": result.get("orders_submitted"),
        "approved_for_live": result.get("approved_for_live"),
        "live_trading_authorized": result.get("live_trading_authorized"),
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
