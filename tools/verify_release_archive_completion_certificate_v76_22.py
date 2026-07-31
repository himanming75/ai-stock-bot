from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.release_archive_completion_certificate_v76_22 import (
    digest,
    load_json,
    summary_from,
)

EXPECTED_NEXT = "V76_23_RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION"


def verify_output(output_dir: Path) -> dict[str, Any]:
    result = load_json(
        output_dir / "release_archive_completion_certificate_v76_22.json"
    )
    summary = load_json(
        output_dir / "release_archive_completion_certificate_summary_v76_22.json"
    )
    text_path = output_dir / "release_archive_completion_certificate_v76_22.txt"
    errors: list[str] = []

    stored = result.get("certificate_sha256")
    calculated = digest({
        key: value for key, value in result.items()
        if key not in {"certificate_sha256", "issued_at_utc", "duration_seconds"}
    })
    if stored != calculated:
        errors.append("certificate self-hash mismatch")

    chain = result.get("completion_chain")
    if not isinstance(chain, dict):
        errors.append("completion chain must be an object")
    elif result.get("completion_chain_sha256") != digest(chain):
        errors.append("completion chain hash mismatch")

    if summary != summary_from(result):
        errors.append("summary mismatch")
    if not text_path.is_file():
        errors.append("text output missing")

    certificate = result.get("certificate_result", {})
    gates = certificate.get("gates")
    if result.get("status") != "PASS":
        errors.append("status is not PASS")
    if result.get("decision") != "release_archive_completion_certified":
        errors.append("decision mismatch")
    if result.get("record_type") != "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE":
        errors.append("record type mismatch")
    if result.get("release_archive_completion_certified") is not True:
        errors.append("completion certificate flag mismatch")
    if certificate.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if certificate.get("failed_gate_ids") != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list):
        errors.append("gates must be a list")
    else:
        if certificate.get("gate_count") != len(gates):
            errors.append("gate count mismatch")
        if certificate.get("passed_gate_count") != len(gates):
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
        "certificate_sha256": stored,
        "completion_chain_sha256": result.get("completion_chain_sha256"),
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
