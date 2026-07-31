from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.release_candidate_audit_certificate_v76_8 import (
    CertificateError,
    digest,
    load_json,
)


def verify_certificate(
    certificate: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    stored = certificate.get("audit_certificate_sha256")
    calculated = digest({
        key: value for key, value in certificate.items()
        if key != "audit_certificate_sha256"
    })
    if stored != calculated:
        errors.append("audit certificate hash mismatch")

    if certificate.get("status") != "PASS":
        errors.append("certificate status is not PASS")
    if certificate.get("release_candidate_audit_certified") is not True:
        errors.append("audit certification is not true")
    if certificate.get("network_allowed") is not False:
        errors.append("network_allowed must be false")
    if certificate.get("orders_submitted") != 0:
        errors.append("orders_submitted must be zero")
    if certificate.get("approved_for_live") is not False:
        errors.append("approved_for_live must be false")

    result = certificate.get("audit_result", {})
    if result.get("failed_gate_count") != 0:
        errors.append("failed_gate_count must be zero")
    if result.get("passed_gate_count") != result.get("gate_count"):
        errors.append("not all gates passed")

    if summary.get("audit_certificate_sha256") != stored:
        errors.append("summary certificate hash reference mismatch")
    if summary.get("status") != certificate.get("status"):
        errors.append("summary status mismatch")

    for key, value in certificate.get("anchored_artifacts", {}).items():
        if summary.get(key) != value:
            errors.append(f"summary anchor mismatch: {key}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "verified": not errors,
        "error_count": len(errors),
        "errors": errors,
        "audit_certificate_sha256": stored,
        "release_candidate_audit_certified":
            certificate.get("release_candidate_audit_certified"),
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "next_phase": (
            "V76_9_RELEASE_CANDIDATE_AUDIT_CERTIFICATE_VERIFICATION"
            if not errors
            else "REPAIR_V76_8_AUDIT_CERTIFICATE"
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    try:
        certificate = load_json(
            output_dir / "release_candidate_audit_certificate_v76_8.json"
        )
        summary = load_json(
            output_dir
            / "release_candidate_audit_certificate_summary_v76_8.json"
        )
        result = verify_certificate(certificate, summary)
    except (CertificateError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
