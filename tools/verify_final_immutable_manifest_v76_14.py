from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.final_immutable_manifest_v76_14 import digest, load_json

EXPECTED_NEXT = "V76_15_FINAL_INTEGRITY_VERIFICATION"


def verify_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "final_immutable_manifest_v76_14.json"
    summary_path = output_dir / "final_immutable_manifest_summary_v76_14.json"
    text_path = output_dir / "final_immutable_manifest_v76_14.txt"

    errors: list[str] = []
    manifest = load_json(manifest_path)
    summary = load_json(summary_path)

    stored_manifest = manifest.get("final_manifest_sha256")
    calculated_manifest = digest(
        {
            key: value
            for key, value in manifest.items()
            if key not in {
                "final_manifest_sha256",
                "issued_at_utc",
                "duration_seconds",
            }
        }
    )
    if stored_manifest != calculated_manifest:
        errors.append("final manifest self-hash mismatch")

    anchors = manifest.get("immutable_anchor_chain")
    stored_anchor_hash = manifest.get("immutable_anchor_chain_sha256")
    calculated_anchor_hash = digest(anchors) if isinstance(anchors, dict) else None
    if stored_anchor_hash != calculated_anchor_hash:
        errors.append("immutable anchor chain hash mismatch")

    if manifest.get("status") != "PASS":
        errors.append("manifest status is not PASS")
    if manifest.get("final_manifest_issued") is not True:
        errors.append("final manifest issued flag is not true")
    if manifest.get("release_candidate_closed") is not True:
        errors.append("release candidate closed flag is not true")

    result = manifest.get("manifest_result", {})
    gates = result.get("gates")
    if result.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if result.get("failed_gate_ids") != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list) or not gates:
        errors.append("manifest gates missing")
    elif not all(
        isinstance(gate, dict) and gate.get("status") == "PASS"
        for gate in gates
    ):
        errors.append("not all manifest gates passed")
    if result.get("gate_count") != result.get("passed_gate_count"):
        errors.append("gate count and passed gate count differ")

    if summary.get("final_manifest_sha256") != stored_manifest:
        errors.append("summary final manifest hash mismatch")
    if summary.get("immutable_anchor_chain_sha256") != stored_anchor_hash:
        errors.append("summary anchor chain hash mismatch")
    if summary.get("status") != manifest.get("status"):
        errors.append("summary status mismatch")
    if summary.get("final_manifest_issued") is not True:
        errors.append("summary final manifest issued flag is not true")
    if summary.get("release_candidate_closed") is not True:
        errors.append("summary release candidate closed flag is not true")
    if summary.get("failed_gate_count") != 0:
        errors.append("summary failed gate count must be zero")
    if summary.get("next_phase") != EXPECTED_NEXT:
        errors.append("summary next phase mismatch")
    if not text_path.is_file():
        errors.append("text manifest missing")

    for key, expected in (
        ("network_allowed", False),
        ("orders_submitted", 0),
        ("approved_for_live", False),
        ("live_trading_authorized", False),
    ):
        if manifest.get(key) != expected:
            errors.append(f"{key} safety value invalid")
        if summary.get(key) != expected:
            errors.append(f"summary {key} safety value invalid")

    verified = not errors
    return {
        "approved_for_live": False,
        "error_count": len(errors),
        "errors": errors,
        "final_manifest_issued":
            manifest.get("final_manifest_issued") is True and verified,
        "final_manifest_sha256": stored_manifest,
        "immutable_anchor_chain_sha256": stored_anchor_hash,
        "live_trading_authorized": False,
        "network_allowed": False,
        "next_phase": (
            EXPECTED_NEXT
            if verified
            else "REPAIR_V76_14_FINAL_IMMUTABLE_MANIFEST"
        ),
        "orders_submitted": 0,
        "release_candidate_closed":
            manifest.get("release_candidate_closed") is True and verified,
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
