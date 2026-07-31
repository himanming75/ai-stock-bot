from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpointManager
from broker.recovery_continuation_safety_v77_7 import RecoveryContinuationSafety

VERSION = "77.7"
SCHEMA = "v77.7.recovery_continuation_safety_verification.1"
NEXT_PHASE = "V77_8_MULTI_ORDER_CONTINUATION_STRESS"


class VerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root must be object: {path}")
    return value


def run_git(root: Path, args: list[str]) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if process.returncode != 0:
        raise VerificationError(f"git {' '.join(args)} failed: {process.stderr.strip()}")
    return process.stdout.strip()


def git_state(root: Path) -> dict[str, str]:
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
    }


def git_is_ancestor(root: Path, ancestor: str) -> bool:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, "HEAD"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    if process.returncode not in {0, 1}:
        raise VerificationError(process.stderr.strip())
    return process.returncode == 0


def add_gate(gates: list[dict[str, str]], gate_id: str, passed: bool) -> None:
    gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL"})


def verify(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    git = git_state(root)
    gates: list[dict[str, str]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_FRAMEWORK_COMMIT_IS_ANCESTOR",
             git_is_ancestor(root, config["expected_framework_commit_sha"]))

    source_path = root/"release/v77_6/output/restart_recovery_replay_verification_v77_6.json"
    checkpoint_path = root/"release/v77_5/output/sample_broker_state_checkpoint_v77_5.json"
    add_gate(gates, "V77_6_VERIFICATION_EXISTS", source_path.is_file())
    add_gate(gates, "V77_5_CHECKPOINT_EXISTS", checkpoint_path.is_file())
    source = load_json(source_path)
    add_gate(gates, "V77_6_STATUS_PASS", source.get("status") == "PASS")
    add_gate(gates, "V77_6_RECOVERY_ANCHOR_MATCH",
             source.get("restart_recovery_replay_sha256")
             == config["expected_v77_6_recovery_sha256"])
    add_gate(gates, "V77_6_STATE_ANCHOR_MATCH",
             source.get("replay_report", {}).get("replayed_state_sha256")
             == config["expected_v77_6_replayed_state_sha256"])
    add_gate(gates, "V77_6_VERIFICATION_ANCHOR_MATCH",
             source.get("verification_sha256")
             == config["expected_v77_6_verification_sha256"])
    add_gate(gates, "V77_6_NEXT_PHASE_MATCH",
             source.get("next_phase") == "V77_7_RECOVERY_CONTINUATION_SAFETY")

    manager = BrokerStateCheckpointManager()
    checkpoint = manager.read(checkpoint_path)
    simulator, report = RecoveryContinuationSafety(
        checkpoint_manager=manager
    ).continue_from_checkpoint(checkpoint)
    checks = report.checks

    mapping = {
        "DUPLICATE_CLIENT_ORDER_REJECTED": "duplicate_client_order_rejected",
        "NEW_ORDER_ID_UNIQUE": "new_order_id_unique",
        "NEW_FILL_ID_UNIQUE": "new_fill_id_unique",
        "ORDER_SEQUENCE_CONTIGUOUS": "new_order_sequence_contiguous",
        "FILL_SEQUENCE_CONTIGUOUS": "new_fill_sequence_contiguous",
        "EVENT_SEQUENCE_CONTIGUOUS": "new_event_sequence_contiguous",
        "SOURCE_ORDER_IDS_PRESERVED": "source_order_ids_preserved",
        "SOURCE_FILL_IDS_PRESERVED": "source_fill_ids_preserved",
        "POST_CONTINUATION_RECONCILIATION_PASS": "reconciliation_pass",
        "CONTINUED_CHECKPOINT_VALID": "continued_checkpoint_valid",
        "CONTINUED_CHECKPOINT_CHANGED": "continued_checkpoint_changed",
        "ORDER_COUNT_INCREMENTED": "order_count_incremented",
        "FILL_COUNT_INCREMENTED": "fill_count_incremented",
        "EVENT_COUNT_INCREMENTED": "event_count_incremented",
        "ACTUAL_ORDER_COUNT_ZERO": "actual_orders_submitted_zero",
        "NETWORK_DISABLED": "network_unused",
    }
    add_gate(gates, "CONTINUATION_STATUS_PASS", report.status == "PASS")
    for gate_id, key in mapping.items():
        add_gate(gates, gate_id, bool(checks[key]))
    add_gate(gates, "BROKER_DISCONNECTED", simulator.health().connected is False)

    definition = {
        "continuation_actions": [
            "reject_duplicate_client_order_id",
            "submit_new_offline_order",
            "apply_new_simulated_fill",
            "verify_identifier_continuity",
            "verify_event_sequence_continuity",
            "reconcile_continued_state",
            "create_continued_checkpoint",
            "verify_checkpoint_chain_change",
        ],
        "actual_network_calls": 0,
        "actual_orders_submitted": 0,
    }
    continuation_sha = digest(definition)
    add_gate(gates, "CONTINUATION_FRAMEWORK_DIGEST_CREATED",
             len(continuation_sha) == 64)

    failed = [g["gate_id"] for g in gates if g["status"] == "FAIL"]
    status = "PASS" if not failed else "FAIL"
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "RECOVERY_CONTINUATION_SAFETY_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "decision": (
            "recovery_continuation_safety_established"
            if status == "PASS" else "recovery_continuation_safety_rejected"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
        },
        "source_anchors": {
            "v77_6_restart_recovery_replay_sha256":
                source.get("restart_recovery_replay_sha256"),
            "v77_6_replayed_state_sha256":
                source.get("replay_report", {}).get("replayed_state_sha256"),
            "v77_6_verification_sha256": source.get("verification_sha256"),
        },
        "continuation_definition": definition,
        "recovery_continuation_safety_sha256": continuation_sha,
        "continuation_report": report.as_dict(),
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "environment": "offline",
        "network_allowed": False,
        "broker_connected": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS"
            else "REPAIR_V77_7_RECOVERY_CONTINUATION_SAFETY",
    }
    result["verification_sha256"] = digest(
        {k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc"}}
    )
    return result


def summary(result: dict[str, Any]) -> dict[str, Any]:
    vr = result["verification_result"]
    report = result["continuation_report"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "recovery_continuation_safety_sha256":
            result["recovery_continuation_safety_sha256"],
        "source_checkpoint_sha256": report["source_checkpoint_sha256"],
        "continued_checkpoint_sha256": report["continued_checkpoint_sha256"],
        "verification_sha256": result["verification_sha256"],
        **result["source_anchors"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "continuation_status": report["status"],
        "new_order_id": report["new_order_id"],
        "new_fill_id": report["new_fill_id"],
        "environment": result["environment"],
        "network_allowed": result["network_allowed"],
        "broker_connected": result["broker_connected"],
        "actual_orders_submitted": result["actual_orders_submitted"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def write_outputs(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir/"recovery_continuation_safety_verification_v77_7.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )
    (output_dir/"recovery_continuation_safety_summary_v77_7.json").write_text(
        json.dumps(summary(result), indent=2, sort_keys=True)+"\n", encoding="utf-8"
    )


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = verify(Path(args.repository_root), load_json(Path(args.config)))
    write_outputs(result, Path(args.output_dir))
    print(json.dumps(summary(result), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
