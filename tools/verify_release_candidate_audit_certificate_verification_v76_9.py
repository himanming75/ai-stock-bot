from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_candidate_audit_certificate_verification_v76_9 import (
    VerificationError,
    digest,
    load_json,
)


def independently_verify(
    result: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    stored = result.get("verification_sha256")
    calculated = digest({
        key: value for key, value in result.items()
        if key != "verification_sha256"
    })
    if stored != calculated:
        errors.append("verification self-hash mismatch")
    if result.get("status") != "PASS":
        errors.append("verification status is not PASS")
    if result.get("audit_certificate_independently_verified") is not True:
        errors.append("independent verification flag is not true")
    verification = result.get("verification_result", {})
    if verification.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if verification.get("passed_gate_count") != verification.get("gate_count"):
        errors.append("not all verification gates passed")
    if result.get("network_allowed") is not False:
        errors.append("network_allowed must be false")
    if result.get("orders_submitted") != 0:
        errors.append("orders_submitted must be zero")
    if result.get("approved_for_live") is not False:
        errors.append("approved_for_live must be false")
    if summary.get("verification_sha256") != stored:
        errors.append("summary verification hash mismatch")
    if summary.get("status") != result.get("status"):
        errors.append("summary status mismatch")
    if (
        summary.get("audit_certificate_sha256")
        != result.get("source_certificate", {}).get("audit_certificate_sha256")
    ):
        errors.append("summary source certificate hash mismatch")

    return {
        "status": "PASS" if not errors else "FAIL",
        "verified": not errors,
        "error_count": len(errors),
        "errors": errors,
        "verification_sha256": stored,
        "audit_certificate_independently_verified":
            result.get("audit_certificate_independently_verified"),
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "next_phase": (
            "V76_10_RELEASE_CANDIDATE_FINAL_ATTESTATION"
            if not errors
            else "REPAIR_V76_9_VERIFICATION"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    try:
        result = load_json(
            output_dir / "release_candidate_audit_certificate_verification_v76_9.json"
        )
        summary = load_json(
            output_dir / "release_candidate_audit_certificate_verification_summary_v76_9.json"
        )
        verdict = independently_verify(result, summary)
    except (VerificationError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
