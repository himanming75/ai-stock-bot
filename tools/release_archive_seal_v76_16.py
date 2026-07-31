from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VERSION = "76.16"
SCHEMA = "v76.16.release_archive_seal.1"
NEXT_PHASE = "V76_17_RELEASE_ARCHIVE_SEAL_VERIFICATION"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class ReleaseArchiveSealError(ValueError):
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
        raise ReleaseArchiveSealError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseArchiveSealError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ReleaseArchiveSealError(f"JSON root must be object: {path}")
    return value


def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise ReleaseArchiveSealError(f"{name} must be {length} hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ReleaseArchiveSealError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("seal_scope") != "RELEASE_ARCHIVE_SEAL":
        raise ReleaseArchiveSealError("seal_scope invalid")
    for key in (
        "offline_only",
        "deterministic_archive_required",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_v76_14_outputs",
        "require_v76_15_outputs",
        "require_source_hash_anchors",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise ReleaseArchiveSealError(f"{key} must be true")
    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise ReleaseArchiveSealError(f"{key} must be false")

    validate_hex(config.get("expected_framework_commit_sha"), 40, "expected_framework_commit_sha")
    for key in (
        "expected_v76_15_verification_sha256",
        "expected_v76_15_artifact_set_sha256",
        "expected_v76_14_final_manifest_sha256",
        "expected_v76_14_anchor_chain_sha256",
    ):
        validate_hex(config.get(key), 64, key)

    sources = config.get("source_files")
    if not isinstance(sources, list) or len(sources) != 6:
        raise ReleaseArchiveSealError("source_files must contain exactly 6 paths")
    if len(set(sources)) != len(sources):
        raise ReleaseArchiveSealError("source_files must be unique")
    for source in sources:
        if not isinstance(source, str) or not source:
            raise ReleaseArchiveSealError("source file path invalid")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ReleaseArchiveSealError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ReleaseArchiveSealError(f"path outside repository: {relative_text}") from exc
    return resolved


def run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise ReleaseArchiveSealError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    full = run_git(root, ["status", "--short"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
        "full_status_short": full.splitlines() if full else [],
    }


def add_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool, **details: Any) -> None:
    gate = {"gate_id": gate_id, "status": "PASS" if passed else "FAIL"}
    gate.update(details)
    gates.append(gate)


def deterministic_zip(source_root: Path, member_names: list[str], zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = zip_path.with_suffix(zip_path.suffix + ".tmp")
    if temp_path.exists():
        temp_path.unlink()
    with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(member_names):
            source = source_root / name
            info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
    temp_path.replace(zip_path)


def build_release_archive_seal(
    root: Path,
    config: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    root = root.resolve()
    output_dir = output_dir.resolve()
    validate_config(config)
    started = time.time()
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
             git["head_sha"] == git["origin_main_sha"],
             actual=git["head_sha"], expected=git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT",
             git["head_sha"] == config["expected_framework_commit_sha"],
             actual=git["head_sha"], expected=config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main",
             actual=git["branch"], expected="main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
             git["tracked_status_short"] == [],
             actual=git["tracked_status_short"], expected=[])

    source_paths: list[tuple[str, Path]] = []
    for relative in config["source_files"]:
        source = safe_relative(root, relative)
        member = f"evidence/{relative.replace(chr(92), '/')}"
        source_paths.append((member, source))
        add_gate(gates, f"SOURCE_EXISTS_{len(source_paths):02d}", source.is_file(),
                 source=relative)

    v14_manifest = load_json(safe_relative(
        root, "release/v76_14/output/final_immutable_manifest_v76_14.json"
    ))
    v15_verification = load_json(safe_relative(
        root, "release/v76_15/output/final_integrity_verification_v76_15.json"
    ))

    add_gate(gates, "V76_14_FINAL_MANIFEST_HASH_ANCHORED",
             v14_manifest.get("final_manifest_sha256")
             == config["expected_v76_14_final_manifest_sha256"])
    add_gate(gates, "V76_14_ANCHOR_CHAIN_HASH_ANCHORED",
             v14_manifest.get("immutable_anchor_chain_sha256")
             == config["expected_v76_14_anchor_chain_sha256"])
    add_gate(gates, "V76_15_VERIFICATION_HASH_ANCHORED",
             v15_verification.get("verification_sha256")
             == config["expected_v76_15_verification_sha256"])
    add_gate(gates, "V76_15_ARTIFACT_SET_HASH_ANCHORED",
             v15_verification.get("source", {}).get("artifact_set_sha256")
             == config["expected_v76_15_artifact_set_sha256"])
    add_gate(gates, "V76_15_STATUS_PASS", v15_verification.get("status") == "PASS")
    add_gate(gates, "V76_15_INDEPENDENTLY_VERIFIED",
             v15_verification.get("final_manifest_independently_verified") is True)
    add_gate(gates, "V76_15_RELEASE_CANDIDATE_CLOSED",
             v15_verification.get("release_candidate_closed") is True)

    safety_checks = {
        "NETWORK_DISABLED": v15_verification.get("network_allowed") is False,
        "BROKER_NOT_CONNECTED": v15_verification.get("broker_connected") is False,
        "ZERO_ORDERS_SUBMITTED": v15_verification.get("orders_submitted") == 0,
        "NOT_APPROVED_FOR_LIVE": v15_verification.get("approved_for_live") is False,
        "LIVE_TRADING_NOT_AUTHORIZED":
            v15_verification.get("live_trading_authorized") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    staging = output_dir / "_archive_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    evidence_records = []
    for member, source in sorted(source_paths):
        target = staging / member
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        evidence_records.append({
            "archive_path": member,
            "source_path": str(source.relative_to(root)).replace("\\", "/"),
            "size_bytes": target.stat().st_size,
            "sha256": file_sha256(target),
        })

    evidence_set_sha256 = digest(evidence_records)
    archive_manifest = {
        "schema_version": "v76.16.archive_manifest.1",
        "version": VERSION,
        "framework_commit_sha": config["expected_framework_commit_sha"],
        "source_anchors": {
            "v76_14_final_manifest_sha256":
                config["expected_v76_14_final_manifest_sha256"],
            "v76_14_anchor_chain_sha256":
                config["expected_v76_14_anchor_chain_sha256"],
            "v76_15_verification_sha256":
                config["expected_v76_15_verification_sha256"],
            "v76_15_artifact_set_sha256":
                config["expected_v76_15_artifact_set_sha256"],
        },
        "evidence_file_count": len(evidence_records),
        "evidence_files": evidence_records,
        "evidence_set_sha256": evidence_set_sha256,
        "safety": {
            "network_allowed": False,
            "broker_connected": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "live_trading_authorized": False,
        },
    }
    archive_manifest["archive_manifest_sha256"] = digest(archive_manifest)
    manifest_member = "seal/release_archive_manifest_v76_16.json"
    manifest_path = staging / manifest_member
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(archive_manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    member_names = [record["archive_path"] for record in evidence_records] + [manifest_member]
    archive_path = output_dir / "ai_stock_bot_release_evidence_v76_16.zip"
    deterministic_zip(staging, member_names, archive_path)
    archive_sha256 = file_sha256(archive_path)

    # Rebuild independently and compare bytes/hash for determinism.
    second_path = output_dir / "_determinism_check.zip"
    deterministic_zip(staging, member_names, second_path)
    second_sha256 = file_sha256(second_path)
    add_gate(gates, "ARCHIVE_DETERMINISTIC", archive_sha256 == second_sha256,
             first=archive_sha256, second=second_sha256)
    second_path.unlink(missing_ok=True)

    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        add_gate(gates, "ARCHIVE_MEMBER_SET_MATCH",
                 names == sorted(member_names),
                 actual=names, expected=sorted(member_names))
        add_gate(gates, "ARCHIVE_TESTZIP_CLEAN", archive.testzip() is None)
        for record in evidence_records:
            data = archive.read(record["archive_path"])
            actual = hashlib.sha256(data).hexdigest()
            add_gate(gates, f"ARCHIVE_MEMBER_HASH_{record['archive_path']}",
                     actual == record["sha256"])
        embedded = json.loads(archive.read(manifest_member).decode("utf-8"))
        embedded_stored = embedded.get("archive_manifest_sha256")
        embedded_calc = digest({
            key: value for key, value in embedded.items()
            if key != "archive_manifest_sha256"
        })
        add_gate(gates, "EMBEDDED_MANIFEST_SELF_HASH",
                 embedded_stored == embedded_calc)

    failed = [gate["gate_id"] for gate in gates if gate["status"] != "PASS"]
    passed = len(gates) - len(failed)
    status = "PASS" if not failed else "FAIL"

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "seal_type": "DETERMINISTIC_RELEASE_ARCHIVE_SEAL",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 6),
        "status": status,
        "decision": "release_archive_sealed" if status == "PASS"
                    else "release_archive_seal_failed",
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "source_anchors": archive_manifest["source_anchors"],
        "archive": {
            "filename": archive_path.name,
            "sha256": archive_sha256,
            "size_bytes": archive_path.stat().st_size,
            "member_count": len(member_names),
            "evidence_file_count": len(evidence_records),
            "evidence_set_sha256": evidence_set_sha256,
            "archive_manifest_sha256": archive_manifest["archive_manifest_sha256"],
        },
        "seal_result": {
            "gate_count": len(gates),
            "passed_gate_count": passed,
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_archive_sealed": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS"
                      else "REPAIR_V76_16_RELEASE_ARCHIVE_SEAL",
    }
    immutable = {
        key: value for key, value in result.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    result["seal_certificate_sha256"] = digest(immutable)
    shutil.rmtree(staging)
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    seal = result["seal_result"]
    archive = result["archive"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "seal_certificate_sha256": result["seal_certificate_sha256"],
        "archive_sha256": archive["sha256"],
        "archive_manifest_sha256": archive["archive_manifest_sha256"],
        "evidence_set_sha256": archive["evidence_set_sha256"],
        "archive_size_bytes": archive["size_bytes"],
        "archive_member_count": archive["member_count"],
        "evidence_file_count": archive["evidence_file_count"],
        "gate_count": seal["gate_count"],
        "passed_gate_count": seal["passed_gate_count"],
        "failed_gate_count": seal["failed_gate_count"],
        "failed_gate_ids": seal["failed_gate_ids"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def render_text(result: dict[str, Any]) -> str:
    summary = summary_from(result)
    return "\n".join(
        ["V76.16 RELEASE ARCHIVE SEAL"]
        + [f"{key}: {value}" for key, value in summary.items()]
    ) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "release_archive_seal_v76_16.json"
    summary_path = output_dir / "release_archive_seal_summary_v76_16.json"
    text_path = output_dir / "release_archive_seal_v76_16.txt"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary_from(result), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(render_text(result), encoding="utf-8")
    return [result_path, summary_path, text_path]


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    root = Path(args.repository_root)
    output_dir = Path(args.output_dir)
    config = load_json(Path(args.config))
    result = build_release_archive_seal(root, config, output_dir)
    outputs = write_outputs(result, output_dir)
    seal = result["seal_result"]
    archive = result["archive"]
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": seal["gate_count"],
        "passed_gate_count": seal["passed_gate_count"],
        "failed_gate_count": seal["failed_gate_count"],
        "failed_gate_ids": seal["failed_gate_ids"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "seal_certificate_sha256": result["seal_certificate_sha256"],
        "archive_sha256": archive["sha256"],
        "archive_manifest_sha256": archive["archive_manifest_sha256"],
        "evidence_set_sha256": archive["evidence_set_sha256"],
        "archive_size_bytes": archive["size_bytes"],
        "archive_member_count": archive["member_count"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
        "outputs": [str(p) for p in outputs] + [
            str(output_dir / archive["filename"])
        ],
    }, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
