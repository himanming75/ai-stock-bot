from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VERSION = "76.17"
SCHEMA = "v76.17.release_archive_seal_verification.1"
NEXT_PHASE = "V76_18_RELEASE_ARCHIVE_CLOSURE_CERTIFICATE"
MANIFEST_MEMBER = "seal/release_archive_manifest_v76_16.json"


class ArchiveSealVerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArchiveSealVerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ArchiveSealVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ArchiveSealVerificationError(f"JSON root must be object: {path}")
    return value


def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise ArchiveSealVerificationError(
            f"{name} must be {length} hexadecimal characters"
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise ArchiveSealVerificationError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "RELEASE_ARCHIVE_SEAL_VERIFICATION":
        raise ArchiveSealVerificationError("verification_scope invalid")
    for key in (
        "offline_only",
        "read_only_verification",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_v76_16_outputs",
        "require_archive_exact_member_set",
        "require_archive_member_hashes",
        "require_embedded_manifest_self_hash",
        "require_source_anchor_match",
        "require_zero_trading_side_effects",
        "deterministic_verification_required",
    ):
        if config.get(key) is not True:
            raise ArchiveSealVerificationError(f"{key} must be true")
    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise ArchiveSealVerificationError(f"{key} must be false")

    validate_hex(config.get("expected_framework_commit_sha"), 40,
                 "expected_framework_commit_sha")
    for key in (
        "expected_v76_16_seal_certificate_sha256",
        "expected_v76_16_archive_sha256",
        "expected_v76_16_archive_manifest_sha256",
        "expected_v76_16_evidence_set_sha256",
        "expected_v76_14_final_manifest_sha256",
        "expected_v76_14_anchor_chain_sha256",
        "expected_v76_15_verification_sha256",
        "expected_v76_15_artifact_set_sha256",
    ):
        validate_hex(config.get(key), 64, key)
    if config.get("expected_archive_member_count") != 7:
        raise ArchiveSealVerificationError("expected_archive_member_count must be 7")
    if config.get("expected_evidence_file_count") != 6:
        raise ArchiveSealVerificationError("expected_evidence_file_count must be 6")


def run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False
    )
    if completed.returncode != 0:
        raise ArchiveSealVerificationError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
    }


def add_gate(gates: list[dict[str, Any]], gate_id: str,
             passed: bool, **details: Any) -> None:
    gate = {"gate_id": gate_id, "status": "PASS" if passed else "FAIL"}
    gate.update(details)
    gates.append(gate)


