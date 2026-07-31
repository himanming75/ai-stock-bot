from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.release_archive_seal_v76_16 import digest, file_sha256, load_json

EXPECTED_NEXT = "V76_17_RELEASE_ARCHIVE_SEAL_VERIFICATION"


def verify_output(output_dir: Path) -> dict[str, Any]:
    result_path = output_dir / "release_archive_seal_v76_16.json"
    summary_path = output_dir / "release_archive_seal_summary_v76_16.json"
    text_path = output_dir / "release_archive_seal_v76_16.txt"
    result = load_json(result_path)
    summary = load_json(summary_path)
    errors: list[str] = []

    stored_cert = result.get("seal_certificate_sha256")
    calculated_cert = digest({
        key: value for key, value in result.items()
        if key not in {"seal_certificate_sha256", "issued_at_utc", "duration_seconds"}
    })
    if stored_cert != calculated_cert:
        errors.append("seal certificate self-hash mismatch")

    archive_meta = result.get("archive", {})
    archive_path = output_dir / str(archive_meta.get("filename", ""))
    if not archive_path.is_file():
        errors.append("release archive missing")
    else:
        actual_archive_sha = file_sha256(archive_path)
        if actual_archive_sha != archive_meta.get("sha256"):
            errors.append("release archive SHA256 mismatch")
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                bad = archive.testzip()
                if bad is not None:
                    errors.append(f"corrupt archive member: {bad}")
                manifest_name = "seal/release_archive_manifest_v76_16.json"
                if manifest_name not in archive.namelist():
                    errors.append("embedded archive manifest missing")
                else:
                    embedded = json.loads(archive.read(manifest_name).decode("utf-8"))
                    stored = embedded.get("archive_manifest_sha256")
                    calculated = digest({
                        key: value for key, value in embedded.items()
                        if key != "archive_manifest_sha256"
                    })
                    if stored != calculated:
                        errors.append("embedded archive manifest self-hash mismatch")
                    if stored != archive_meta.get("archive_manifest_sha256"):
                        errors.append("embedded archive manifest anchor mismatch")
                    records = embedded.get("evidence_files", [])
                    for record in records:
                        name = record.get("archive_path")
                        if name not in archive.namelist():
                            errors.append(f"archive member missing: {name}")
                            continue
                        actual = hashlib.sha256(archive.read(name)).hexdigest()
                        if actual != record.get("sha256"):
                            errors.append(f"archive member hash mismatch: {name}")
                    if digest(records) != embedded.get("evidence_set_sha256"):
                        errors.append("evidence set hash mismatch")
                    if embedded.get("evidence_set_sha256") != archive_meta.get(
                        "evidence_set_sha256"
                    ):
                        errors.append("evidence set anchor mismatch")
        except (zipfile.BadZipFile, json.JSONDecodeError) as exc:
            errors.append(f"invalid release archive: {exc}")

    seal = result.get("seal_result", {})
    gates = seal.get("gates")
    if result.get("status") != "PASS":
        errors.append("seal status is not PASS")
    if result.get("decision") != "release_archive_sealed":
        errors.append("seal decision mismatch")
    if result.get("release_archive_sealed") is not True:
        errors.append("release archive sealed flag is not true")
    if result.get("release_candidate_closed") is not True:
        errors.append("release candidate closed flag is not true")
    if seal.get("failed_gate_count") != 0:
        errors.append("failed gate count must be zero")
    if seal.get("failed_gate_ids") != []:
        errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list):
        errors.append("gates must be a list")
    else:
        if seal.get("gate_count") != len(gates):
            errors.append("gate count mismatch")
        if any(gate.get("status") != "PASS" for gate in gates):
            errors.append("not all gates passed")
    if seal.get("passed_gate_count") != seal.get("gate_count"):
        errors.append("passed gate count mismatch")

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
    if not text_path.is_file():
        errors.append("text output missing")

    expected_summary = {
        "status": result.get("status"),
        "decision": result.get("decision"),
        "framework_commit_sha": result.get("repository", {}).get("framework_commit_sha"),
        "seal_certificate_sha256": stored_cert,
        "archive_sha256": archive_meta.get("sha256"),
        "archive_manifest_sha256": archive_meta.get("archive_manifest_sha256"),
        "evidence_set_sha256": archive_meta.get("evidence_set_sha256"),
        "archive_size_bytes": archive_meta.get("size_bytes"),
        "archive_member_count": archive_meta.get("member_count"),
        "evidence_file_count": archive_meta.get("evidence_file_count"),
        "gate_count": seal.get("gate_count"),
        "passed_gate_count": seal.get("passed_gate_count"),
        "failed_gate_count": seal.get("failed_gate_count"),
        "failed_gate_ids": seal.get("failed_gate_ids"),
        "release_archive_sealed": result.get("release_archive_sealed"),
        "release_candidate_closed": result.get("release_candidate_closed"),
        "network_allowed": result.get("network_allowed"),
        "orders_submitted": result.get("orders_submitted"),
        "approved_for_live": result.get("approved_for_live"),
        "live_trading_authorized": result.get("live_trading_authorized"),
        "next_phase": result.get("next_phase"),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            errors.append(f"summary {key} mismatch")

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "seal_certificate_sha256": stored_cert,
        "archive_sha256": archive_meta.get("sha256"),
        "archive_manifest_sha256": archive_meta.get("archive_manifest_sha256"),
        "evidence_set_sha256": archive_meta.get("evidence_set_sha256"),
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
