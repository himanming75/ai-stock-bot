from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "76.22"
SCHEMA = "v76.22.release_archive_completion_certificate.1"
NEXT_PHASE = "V76_23_RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION"


class CompletionCertificateError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompletionCertificateError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CompletionCertificateError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CompletionCertificateError(f"JSON root must be object: {path}")
    return value


def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise CompletionCertificateError(
            f"{name} must be {length} hexadecimal characters"
        )
    try:
        int(value, 16)
    except ValueError as exc:
        raise CompletionCertificateError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("certificate_scope") != "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE":
        raise CompletionCertificateError("certificate_scope invalid")

    for key in (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_verification_self_hash",
        "require_verification_chain_self_hash",
        "require_fixed_anchor_match",
        "require_v76_21_zero_failed_gates",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise CompletionCertificateError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise CompletionCertificateError(f"{key} must be false")

    validate_hex(config.get("expected_framework_commit_sha"), 40,
                 "expected_framework_commit_sha")
    validate_hex(config.get("expected_verification_sha256"), 64,
                 "expected_verification_sha256")
    validate_hex(config.get("expected_verification_chain_sha256"), 64,
                 "expected_verification_chain_sha256")


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
        raise CompletionCertificateError(
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


def add_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool) -> None:
    gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL"})


def create_certificate(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
             git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT",
             git["head_sha"] == config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
             git["tracked_status_short"] == [])

    source_path = (
        root / "release/v76_21/output/"
        "release_archive_finalization_verification_v76_21.json"
    )
    add_gate(gates, "V76_21_VERIFICATION_EXISTS", source_path.is_file())
    source = load_json(source_path)

    stored_verification = source.get("verification_sha256")
    calculated_verification = digest({
        key: value for key, value in source.items()
        if key not in {"verification_sha256", "issued_at_utc", "duration_seconds"}
    })
    add_gate(gates, "V76_21_VERIFICATION_SELF_HASH",
             stored_verification == calculated_verification)
    add_gate(gates, "V76_21_VERIFICATION_FIXED_ANCHOR",
             stored_verification == config["expected_verification_sha256"])

    chain = source.get("verification_chain")
    calculated_chain = digest(chain) if isinstance(chain, dict) else None
    add_gate(gates, "V76_21_VERIFICATION_CHAIN_OBJECT", isinstance(chain, dict))
    add_gate(gates, "V76_21_VERIFICATION_CHAIN_SELF_HASH",
             source.get("verification_chain_sha256") == calculated_chain)
    add_gate(gates, "V76_21_VERIFICATION_CHAIN_FIXED_ANCHOR",
             source.get("verification_chain_sha256") ==
             config["expected_verification_chain_sha256"])

    verification_result = source.get("verification_result", {})
    required = {
        "V76_21_STATUS_PASS": source.get("status") == "PASS",
        "V76_21_DECISION_VERIFIED":
            source.get("decision") ==
            "release_archive_finalization_independently_verified",
        "V76_21_TYPE_MATCH":
            source.get("verification_type") ==
            "RELEASE_ARCHIVE_FINALIZATION_VERIFICATION",
        "V76_21_FINALIZATION_VERIFIED":
            source.get("release_archive_finalization_independently_verified") is True,
        "V76_21_ARCHIVE_FINALIZED":
            source.get("release_archive_finalized") is True,
        "V76_21_CLOSURE_VERIFIED":
            source.get("release_archive_closure_independently_verified") is True,
        "V76_21_CLOSURE_CERTIFIED":
            source.get("release_archive_closure_certified") is True,
        "V76_21_ARCHIVE_SEALED":
            source.get("release_archive_sealed") is True,
        "V76_21_CANDIDATE_CLOSED":
            source.get("release_candidate_closed") is True,
        "V76_21_ZERO_FAILED_GATES":
            verification_result.get("failed_gate_count") == 0,
        "V76_21_FAILED_GATE_IDS_EMPTY":
            verification_result.get("failed_gate_ids") == [],
        "V76_21_NETWORK_DISABLED": source.get("network_allowed") is False,
        "V76_21_BROKER_NOT_CONNECTED": source.get("broker_connected") is False,
        "V76_21_ZERO_ORDERS": source.get("orders_submitted") == 0,
        "V76_21_NOT_APPROVED_FOR_LIVE":
            source.get("approved_for_live") is False,
        "V76_21_LIVE_TRADING_NOT_AUTHORIZED":
            source.get("live_trading_authorized") is False,
        "V76_21_NEXT_PHASE_MATCH":
            source.get("next_phase") ==
            "V76_22_RELEASE_ARCHIVE_COMPLETION_CERTIFICATE",
    }
    for gate_id, passed in required.items():
        add_gate(gates, gate_id, passed)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"

    certified_anchors = {
        "v76_21_verification_sha256": stored_verification,
        "v76_21_verification_chain_sha256":
            source.get("verification_chain_sha256"),
    }
    completion_chain = {
        **certified_anchors,
        "v76_21_framework_commit_sha":
            source.get("repository", {}).get("framework_commit_sha"),
        "v76_21_schema_version": source.get("schema_version"),
        "v76_21_verification_type": source.get("verification_type"),
        "v76_21_decision": source.get("decision"),
    }

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 6),
        "status": status,
        "decision": (
            "release_archive_completion_certified"
            if status == "PASS"
            else "release_archive_completion_certificate_failed"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "certified_anchors": certified_anchors,
        "completion_chain": completion_chain,
        "completion_chain_sha256": digest(completion_chain),
        "certificate_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_archive_completion_certified": status == "PASS",
        "release_archive_finalization_independently_verified": status == "PASS",
        "release_archive_finalized": status == "PASS",
        "release_archive_closure_independently_verified": status == "PASS",
        "release_archive_closure_certified": status == "PASS",
        "release_archive_sealed": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": (
            NEXT_PHASE if status == "PASS"
            else "REPAIR_V76_22_COMPLETION_CERTIFICATE"
        ),
    }
    immutable = {
        key: value for key, value in result.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    result["certificate_sha256"] = digest(immutable)
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    check = result["certificate_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "certificate_sha256": result["certificate_sha256"],
        "completion_chain_sha256": result["completion_chain_sha256"],
        **result["certified_anchors"],
        "gate_count": check["gate_count"],
        "passed_gate_count": check["passed_gate_count"],
        "failed_gate_count": check["failed_gate_count"],
        "failed_gate_ids": check["failed_gate_ids"],
        "release_archive_completion_certified":
            result["release_archive_completion_certified"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "release_archive_completion_certificate_v76_22.json"
    summary_path = (
        output_dir / "release_archive_completion_certificate_summary_v76_22.json"
    )
    text_path = output_dir / "release_archive_completion_certificate_v76_22.txt"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(summary_from(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(
        "V76.22 RELEASE ARCHIVE COMPLETION CERTIFICATE\n" +
        "\n".join(f"{k}: {v}" for k, v in summary_from(result).items()) + "\n",
        encoding="utf-8",
    )
    return [result_path, summary_path, text_path]


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    result = create_certificate(
        Path(args.repository_root), load_json(Path(args.config))
    )
    write_outputs(result, Path(args.output_dir))
    print(json.dumps(summary_from(result), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
