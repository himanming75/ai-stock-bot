from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.release_archive_completion_certificate_verification_v76_23 import digest, load_json, summary_from

EXPECTED_NEXT = "V76_24_PROJECT_RELEASE_CLOSURE"

def verify_output(output_dir: Path) -> dict[str, Any]:
    result = load_json(output_dir/"release_archive_completion_certificate_verification_v76_23.json")
    summary = load_json(output_dir/"release_archive_completion_certificate_verification_summary_v76_23.json")
    text_path = output_dir/"release_archive_completion_certificate_verification_v76_23.txt"
    errors: list[str] = []

    stored = result.get("verification_sha256")
    calculated = digest({
        k:v for k,v in result.items()
        if k not in {"verification_sha256","issued_at_utc","duration_seconds"}
    })
    if stored != calculated:
        errors.append("verification self-hash mismatch")

    chain = result.get("verification_chain")
    if not isinstance(chain, dict):
        errors.append("verification chain must be an object")
    elif result.get("verification_chain_sha256") != digest(chain):
        errors.append("verification chain hash mismatch")

    if summary != summary_from(result):
        errors.append("summary mismatch")
    if not text_path.is_file():
        errors.append("text output missing")

    vr = result.get("verification_result", {})
    gates = vr.get("gates")
    checks = [
        (result.get("status") == "PASS", "status is not PASS"),
        (result.get("decision") == "release_archive_completion_certificate_independently_verified", "decision mismatch"),
        (result.get("verification_type") == "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION", "verification type mismatch"),
        (result.get("release_archive_completion_certificate_independently_verified") is True, "verification flag mismatch"),
        (vr.get("failed_gate_count") == 0, "failed gate count must be zero"),
        (vr.get("failed_gate_ids") == [], "failed gate IDs must be empty"),
        (result.get("network_allowed") is False, "network_allowed mismatch"),
        (result.get("broker_connected") is False, "broker_connected mismatch"),
        (result.get("orders_submitted") == 0, "orders_submitted mismatch"),
        (result.get("approved_for_live") is False, "approved_for_live mismatch"),
        (result.get("live_trading_authorized") is False, "live_trading_authorized mismatch"),
        (result.get("next_phase") == EXPECTED_NEXT, "next_phase mismatch"),
    ]
    for ok, msg in checks:
        if not ok:
            errors.append(msg)

    if not isinstance(gates, list):
        errors.append("gates must be a list")
    else:
        if vr.get("gate_count") != len(gates):
            errors.append("gate count mismatch")
        if vr.get("passed_gate_count") != len(gates):
            errors.append("passed gate count mismatch")
        if any(g.get("status") != "PASS" for g in gates):
            errors.append("not all gates passed")

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "verification_sha256": stored,
        "verification_chain_sha256": result.get("verification_chain_sha256"),
        "next_phase": result.get("next_phase"),
    }

def cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    checked = verify_output(Path(a.output_dir))
    print(json.dumps(checked, indent=2))
    return 0 if checked["verified"] else 1

if __name__ == "__main__":
    raise SystemExit(cli())
