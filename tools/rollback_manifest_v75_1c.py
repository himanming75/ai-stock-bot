from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "75.1C"
SCHEMA_VERSION = "v75.1c.rollback_manifest.1"
SUPPORTED_SOURCE_SCHEMA = "v75.1b.promotion_manifest.1"


class RollbackManifestError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RollbackManifestError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RollbackManifestError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise RollbackManifestError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise RollbackManifestError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise RollbackManifestError("unsupported source schema_version")
    if source.get("manifest_state") != "READY_FOR_ROLLBACK_MANIFEST":
        raise RollbackManifestError(
            "manifest_state must be READY_FOR_ROLLBACK_MANIFEST"
        )
    if source.get("promotion_scope") != "PROVISIONAL_PAPER_ONLY":
        raise RollbackManifestError(
            "promotion_scope must be PROVISIONAL_PAPER_ONLY"
        )
    if source.get("requires_rollback_manifest") is not True:
        raise RollbackManifestError("rollback manifest must be required")
    if source.get("approved_for_live") is not False:
        raise RollbackManifestError("source approved_for_live must be false")
    if source.get("network_used") is not False:
        raise RollbackManifestError("source network_used must be false")

    champion_id = source.get("champion_candidate_id")
    if not champion_id:
        raise RollbackManifestError("champion_candidate_id is required")

    order = source.get("promotion_order")
    if not isinstance(order, list) or not order:
        raise RollbackManifestError("promotion_order must be non-empty")
    if order[0] != champion_id:
        raise RollbackManifestError(
            "champion must be first in promotion_order"
        )

    runner_id = source.get("runner_up_candidate_id")
    if runner_id is not None:
        if len(order) < 2 or order[1] != runner_id:
            raise RollbackManifestError(
                "runner-up must be second in promotion_order"
            )

    rollback_ref = source.get("rollback_reference")
    if not isinstance(rollback_ref, dict):
        raise RollbackManifestError("rollback_reference is required")
    if rollback_ref.get("required") is not True:
        raise RollbackManifestError("rollback_reference.required must be true")
    if rollback_ref.get("expected_version") != VERSION:
        raise RollbackManifestError(
            "rollback_reference.expected_version must be 75.1C"
        )

    observed_hash = source.get("promotion_manifest_sha256")
    if not isinstance(observed_hash, str) or len(observed_hash) != 64:
        raise RollbackManifestError("promotion_manifest_sha256 is invalid")

    copied = dict(source)
    copied.pop("promotion_manifest_sha256", None)
    expected_hash = sha256_of(copied)
    if observed_hash != expected_hash:
        raise RollbackManifestError(
            "promotion manifest integrity verification failed"
        )


def build_rollback_sequence(
    champion_id: str,
    runner_up_id: Optional[str],
) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = [
        {
            "sequence": 1,
            "action": "FREEZE_NEW_PAPER_ORDERS",
            "candidate_id": champion_id,
            "required_state": "FROZEN",
        },
        {
            "sequence": 2,
            "action": "CAPTURE_FINAL_PAPER_SNAPSHOT",
            "candidate_id": champion_id,
            "required_state": "CAPTURED",
        },
        {
            "sequence": 3,
            "action": "CANCEL_PENDING_PAPER_ORDERS",
            "candidate_id": champion_id,
            "required_state": "CANCELLED",
        },
        {
            "sequence": 4,
            "action": "RECONCILE_PAPER_POSITIONS",
            "candidate_id": champion_id,
            "required_state": "RECONCILED",
        },
        {
            "sequence": 5,
            "action": "DEACTIVATE_CHAMPION",
            "candidate_id": champion_id,
            "required_state": "DEACTIVATED",
        },
    ]
    if runner_up_id is not None:
        steps.append(
            {
                "sequence": 6,
                "action": "STAGE_RUNNER_UP_FAILOVER",
                "candidate_id": runner_up_id,
                "required_state": "STAGED",
            }
        )
    steps.append(
        {
            "sequence": len(steps) + 1,
            "action": "VERIFY_RECOVERY_STATE",
            "candidate_id": runner_up_id or champion_id,
            "required_state": "PASS",
        }
    )
    return steps


