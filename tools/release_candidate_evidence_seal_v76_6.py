from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

VERSION = "76.6"
SCHEMA = "v76.6.release_candidate_evidence_seal.1"


class SealError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SealError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SealError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SealError(f"JSON root must be object: {path}")
    return value


def validate_config(config: dict[str, Any]) -> None:
    if config.get("seal_scope") != "RELEASE_CANDIDATE_EVIDENCE_SEAL":
        raise SealError("seal_scope invalid")

    required_true = (
        "offline_only",
        "preserve_repository",
        "require_all_evidence_present",
        "require_prior_acceptance_pass",
        "require_zero_trading_side_effects",
        "require_tracked_file_immutability",
        "require_manifest_verification",
    )
    required_false = (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise SealError(f"{key} must be true")
    for key in required_false:
        if config.get(key) is not False:
            raise SealError(f"{key} must be false")

    evidence = config.get("evidence_files")
    if not isinstance(evidence, list) or not evidence:
        raise SealError("evidence_files must be a non-empty list")

    ids: set[str] = set()
    for item in evidence:
        if not isinstance(item, dict):
            raise SealError("evidence item must be an object")
        evidence_id = item.get("evidence_id")
        path = item.get("path")
        required = item.get("required")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise SealError("evidence_id required")
        if evidence_id in ids:
            raise SealError(f"duplicate evidence_id: {evidence_id}")
        ids.add(evidence_id)
        if not isinstance(path, str) or not path:
            raise SealError(f"path required for {evidence_id}")
        if required is not True:
            raise SealError(f"required must be true for {evidence_id}")


def safe_relative_path(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise SealError(f"unsafe path: {value}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise SealError(f"path outside repository: {value}") from exc
    return resolved


def git_commit_info(root: Path) -> dict[str, Any]:
    def run(args: list[str]) -> str:
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
            raise SealError(
                f"git {' '.join(args)} failed: {completed.stderr.strip()}"
            )
        return completed.stdout.strip()

    return {
        "commit_sha": run(["rev-parse", "HEAD"]),
        "branch": run(["rev-parse", "--abbrev-ref", "HEAD"]),
        "commit_subject": run(["log", "-1", "--pretty=%s"]),
        "origin_main_sha": run(["rev-parse", "origin/main"]),
    }


def tracked_snapshot(root: Path) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SealError(
            "git ls-files failed: "
            + completed.stderr.decode("utf-8", "replace")
        )
    snapshot: dict[str, str] = {}
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        name = raw.decode("utf-8", "surrogateescape")
        path = root / name
        snapshot[name.replace("\\", "/")] = (
            file_sha256(path) if path.is_file() else "<MISSING>"
        )
    return snapshot


def tracked_diff_state(root: Path) -> dict[str, Any]:
    commands = {
        "modified_tracked_files": ["git", "diff", "--name-only"],
        "staged_files": ["git", "diff", "--cached", "--name-only"],
    }
    result: dict[str, Any] = {}
    for key, command in commands.items():
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            raise SealError(f"{' '.join(command)} failed")
        result[key] = sorted(
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        )
    return result


def validate_known_evidence(evidence_id: str, value: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {"json_object": isinstance(value, dict)}

    if evidence_id == "V76_4_FULL_VERIFICATION":
        checks.update({
            "status_pass": value.get("status") == "PASS",
            "failed_scenario_count_zero":
                value.get("failed_scenario_count") == 0,
            "all_outputs_repeatable":
                value.get("all_outputs_repeatable") is True,
            "tracked_file_immutability_verified":
                value.get("tracked_file_immutability_verified") is True,
            "orders_submitted_zero":
                value.get("orders_submitted") == 0,
            "approved_for_live_false":
                value.get("approved_for_live") is False,
        })

    elif evidence_id == "V76_4_SUMMARY":
        checks.update({
            "status_pass": value.get("status") == "PASS",
            "failed_scenario_count_zero":
                value.get("failed_scenario_count") == 0,
            "all_outputs_repeatable":
                value.get("all_outputs_repeatable") is True,
            "tracked_file_immutability_verified":
                value.get("tracked_file_immutability_verified") is True,
            "next_phase_v76_5":
                value.get("next_phase")
                == "V76_5_RELEASE_CANDIDATE_SYSTEM_ACCEPTANCE",
        })

    elif evidence_id == "V76_5_FULL_ACCEPTANCE":
        checks.update({
            "status_pass": value.get("status") == "PASS",
            "failed_gate_count_zero":
                value.get("failed_gate_count") == 0,
            "release_candidate_accepted":
                value.get("release_candidate_accepted") is True,
            "tracked_file_immutability_verified":
                value.get("tracked_file_immutability_verified") is True,
            "orders_submitted_zero":
                value.get("orders_submitted") == 0,
            "approved_for_live_false":
                value.get("approved_for_live") is False,
            "next_phase_v76_6":
                value.get("next_phase")
                == "V76_6_RELEASE_CANDIDATE_EVIDENCE_SEAL",
        })

    elif evidence_id == "V76_5_SUMMARY":
        checks.update({
            "status_pass": value.get("status") == "PASS",
            "failed_gate_count_zero":
                value.get("failed_gate_count") == 0,
            "release_candidate_accepted":
                value.get("release_candidate_accepted") is True,
            "approved_for_live_false":
                value.get("approved_for_live") is False,
            "next_phase_v76_6":
                value.get("next_phase")
                == "V76_6_RELEASE_CANDIDATE_EVIDENCE_SEAL",
        })

    return checks


def collect_evidence(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in config["evidence_files"]:
        path = safe_relative_path(root, item["path"])
        record: dict[str, Any] = {
            "evidence_id": item["evidence_id"],
            "description": item.get("description", ""),
            "path": path.relative_to(root).as_posix(),
            "required": True,
            "exists": path.is_file(),
            "size_bytes": path.stat().st_size if path.is_file() else None,
            "file_sha256": file_sha256(path) if path.is_file() else None,
            "json_validation": {},
            "status": "MISSING",
        }
        if path.is_file():
            try:
                value = load_json(path)
                checks = validate_known_evidence(item["evidence_id"], value)
                record["json_validation"] = checks
                record["status"] = (
                    "PASS" if all(checks.values()) else "FAIL"
                )
            except SealError as exc:
                record["json_validation"] = {
                    "valid_json": False,
                    "error": str(exc),
                }
                record["status"] = "FAIL"
        record["record_sha256"] = digest({
            key: value for key, value in record.items()
            if key != "record_sha256"
        })
        records.append(record)
    return records


def build_manifest(
    evidence_records: list[dict[str, Any]],
    repository: dict[str, Any],
) -> dict[str, Any]:
    manifest = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "manifest_type": "RELEASE_CANDIDATE_EVIDENCE_MANIFEST",
        "repository": repository,
        "evidence_count": len(evidence_records),
        "evidence": [
            {
                "evidence_id": item["evidence_id"],
                "path": item["path"],
                "size_bytes": item["size_bytes"],
                "file_sha256": item["file_sha256"],
                "status": item["status"],
                "record_sha256": item["record_sha256"],
            }
            for item in evidence_records
        ],
    }
    manifest["manifest_sha256"] = digest(manifest)
    return manifest


def build_ledger(
    evidence_records: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    previous_hash = "0" * 64

    for index, item in enumerate(evidence_records, start=1):
        entry = {
            "sequence": index,
            "evidence_id": item["evidence_id"],
            "path": item["path"],
            "file_sha256": item["file_sha256"],
            "record_sha256": item["record_sha256"],
            "previous_entry_sha256": previous_hash,
        }
        entry["entry_sha256"] = digest(entry)
        previous_hash = entry["entry_sha256"]
        entries.append(entry)

    final_entry = {
        "sequence": len(entries) + 1,
        "evidence_id": "V76_6_MANIFEST",
        "path": "release/v76_6/output/release_candidate_evidence_manifest_v76_6.json",
        "file_sha256": None,
        "record_sha256": manifest["manifest_sha256"],
        "previous_entry_sha256": previous_hash,
    }
    final_entry["entry_sha256"] = digest(final_entry)
    entries.append(final_entry)

    ledger = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "ledger_type": "RELEASE_CANDIDATE_EVIDENCE_LEDGER",
        "entry_count": len(entries),
        "entries": entries,
        "ledger_head_sha256": entries[-1]["entry_sha256"],
    }
    ledger["ledger_sha256"] = digest(ledger)
    return ledger


def verify_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    previous_hash = "0" * 64
    errors: list[str] = []

    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        return {
            "valid": False,
            "errors": ["entries must be a list"],
        }

    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.get("sequence") != expected_sequence:
            errors.append(f"sequence mismatch at {expected_sequence}")
        if entry.get("previous_entry_sha256") != previous_hash:
            errors.append(f"previous hash mismatch at {expected_sequence}")
        stored_hash = entry.get("entry_sha256")
        calculated_hash = digest({
            key: value for key, value in entry.items()
            if key != "entry_sha256"
        })
        if stored_hash != calculated_hash:
            errors.append(f"entry hash mismatch at {expected_sequence}")
        previous_hash = stored_hash

    if entries and ledger.get("ledger_head_sha256") != entries[-1].get("entry_sha256"):
        errors.append("ledger head mismatch")

    return {
        "valid": not errors,
        "errors": errors,
        "verified_entry_count": len(entries),
        "ledger_head_sha256": ledger.get("ledger_head_sha256"),
    }


def build_certificate(
    repository: dict[str, Any],
    manifest: dict[str, Any],
    ledger: dict[str, Any],
    evidence_records: list[dict[str, Any]],
    repository_integrity: dict[str, Any],
) -> dict[str, Any]:
    failed_evidence = [
        item["evidence_id"]
        for item in evidence_records
        if item["status"] != "PASS"
    ]
    seal_material = {
        "repository_commit_sha": repository["commit_sha"],
        "origin_main_sha": repository["origin_main_sha"],
        "manifest_sha256": manifest["manifest_sha256"],
        "ledger_sha256": ledger["ledger_sha256"],
        "ledger_head_sha256": ledger["ledger_head_sha256"],
        "evidence_record_hashes": [
            item["record_sha256"] for item in evidence_records
        ],
    }
    release_seal_sha256 = digest(seal_material)

    passed = (
        not failed_evidence
        and repository["commit_sha"] == repository["origin_main_sha"]
        and repository_integrity["clean"]
    )
    certificate = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "certificate_type": "RELEASE_CANDIDATE_EVIDENCE_CERTIFICATE",
        "status": "PASS" if passed else "FAIL",
        "decision": (
            "release_candidate_evidence_sealed"
            if passed
            else "release_candidate_evidence_seal_failed"
        ),
        "repository": repository,
        "evidence_count": len(evidence_records),
        "failed_evidence_count": len(failed_evidence),
        "failed_evidence_ids": failed_evidence,
        "repository_integrity": repository_integrity,
        "manifest_sha256": manifest["manifest_sha256"],
        "ledger_sha256": ledger["ledger_sha256"],
        "ledger_head_sha256": ledger["ledger_head_sha256"],
        "release_seal_sha256": release_seal_sha256,
        "release_candidate_sealed": passed,
        "orders_submitted": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "network_allowed": False,
        "broker_connected": False,
        "approved_for_live": False,
        "next_phase": (
            "V76_7_RELEASE_CANDIDATE_SEAL_VERIFICATION"
            if passed
            else "REPAIR_RELEASE_CANDIDATE_EVIDENCE_GAPS"
        ),
    }
    certificate["certificate_sha256"] = digest(certificate)
    return certificate


def certificate_text(certificate: dict[str, Any]) -> str:
    return "\n".join([
        "AI STOCK BOT RELEASE CANDIDATE EVIDENCE CERTIFICATE",
        "=" * 58,
        f"Version                  : V{certificate['version']}",
        f"Status                   : {certificate['status']}",
        f"Decision                 : {certificate['decision']}",
        f"Repository Commit        : {certificate['repository']['commit_sha']}",
        f"Origin Main              : {certificate['repository']['origin_main_sha']}",
        f"Evidence Count           : {certificate['evidence_count']}",
        f"Failed Evidence Count    : {certificate['failed_evidence_count']}",
        f"Manifest SHA256          : {certificate['manifest_sha256']}",
        f"Ledger SHA256            : {certificate['ledger_sha256']}",
        f"Ledger Head SHA256       : {certificate['ledger_head_sha256']}",
        f"Release Seal SHA256      : {certificate['release_seal_sha256']}",
        f"Certificate SHA256       : {certificate['certificate_sha256']}",
        f"Release Candidate Sealed : {str(certificate['release_candidate_sealed']).lower()}",
        f"Orders Submitted         : {certificate['orders_submitted']}",
        f"Network Allowed          : {str(certificate['network_allowed']).lower()}",
        f"Approved For Live        : {str(certificate['approved_for_live']).lower()}",
        f"Next Phase               : {certificate['next_phase']}",
        "",
        "This certificate seals an offline release candidate only.",
        "It does not authorize or enable live trading.",
        "",
    ])


def write_outputs(
    output_dir: Path,
    manifest: dict[str, Any],
    ledger: dict[str, Any],
    certificate: dict[str, Any],
    result: dict[str, Any],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "manifest": output_dir / "release_candidate_evidence_manifest_v76_6.json",
        "ledger": output_dir / "release_candidate_evidence_ledger_v76_6.json",
        "certificate": output_dir / "release_candidate_certificate_v76_6.json",
        "result": output_dir / "release_candidate_evidence_seal_v76_6.json",
        "certificate_text": output_dir / "release_candidate_certificate_v76_6.txt",
    }

    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["ledger"].write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["certificate"].write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["result"].write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["certificate_text"].write_text(
        certificate_text(certificate),
        encoding="utf-8",
    )
    return list(paths.values())


def run_seal(root: Path, config: dict[str, Any]) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    root = root.resolve()
    if not root.is_dir():
        raise SealError(f"repository root not found: {root}")

    validate_config(config)
    started = time.time()

    before_snapshot = tracked_snapshot(root)
    before_diff = tracked_diff_state(root)
    repository = git_commit_info(root)

    evidence_records = collect_evidence(root, config)
    manifest = build_manifest(evidence_records, repository)
    ledger = build_ledger(evidence_records, manifest)
    ledger_verification = verify_ledger(ledger)

    after_snapshot = tracked_snapshot(root)
    after_diff = tracked_diff_state(root)
    changed_during_seal = sorted(
        name for name in set(before_snapshot) | set(after_snapshot)
        if before_snapshot.get(name) != after_snapshot.get(name)
    )

    repository_integrity = {
        "clean": (
            not before_diff["modified_tracked_files"]
            and not before_diff["staged_files"]
            and not after_diff["modified_tracked_files"]
            and not after_diff["staged_files"]
            and not changed_during_seal
        ),
        "head_matches_origin_main":
            repository["commit_sha"] == repository["origin_main_sha"],
        "before_diff": before_diff,
        "after_diff": after_diff,
        "changed_tracked_files_during_seal": changed_during_seal,
        "tracked_snapshot_before_sha256": digest(before_snapshot),
        "tracked_snapshot_after_sha256": digest(after_snapshot),
    }
    repository_integrity["clean"] = (
        repository_integrity["clean"]
        and repository_integrity["head_matches_origin_main"]
    )

    certificate = build_certificate(
        repository,
        manifest,
        ledger,
        evidence_records,
        repository_integrity,
    )

    all_evidence_passed = all(
        item["status"] == "PASS" for item in evidence_records
    )
    status = (
        "PASS"
        if all_evidence_passed
        and ledger_verification["valid"]
        and certificate["release_candidate_sealed"]
        else "FAIL"
    )

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "status": status,
        "decision": certificate["decision"],
        "evidence_count": len(evidence_records),
        "passed_evidence_count": sum(
            item["status"] == "PASS" for item in evidence_records
        ),
        "failed_evidence_count": sum(
            item["status"] != "PASS" for item in evidence_records
        ),
        "failed_evidence_ids": [
            item["evidence_id"]
            for item in evidence_records
            if item["status"] != "PASS"
        ],
        "evidence_records": evidence_records,
        "manifest_sha256": manifest["manifest_sha256"],
        "ledger_sha256": ledger["ledger_sha256"],
        "ledger_head_sha256": ledger["ledger_head_sha256"],
        "ledger_verification": ledger_verification,
        "release_seal_sha256": certificate["release_seal_sha256"],
        "certificate_sha256": certificate["certificate_sha256"],
        "repository_integrity": repository_integrity,
        "release_candidate_sealed":
            certificate["release_candidate_sealed"],
        "orders_submitted": 0,
        "network_allowed": False,
        "approved_for_live": False,
        "next_phase": certificate["next_phase"],
        "duration_seconds": round(time.time() - started, 6),
    }
    result["seal_result_sha256"] = digest(result)
    return result, manifest, ledger, certificate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        config = load_json(Path(args.config))
        result, manifest, ledger, certificate = run_seal(
            Path(args.repository_root),
            config,
        )
        outputs = write_outputs(
            Path(args.output_dir),
            manifest,
            ledger,
            certificate,
            result,
        )
    except (SealError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "evidence_count": result["evidence_count"],
        "passed_evidence_count": result["passed_evidence_count"],
        "failed_evidence_count": result["failed_evidence_count"],
        "failed_evidence_ids": result["failed_evidence_ids"],
        "ledger_verified": result["ledger_verification"]["valid"],
        "repository_clean":
            result["repository_integrity"]["clean"],
        "release_candidate_sealed":
            result["release_candidate_sealed"],
        "orders_submitted": result["orders_submitted"],
        "network_allowed": result["network_allowed"],
        "approved_for_live": result["approved_for_live"],
        "next_phase": result["next_phase"],
        "release_seal_sha256": result["release_seal_sha256"],
        "certificate_sha256": result["certificate_sha256"],
        "outputs": [str(path) for path in outputs],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
