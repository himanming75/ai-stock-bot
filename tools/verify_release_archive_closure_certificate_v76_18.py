from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_archive_closure_certificate_v76_18 import (
    digest, load_json, summary_from
)

EXPECTED_NEXT = "V76_19_RELEASE_ARCHIVE_CLOSURE_VERIFICATION"


def verify_output(output_dir: Path) -> dict[str, Any]:
    result_path = output_dir / "release_archive_closure_certificate_v76_18.json"
    summary_path = (
        output_dir / "release_archive_closure_certificate_summary_v76_18.json"
    )
    text_path = output_dir / "release_archive_closure_certificate_v76_18.txt"
    result = load_json(result_path)
    summary = load_json(summary_path)
    errors: list[str] = []

    stored = result.get("closure_certificate_sha256")
    calculated = digest({
        key: value for key, value in result.items()
        if key not in {"closure_certificate_sha256",
                       "issued_at_utc", "duration_seconds"}
    })
    if stored != calculated:
        errors.append("closure certificate self-hash mismatch")

    chain = result.get("closure_chain", {})
    if result.get("closure_chain_sha256") != digest(chain):
        errors.append("closure chain hash mismatch")
    if summary != summary_from(result):
        errors.append("summary mismatch")
    if not text_path.is_file():
        errors.append("text output missing")

    cert = result.get("certificate_result", {})
    gates = cert.get("gates")
    if result.get("status") != "PASS":
        errors.append("status is not PASS")
    if result.get("decision") != "release_archive_closure_certified":
        errors.append("decision mismatch")
    if result.get("release_archive_closure_certified") is not True:
        errors.append("closure certified flag mismatch")
    if result.get("release_archive_independently_verified") is not True:
        errors.append("independent verification flag mismatch")
    if result.get("release_archive_sealed") is not True:
        errors.append("archive sealed flag mismatch")
    if result.get("release_candidate_closed") is not True:
        errors.append("release candidate closed flag mismatch")
    if cert.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if cert.get("failed_gate_ids") != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list):
        errors.append("gates must be a list")
    else:
        if cert.get("gate_count") != len(gates):
            errors.append("gate count mismatch")
        if cert.get("passed_gate_count") != len(gates):
            errors.append("passed gate count mismatch")
        if any(gate.get("status") != "PASS" for gate in gates):
            errors.append("not all gates passed")

    for key, expected in (
        ("network_allowed", False),
        ("broker_connected", False),
        ("orders_submitted", 0),
        ("approved_for_live", False),
        ("live_trading_authorized", False),
        ("next_phase", EXPECTED_NEXT),
    ):
        if result.get(key) != expected:
            errors.append(f"{key} mismatch")

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "closure_certificate_sha256": stored,
        "closure_chain_sha256": result.get("closure_chain_sha256"),
        **chain,
        "release_archive_closure_certified":
            result.get("release_archive_closure_certified"),
        "release_archive_independently_verified":
            result.get("release_archive_independently_verified"),
        "release_archive_sealed": result.get("release_archive_sealed"),
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