def build_rollback_manifest(
    source: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    champion_id = source["champion_candidate_id"]
    runner_up_id = source.get("runner_up_candidate_id")
    rollback_sequence = build_rollback_sequence(champion_id, runner_up_id)

    rollback_ledger = [
        {
            "ledger_index": 1,
            "event": "ROLLBACK_PLAN_REGISTERED",
            "candidate_id": champion_id,
            "state": "READY",
        },
        {
            "ledger_index": 2,
            "event": "CHAMPION_ROLLBACK_ROUTE_CREATED",
            "candidate_id": champion_id,
            "state": "READY",
        },
    ]
    if runner_up_id is not None:
        rollback_ledger.append(
            {
                "ledger_index": 3,
                "event": "RUNNER_UP_FAILOVER_ROUTE_CREATED",
                "candidate_id": runner_up_id,
                "state": "READY",
            }
        )
    rollback_ledger.append(
        {
            "ledger_index": len(rollback_ledger) + 1,
            "event": "ROLLBACK_MANIFEST_CREATED",
            "candidate_id": champion_id,
            "state": "READY",
        }
    )

    manifest = {
        "status": "PASS",
        "decision": "rollback_manifest_created",
        "rollback_state": "READY_FOR_PAPER_SESSION_BOOTSTRAP",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": champion_id,
        "runner_up_candidate_id": runner_up_id,
        "rollback_policy": {
            "mode": "MANUAL_OPERATOR_TRIGGERED",
            "automatic_live_actions_allowed": False,
            "close_positions_policy": "RECONCILE_THEN_DEACTIVATE",
            "pending_order_policy": "CANCEL_ALL_PAPER_ONLY",
            "failover_policy": (
                "STAGE_RUNNER_UP"
                if runner_up_id is not None
                else "RETURN_TO_IDLE"
            ),
        },
        "trigger_conditions": [
            "OPERATOR_REQUEST",
            "PAPER_RISK_LIMIT_BREACH",
            "PAPER_SESSION_INTEGRITY_FAILURE",
            "PAPER_RECONCILIATION_FAILURE",
            "CHAMPION_HEALTH_CHECK_FAILURE",
        ],
        "rollback_sequence": rollback_sequence,
        "rollback_ledger": rollback_ledger,
        "recovery_verification": {
            "paper_orders_frozen": False,
            "pending_orders_cancelled": False,
            "positions_reconciled": False,
            "champion_deactivated": False,
            "runner_up_staged": False if runner_up_id is not None else None,
            "verification_state": "PENDING_EXECUTION",
        },
        "paper_session_reference": {
            "bootstrap_version": "75.2A",
            "bootstrap_allowed": True,
            "activation_allowed": False,
        },
        "requires_operator_review": True,
        "requires_paper_session_bootstrap": True,
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_promotion_manifest_sha256": source[
            "promotion_manifest_sha256"
        ],
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    manifest["rollback_sequence_sha256"] = sha256_of(rollback_sequence)
    manifest["rollback_ledger_sha256"] = sha256_of(rollback_ledger)
    manifest["rollback_manifest_sha256"] = sha256_of(manifest)
    return manifest


def write_outputs(manifest: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "rollback_manifest_v75_1c.json": manifest,
        "rollback_sequence_v75_1c.json": {
            "rollback_sequence": manifest["rollback_sequence"],
            "rollback_sequence_sha256": manifest[
                "rollback_sequence_sha256"
            ],
        },
        "rollback_ledger_v75_1c.json": {
            "rollback_ledger": manifest["rollback_ledger"],
            "rollback_ledger_sha256": manifest[
                "rollback_ledger_sha256"
            ],
        },
        "recovery_verification_v75_1c.json": manifest[
            "recovery_verification"
        ],
    }

    for filename, data in outputs.items():
        (output_dir / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (output_dir / "rollback_manifest_v75_1c.sha256").write_text(
        manifest["rollback_manifest_sha256"] + "\n",
        encoding="utf-8",
    )


def run(input_path: Path, output_dir: Path) -> Dict[str, Any]:
    source = read_json(input_path)
    manifest = build_rollback_manifest(source)
    write_outputs(manifest, output_dir)
    return manifest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.1C Rollback Manifest Builder"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = run(args.input, args.output_dir)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "rollback_manifest_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": manifest["status"],
        "decision": manifest["decision"],
        "rollback_state": manifest["rollback_state"],
        "champion_candidate_id": manifest["champion_candidate_id"],
        "runner_up_candidate_id": manifest["runner_up_candidate_id"],
        "rollback_step_count": len(manifest["rollback_sequence"]),
        "ledger_entry_count": len(manifest["rollback_ledger"]),
        "bootstrap_allowed": manifest["paper_session_reference"][
            "bootstrap_allowed"
        ],
        "activation_allowed": manifest["paper_session_reference"][
            "activation_allowed"
        ],
        "approved_for_live": manifest["approved_for_live"],
        "network_used": manifest["network_used"],
        "rollback_manifest_sha256": manifest[
            "rollback_manifest_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
