from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_candidate_closure_verification_v76_13 import (
    digest,
    load_json,
)

EXPECTED_NEXT = "V76_14_FINAL_IMMUTABLE_MANIFEST"


def verify_output(output_dir: Path) -> dict[str, Any]:
    verification_path = output_dir / (
        "release_candidate_closure_verification_v76_13.json"
    )
    summary_path = output_dir / (
        "release_candidate_closure_verification_summary_v76_13.json"
    )
    text_path = output_dir / (
        "release_candidate_closure_verification_v76_13.txt"
    )

    errors: list[str] = []
    verification = load_json(verification_path)
    summary = load_json(summary_path)

    stored = verification.get("verification_sha256")
    calculated = digest(
        {
            key: value
            for key, value in verification.items()
            if key != "verification_sha256"
        }
    )
    if stored != calculated:
        errors.append("verification self-hash mismatch")
    if verification.get("status") != "PASS":
        errors.append("verification status is not PASS")
    if verification.get(
        "closure_certificate_independently_verified"
    ) is not True:
        errors.append("closure certificate independently verified flag is not true")
    if verification.get("release_candidate_closed") is not True:
        errors.append("release candidate closed flag is not true")

    result = verification.get("verification_result", {})
    gates = result.get("gates")
    if result.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if result.get("failed_gate_ids") != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list) or not gates:
        errors.append("verification gates missing")
    elif not all(
        isinstance(gate, dict) and gate.get("status") == "PASS"
        for gate in gates
    ):
        errors.append("not all verification gates passed")
    if result.get("gate_count") != result.get("passed_gate_count"):
        errors.append("gate count and passed gate count differ")

    if summary.get("verification_sha256") != stored:
        errors.append("summary verification hash mismatch")
    if summary.get("status") != verification.get("status"):
        errors.append("summary status mismatch")
    if summary.get(
        "closure_certificate_independently_verified"
    ) is not True:
        errors.append("summary independently verified flag is not true")
    if summary.get("release_candidate_closed") is not True:
        errors.append("summary release candidate closed flag is not true")
    if summary.get("failed_gate_count") != 0:
        errors.append("summary failed gate count must be zero")
    if summary.get("next_phase") != EXPECTED_NEXT:
        errors.append("summary next phase mismatch")
    if not text_path.is_file():
        errors.append("text verification missing")

    for key, expected in (
        ("network_allowed", False),
        ("orders_submitted", 0),
        ("approved_for_live", False),
        ("live_trading_authorized", False),
    ):
        if verification.get(key) != expected:
            errors.append(f"{key} safety value invalid")
        if summary.get(key) != expected:
            errors.append(f"summary {key} safety value invalid")

    verified = not errors
    return {
        "approved_for_live": False,
        "closure_certificate_independently_verified":
            verification.get(
                "closure_certificate_independently_verified"
            ) is True and verified,
        "error_count": len(errors),
        "errors": errors,
        "live_trading_authorized": False,
        "network_allowed": False,
        "next_phase": (
            EXPECTED_NEXT
            if verified
            else "REPAIR_V76_13_RELEASE_CANDIDATE_CLOSURE_VERIFICATION"
        ),
        "orders_submitted": 0,
        "release_candidate_closed":
            verification.get("release_candidate_closed") is True and verified,
        "status": "PASS" if verified else "FAIL",
        "verification_sha256": stored,
        "verified": verified,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = verify_output(Path(args.output_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