def verify_release_archive(
    root: Path,
    config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    root = root.resolve()
    output_dir = output_dir.resolve()
    validate_config(config)
    started = time.time()
    gates: list[dict[str, Any]] = []
    git = git_state(root)

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
             git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT",
             git["head_sha"] == config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
             git["tracked_status_short"] == [])

    v16_dir = root / "release/v76_16/output"
    result_path = v16_dir / "release_archive_seal_v76_16.json"
    summary_path = v16_dir / "release_archive_seal_summary_v76_16.json"
    text_path = v16_dir / "release_archive_seal_v76_16.txt"
    archive_path = v16_dir / "ai_stock_bot_release_evidence_v76_16.zip"

    for gate_id, path in (
        ("V76_16_RESULT_EXISTS", result_path),
        ("V76_16_SUMMARY_EXISTS", summary_path),
        ("V76_16_TEXT_EXISTS", text_path),
        ("V76_16_ARCHIVE_EXISTS", archive_path),
    ):
        add_gate(gates, gate_id, path.is_file(), path=str(path.relative_to(root)))

    seal_result = load_json(result_path)
    seal_summary = load_json(summary_path)

    stored_certificate = seal_result.get("seal_certificate_sha256")
    calculated_certificate = digest({
        key: value for key, value in seal_result.items()
        if key not in {"seal_certificate_sha256", "issued_at_utc", "duration_seconds"}
    })
    add_gate(gates, "V76_16_CERTIFICATE_SELF_HASH",
             stored_certificate == calculated_certificate,
             actual=calculated_certificate, stored=stored_certificate)
    add_gate(gates, "V76_16_CERTIFICATE_ANCHORED",
             stored_certificate ==
             config["expected_v76_16_seal_certificate_sha256"])
    add_gate(gates, "V76_16_STATUS_PASS", seal_result.get("status") == "PASS")
    add_gate(gates, "V76_16_DECISION_SEALED",
             seal_result.get("decision") == "release_archive_sealed")
    add_gate(gates, "V76_16_RELEASE_ARCHIVE_SEALED",
             seal_result.get("release_archive_sealed") is True)
    add_gate(gates, "V76_16_RELEASE_CANDIDATE_CLOSED",
             seal_result.get("release_candidate_closed") is True)

    seal_gates = seal_result.get("seal_result", {})
    gate_list = seal_gates.get("gates", [])
    add_gate(gates, "V76_16_ZERO_FAILED_GATES",
             seal_gates.get("failed_gate_count") == 0)
    add_gate(gates, "V76_16_FAILED_GATE_IDS_EMPTY",
             seal_gates.get("failed_gate_ids") == [])
    add_gate(gates, "V76_16_ALL_GATES_PASS",
             isinstance(gate_list, list) and
             all(item.get("status") == "PASS" for item in gate_list))
    add_gate(gates, "V76_16_GATE_COUNTS_CONSISTENT",
             isinstance(gate_list, list) and
             seal_gates.get("gate_count") == len(gate_list) and
             seal_gates.get("passed_gate_count") == len(gate_list))

    archive_meta = seal_result.get("archive", {})
    actual_archive_sha = file_sha256(archive_path)
    add_gate(gates, "ARCHIVE_SHA_MATCHES_RESULT",
             actual_archive_sha == archive_meta.get("sha256"))
    add_gate(gates, "ARCHIVE_SHA_ANCHORED",
             actual_archive_sha == config["expected_v76_16_archive_sha256"])
    add_gate(gates, "ARCHIVE_SIZE_MATCHES_RESULT",
             archive_path.stat().st_size == archive_meta.get("size_bytes"))
    add_gate(gates, "ARCHIVE_MEMBER_COUNT_ANCHORED",
             archive_meta.get("member_count") ==
             config["expected_archive_member_count"])
    add_gate(gates, "EVIDENCE_FILE_COUNT_ANCHORED",
             archive_meta.get("evidence_file_count") ==
             config["expected_evidence_file_count"])
    add_gate(gates, "ARCHIVE_MANIFEST_HASH_ANCHORED",
             archive_meta.get("archive_manifest_sha256") ==
             config["expected_v76_16_archive_manifest_sha256"])
    add_gate(gates, "EVIDENCE_SET_HASH_ANCHORED",
             archive_meta.get("evidence_set_sha256") ==
             config["expected_v76_16_evidence_set_sha256"])

    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        add_gate(gates, "ARCHIVE_TESTZIP_CLEAN", archive.testzip() is None)
        add_gate(gates, "ARCHIVE_NO_DUPLICATE_MEMBERS",
                 len(names) == len(set(names)))
        add_gate(gates, "ARCHIVE_MEMBER_COUNT_EXACT",
                 len(names) == config["expected_archive_member_count"])
        add_gate(gates, "EMBEDDED_MANIFEST_PRESENT",
                 MANIFEST_MEMBER in names)

        embedded = json.loads(archive.read(MANIFEST_MEMBER).decode("utf-8"))
        embedded_stored = embedded.get("archive_manifest_sha256")
        embedded_calculated = digest({
            key: value for key, value in embedded.items()
            if key != "archive_manifest_sha256"
        })
        add_gate(gates, "EMBEDDED_MANIFEST_SELF_HASH",
                 embedded_stored == embedded_calculated)
        add_gate(gates, "EMBEDDED_MANIFEST_HASH_MATCHES_RESULT",
                 embedded_stored == archive_meta.get("archive_manifest_sha256"))
        add_gate(gates, "EMBEDDED_MANIFEST_HASH_ANCHORED",
                 embedded_stored ==
                 config["expected_v76_16_archive_manifest_sha256"])

        records = embedded.get("evidence_files", [])
        expected_names = sorted(
            [str(record.get("archive_path")) for record in records] +
            [MANIFEST_MEMBER]
        )
        add_gate(gates, "ARCHIVE_EXACT_MEMBER_SET",
                 sorted(names) == expected_names,
                 actual=sorted(names), expected=expected_names)
        add_gate(gates, "EMBEDDED_EVIDENCE_COUNT",
                 embedded.get("evidence_file_count") ==
                 config["expected_evidence_file_count"])
        add_gate(gates, "EVIDENCE_RECORD_COUNT",
                 isinstance(records, list) and
                 len(records) == config["expected_evidence_file_count"])

        member_hashes_ok = True
        member_sizes_ok = True
        for record in records:
            member = record.get("archive_path")
            if member not in names:
                member_hashes_ok = False
                member_sizes_ok = False
                continue
            data = archive.read(member)
            if hashlib.sha256(data).hexdigest() != record.get("sha256"):
                member_hashes_ok = False
            if len(data) != record.get("size_bytes"):
                member_sizes_ok = False
        add_gate(gates, "ALL_EVIDENCE_MEMBER_HASHES_MATCH", member_hashes_ok)
        add_gate(gates, "ALL_EVIDENCE_MEMBER_SIZES_MATCH", member_sizes_ok)

        calculated_evidence_set = digest(records)
        add_gate(gates, "EVIDENCE_SET_SELF_HASH",
                 calculated_evidence_set == embedded.get("evidence_set_sha256"))
        add_gate(gates, "EVIDENCE_SET_MATCHES_RESULT",
                 calculated_evidence_set == archive_meta.get("evidence_set_sha256"))
        add_gate(gates, "EVIDENCE_SET_ANCHORED",
                 calculated_evidence_set ==
                 config["expected_v76_16_evidence_set_sha256"])

        anchors = embedded.get("source_anchors", {})
        expected_anchors = {
            "v76_14_final_manifest_sha256":
                config["expected_v76_14_final_manifest_sha256"],
            "v76_14_anchor_chain_sha256":
                config["expected_v76_14_anchor_chain_sha256"],
            "v76_15_verification_sha256":
                config["expected_v76_15_verification_sha256"],
            "v76_15_artifact_set_sha256":
                config["expected_v76_15_artifact_set_sha256"],
        }
        add_gate(gates, "EMBEDDED_SOURCE_ANCHORS_MATCH",
                 anchors == expected_anchors)
        add_gate(gates, "RESULT_SOURCE_ANCHORS_MATCH",
                 seal_result.get("source_anchors") == expected_anchors)

        safety = embedded.get("safety", {})
        safety_ok = (
            safety.get("network_allowed") is False and
            safety.get("broker_connected") is False and
            safety.get("orders_submitted") == 0 and
            safety.get("approved_for_live") is False and
            safety.get("live_trading_authorized") is False
        )
        add_gate(gates, "EMBEDDED_SAFETY_STATE", safety_ok)

    summary_checks = {
        "status": seal_result.get("status"),
        "decision": seal_result.get("decision"),
        "seal_certificate_sha256": stored_certificate,
        "archive_sha256": archive_meta.get("sha256"),
        "archive_manifest_sha256": archive_meta.get("archive_manifest_sha256"),
        "evidence_set_sha256": archive_meta.get("evidence_set_sha256"),
        "release_archive_sealed": True,
        "release_candidate_closed": True,
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
    }
    add_gate(gates, "V76_16_SUMMARY_CONSISTENT",
             all(seal_summary.get(k) == v for k, v in summary_checks.items()))

    add_gate(gates, "RESULT_NETWORK_DISABLED",
             seal_result.get("network_allowed") is False)
    add_gate(gates, "RESULT_BROKER_NOT_CONNECTED",
             seal_result.get("broker_connected") is False)
    add_gate(gates, "RESULT_ZERO_ORDERS",
             seal_result.get("orders_submitted") == 0)
    add_gate(gates, "RESULT_NOT_APPROVED_FOR_LIVE",
             seal_result.get("approved_for_live") is False)
    add_gate(gates, "RESULT_LIVE_TRADING_NOT_AUTHORIZED",
             seal_result.get("live_trading_authorized") is False)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "verification_type": "INDEPENDENT_RELEASE_ARCHIVE_SEAL_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 6),
        "status": status,
        "decision": "release_archive_seal_independently_verified"
                    if status == "PASS"
                    else "release_archive_seal_verification_failed",
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "verified_anchors": {
            "v76_16_seal_certificate_sha256": stored_certificate,
            "v76_16_archive_sha256": actual_archive_sha,
            "v76_16_archive_manifest_sha256":
                archive_meta.get("archive_manifest_sha256"),
            "v76_16_evidence_set_sha256":
                archive_meta.get("evidence_set_sha256"),
            "v76_14_final_manifest_sha256":
                config["expected_v76_14_final_manifest_sha256"],
            "v76_14_anchor_chain_sha256":
                config["expected_v76_14_anchor_chain_sha256"],
            "v76_15_verification_sha256":
                config["expected_v76_15_verification_sha256"],
            "v76_15_artifact_set_sha256":
                config["expected_v76_15_artifact_set_sha256"],
        },
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_archive_independently_verified": status == "PASS",
        "release_archive_sealed": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS"
                      else "REPAIR_V76_17_ARCHIVE_SEAL_VERIFICATION",
    }
    immutable = {
        key: value for key, value in result.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    result["verification_sha256"] = digest(immutable)
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    vr = result["verification_result"]
    anchors = result["verified_anchors"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "verification_sha256": result["verification_sha256"],
        **anchors,
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "release_archive_independently_verified":
            result["release_archive_independently_verified"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def render_text(result: dict[str, Any]) -> str:
    return "\n".join(
        ["V76.17 RELEASE ARCHIVE SEAL VERIFICATION"] +
        [f"{key}: {value}" for key, value in summary_from(result).items()]
    ) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "release_archive_seal_verification_v76_17.json"
    summary_path = output_dir / "release_archive_seal_verification_summary_v76_17.json"
    text_path = output_dir / "release_archive_seal_verification_v76_17.txt"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(summary_from(result), indent=2, sort_keys=True,
                   ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    text_path.write_text(render_text(result), encoding="utf-8")
    return [result_path, summary_path, text_path]


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = verify_release_archive(
        Path(args.repository_root),
        load_json(Path(args.config)),
        Path(args.output_dir),
    )
    outputs = write_outputs(result, Path(args.output_dir))
    vr = result["verification_result"]
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "release_archive_independently_verified":
            result["release_archive_independently_verified"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "verification_sha256": result["verification_sha256"],
        **result["verified_anchors"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
        "outputs": [str(path) for path in outputs],
    }, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
