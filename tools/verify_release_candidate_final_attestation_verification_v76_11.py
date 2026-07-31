from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def verify_output(output_dir: Path) -> dict[str, Any]:
    path = (
        output_dir
        / "release_candidate_final_attestation_verification_v76_11.json"
    )
    result = load_json(path)
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
    if result.get("final_attestation_independently_verified") is not True:
        errors.append("independent verification flag is not true")

    vr = result.get("verification_result", {})
    if vr.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if vr.get("passed_gate_count") != vr.get("gate_count"):
        errors.append("not all verification gates passed")
    if result.get("network_allowed") is not False:
        errors.append("network_allowed must be false")
    if result.get("orders_submitted") != 0:
        errors.append("orders_submitted must be zero")
    if result.get("approved_for_live") is not False:
        errors.append("approved_for_live must be false")
    if result.get("live_trading_authorized") is not False:
        errors.append("live_trading_authorized must be false")

    return {
        "status": "PASS" if not errors else "FAIL",
        "verified": not errors,
        "error_count": len(errors),
        "errors": errors,
        "verification_sha256": stored,
        "final_attestation_independently_verified":
            result.get("final_attestation_independently_verified"),
        "network_allowed": result.get("network_allowed"),
        "orders_submitted": result.get("orders_submitted"),
        "approved_for_live": result.get("approved_for_live"),
        "live_trading_authorized":
            result.get("live_trading_authorized"),
        "next_phase": (
            result.get("next_phase")
            if not errors
            else "REPAIR_V76_11_FINAL_ATTESTATION_VERIFICATION"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_output(Path(args.output_dir))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "status": "ERROR",
            "verified": False,
            "error_count": 1,
            "errors": [str(exc)],
            "approved_for_live": False,
            "live_trading_authorized": False,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
