from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_candidate_closure_certificate_v76_12 import (
    canonical,
    digest,
    load_json,
)

EXPECTED_NEXT = "V76_13_RELEASE_CANDIDATE_CLOSURE_VERIFICATION"


def verify_output(output_dir: Path) -> dict[str, Any]:
    cert_path = output_dir / "release_candidate_closure_certificate_v76_12.json"
    summary_path = output_dir / (
        "release_candidate_closure_certificate_summary_v76_12.json"
    )
    text_path = output_dir / "release_candidate_closure_certificate_v76_12.txt"

    errors: list[str] = []
    cert = load_json(cert_path)
    summary = load_json(summary_path)

    stored = cert.get("closure_certificate_sha256")
    calculated = digest({
        k: v for k, v in cert.items()
        if k != "closure_certificate_sha256"
    })
    if stored != calculated:
        errors.append("closure certificate self-hash mismatch")
    if cert.get("status") != "PASS":
        errors.append("certificate status is not PASS")
    if cert.get("release_candidate_closed") is not True:
        errors.append("release candidate closed flag is not true")

    result = cert.get("closure_result", {})
    gates = result.get("gates")
    if result.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if result.get("failed_gate_ids") != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list) or not gates:
        errors.append("closure gates missing")
    elif not all(isinstance(g, dict) and g.get("status") == "PASS"
                 for g in gates):
        errors.append("not all closure gates passed")
    if result.get("gate_count") != result.get("passed_gate_count"):
        errors.append("gate count and passed gate count differ")

    if summary.get("closure_certificate_sha256") != stored:
        errors.append("summary certificate hash mismatch")
    if summary.get("status") != cert.get("status"):
        errors.append("summary status mismatch")
    if summary.get("release_candidate_closed") is not True:
        errors.append("summary closed flag is not true")
    if summary.get("failed_gate_count") != 0:
        errors.append("summary failed gate count must be zero")
    if summary.get("next_phase") != EXPECTED_NEXT:
        errors.append("summary next phase mismatch")
    if not text_path.is_file():
        errors.append("text certificate missing")

    for key, expected in (
        ("network_allowed", False),
        ("orders_submitted", 0),
        ("approved_for_live", False),
        ("live_trading_authorized", False),
    ):
        if cert.get(key) != expected:
            errors.append(f"{key} safety value invalid")
        if summary.get(key) != expected:
            errors.append(f"summary {key} safety value invalid")

    verified = not errors
    return {
        "approved_for_live": False,
        "closure_certificate_sha256": stored,
        "error_count": len(errors),
        "errors": errors,
        "live_trading_authorized": False,
        "network_allowed": False,
        "next_phase": (
            EXPECTED_NEXT if verified
            else "REPAIR_V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE"
        ),
        "orders_submitted": 0,
        "release_candidate_closed":
            cert.get("release_candidate_closed") is True and verified,
        "status": "PASS" if verified else "FAIL",
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
