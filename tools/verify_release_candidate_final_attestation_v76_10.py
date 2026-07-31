from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_candidate_final_attestation_v76_10 import (
    AttestationError,
    digest,
    load_json,
)


def verify_attestation(
    result: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    stored = result.get("final_attestation_sha256")
    calculated = digest({
        k: v for k, v in result.items() if k != "final_attestation_sha256"
    })
    if stored != calculated:
        errors.append("final attestation self-hash mismatch")
    if result.get("status") != "PASS":
        errors.append("attestation status is not PASS")
    if result.get("release_candidate_finally_attested") is not True:
        errors.append("final attestation flag is not true")
    r = result.get("attestation_result", {})
    if r.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if r.get("passed_gate_count") != r.get("gate_count"):
        errors.append("not all attestation gates passed")
    chain = result.get("attested_chain", {})
    for key in (
        "v76_6_release_candidate_sealed",
        "v76_7_seal_independently_verified",
        "v76_8_audit_certified",
        "v76_9_audit_certificate_independently_verified",
    ):
        if chain.get(key) is not True:
            errors.append(f"attested chain failure: {key}")
    if result.get("network_allowed") is not False:
        errors.append("network_allowed must be false")
    if result.get("orders_submitted") != 0:
        errors.append("orders_submitted must be zero")
    if result.get("approved_for_live") is not False:
        errors.append("approved_for_live must be false")
    if result.get("live_trading_authorized") is not False:
        errors.append("live_trading_authorized must be false")
    if summary.get("final_attestation_sha256") != stored:
        errors.append("summary attestation hash mismatch")
    if summary.get("status") != result.get("status"):
        errors.append("summary status mismatch")
    if summary.get("attested_chain") != chain:
        errors.append("summary attested chain mismatch")
    if summary.get("anchored_hashes") != result.get("anchored_hashes"):
        errors.append("summary anchored hashes mismatch")

    return {
        "status": "PASS" if not errors else "FAIL",
        "verified": not errors,
        "error_count": len(errors),
        "errors": errors,
        "release_candidate_finally_attested":
            result.get("release_candidate_finally_attested"),
        "final_attestation_sha256": stored,
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": (
            "V76_11_FINAL_ATTESTATION_VERIFICATION"
            if not errors
            else "REPAIR_V76_10_FINAL_ATTESTATION"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)

    try:
        result = load_json(
            output_dir / "release_candidate_final_attestation_v76_10.json"
        )
        summary = load_json(
            output_dir / "release_candidate_final_attestation_summary_v76_10.json"
        )
        verdict = verify_attestation(result, summary)
    except (AttestationError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
            "live_trading_authorized": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
