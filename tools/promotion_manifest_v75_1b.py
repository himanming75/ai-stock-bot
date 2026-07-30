from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "75.1B"
SCHEMA_VERSION = "v75.1b.promotion_manifest.1"
SUPPORTED_SOURCE_SCHEMA = "v75.1a.champion_promotion_package.1"


class PromotionManifestError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromotionManifestError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromotionManifestError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PromotionManifestError("top-level JSON must be an object")
    return data


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise PromotionManifestError("source status must be PASS")
    if source.get("schema_version") != SUPPORTED_SOURCE_SCHEMA:
        raise PromotionManifestError("unsupported source schema_version")
    if source.get("package_state") != "READY_FOR_PROMOTION_MANIFEST":
        raise PromotionManifestError(
            "package_state must be READY_FOR_PROMOTION_MANIFEST"
        )
    if source.get("approved_for_live") is not False:
        raise PromotionManifestError("source approved_for_live must be false")
    if source.get("network_used") is not False:
        raise PromotionManifestError("source network_used must be false")

    champion = source.get("champion_package")
    summary = source.get("promotion_summary")
    if not isinstance(champion, dict):
        raise PromotionManifestError("champion_package is required")
    if not isinstance(summary, dict):
        raise PromotionManifestError("promotion_summary is required")

    if champion.get("package_role") != "CHAMPION":
        raise PromotionManifestError("champion package_role must be CHAMPION")
    if champion.get("promotion_scope") != "PROVISIONAL_PAPER_ONLY":
        raise PromotionManifestError(
            "champion promotion_scope must be PROVISIONAL_PAPER_ONLY"
        )
    if champion.get("paper_activation_state") != "NOT_ACTIVATED":
        raise PromotionManifestError(
            "champion paper_activation_state must be NOT_ACTIVATED"
        )
    if champion.get("approved_for_live") is not False:
        raise PromotionManifestError(
            "champion approved_for_live must be false"
        )
    if champion.get("network_used") is not False:
        raise PromotionManifestError("champion network_used must be false")

    if summary.get("requires_promotion_manifest") is not True:
        raise PromotionManifestError(
            "promotion summary must require promotion manifest"
        )
    if summary.get("requires_rollback_manifest") is not True:
        raise PromotionManifestError(
            "promotion summary must require rollback manifest"
        )
    if summary.get("champion_candidate_id") != champion.get("candidate_id"):
        raise PromotionManifestError(
            "champion id mismatch between summary and package"
        )

    runner = source.get("runner_up_package")
    runner_id = summary.get("runner_up_candidate_id")
    if runner_id is None:
        if runner is not None:
            raise PromotionManifestError(
                "runner_up_package must be null when runner_up_candidate_id is null"
            )
    else:
        if not isinstance(runner, dict):
            raise PromotionManifestError("runner_up_package is required")
        if runner.get("package_role") != "RUNNER_UP":
            raise PromotionManifestError(
                "runner_up package_role must be RUNNER_UP"
            )
        if runner.get("candidate_id") != runner_id:
            raise PromotionManifestError(
                "runner-up id mismatch between summary and package"
            )
        if runner.get("approved_for_live") is not False:
            raise PromotionManifestError(
                "runner-up approved_for_live must be false"
            )
        if runner.get("network_used") is not False:
            raise PromotionManifestError("runner-up network_used must be false")

    observed_hash = source.get("promotion_package_sha256")
    if not isinstance(observed_hash, str) or len(observed_hash) != 64:
        raise PromotionManifestError("promotion_package_sha256 is invalid")

    copied = dict(source)
    copied.pop("promotion_package_sha256", None)
    expected_hash = sha256_of(copied)
    if observed_hash != expected_hash:
        raise PromotionManifestError(
            "promotion package integrity verification failed"
        )


def build_activation_sequence(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    champion = source["champion_package"]
    runner = source.get("runner_up_package")

    sequence = [
        {
            "sequence": 1,
            "action": "VERIFY_PROMOTION_PACKAGE_INTEGRITY",
            "candidate_id": champion["candidate_id"],
            "required_state": "PASS",
        },
        {
            "sequence": 2,
            "action": "VERIFY_OPERATOR_REVIEW",
            "candidate_id": champion["candidate_id"],
            "required_state": "APPROVED",
        },
        {
            "sequence": 3,
            "action": "VERIFY_ROLLBACK_MANIFEST",
            "candidate_id": champion["candidate_id"],
            "required_state": "READY",
        },
        {
            "sequence": 4,
            "action": "STAGE_CHAMPION_FOR_PROVISIONAL_PAPER",
            "candidate_id": champion["candidate_id"],
            "required_state": "STAGED",
        },
    ]
    if runner is not None:
        sequence.append(
            {
                "sequence": 5,
                "action": "REGISTER_RUNNER_UP_FAILOVER",
                "candidate_id": runner["candidate_id"],
                "required_state": "REGISTERED",
            }
        )
    sequence.append(
        {
            "sequence": len(sequence) + 1,
            "action": "AWAIT_PAPER_SESSION_BOOTSTRAP",
            "candidate_id": champion["candidate_id"],
            "required_state": "PENDING",
        }
    )
    return sequence


def build_promotion_manifest(
    source: Dict[str, Any],
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)

    if created_at is None:
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    champion = source["champion_package"]
    runner = source.get("runner_up_package")
    summary = source["promotion_summary"]

    activation_sequence = build_activation_sequence(source)

    ledger = [
        {
            "ledger_index": 1,
            "event": "PROMOTION_PACKAGE_VERIFIED",
            "candidate_id": champion["candidate_id"],
            "state": "PASS",
        },
        {
            "ledger_index": 2,
            "event": "CHAMPION_REGISTERED",
            "candidate_id": champion["candidate_id"],
            "state": "REGISTERED",
        },
    ]
    if runner is not None:
        ledger.append(
            {
                "ledger_index": 3,
                "event": "RUNNER_UP_REGISTERED",
                "candidate_id": runner["candidate_id"],
                "state": "REGISTERED",
            }
        )
    ledger.append(
        {
            "ledger_index": len(ledger) + 1,
            "event": "PROMOTION_MANIFEST_CREATED",
            "candidate_id": champion["candidate_id"],
            "state": "READY",
        }
    )

    manifest = {
        "status": "PASS",
        "decision": "promotion_manifest_created",
        "manifest_state": "READY_FOR_ROLLBACK_MANIFEST",
        "promotion_scope": "PROVISIONAL_PAPER_ONLY",
        "champion_candidate_id": champion["candidate_id"],
        "runner_up_candidate_id": (
            runner["candidate_id"] if runner is not None else None
        ),
        "champion_score": champion["requalification_score"],
        "runner_up_score": (
            runner["requalification_score"] if runner is not None else None
        ),
        "promotion_order": [
            champion["candidate_id"],
            *([runner["candidate_id"]] if runner is not None else []),
        ],
        "activation_sequence": activation_sequence,
        "promotion_ledger": ledger,
        "integrity_verification": {
            "source_package_sha256": source["promotion_package_sha256"],
            "champion_package_sha256": champion["candidate_package_sha256"],
            "runner_up_package_sha256": (
                runner["candidate_package_sha256"] if runner is not None else None
            ),
            "promotion_summary_sha256": summary["promotion_summary_sha256"],
            "verified": True,
        },
        "rollback_reference": {
            "required": True,
            "expected_version": "75.1C",
            "expected_state": "READY",
        },
        "paper_session_reference": {
            "activation_allowed": False,
            "expected_bootstrap_version": "75.2A",
            "state": "NOT_CREATED",
        },
        "requires_operator_review": True,
        "requires_rollback_manifest": True,
        "requires_paper_session_bootstrap": True,
        "created_at": created_at,
        "approved_for_live": False,
        "network_used": False,
        "source_promotion_package_sha256": source["promotion_package_sha256"],
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    manifest["activation_sequence_sha256"] = sha256_of(activation_sequence)
    manifest["promotion_ledger_sha256"] = sha256_of(ledger)
    manifest["promotion_manifest_sha256"] = sha256_of(manifest)
    return manifest


def write_outputs(manifest: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "promotion_manifest_v75_1b.json": manifest,
        "activation_sequence_v75_1b.json": {
            "activation_sequence": manifest["activation_sequence"],
            "activation_sequence_sha256": manifest[
                "activation_sequence_sha256"
            ],
        },
        "promotion_ledger_v75_1b.json": {
            "promotion_ledger": manifest["promotion_ledger"],
            "promotion_ledger_sha256": manifest[
                "promotion_ledger_sha256"
            ],
        },
    }

    for filename, data in outputs.items():
        (output_dir / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    (output_dir / "promotion_manifest_v75_1b.sha256").write_text(
        manifest["promotion_manifest_sha256"] + "\n",
        encoding="utf-8",
    )


def run(input_path: Path, output_dir: Path) -> Dict[str, Any]:
    source = read_json(input_path)
    manifest = build_promotion_manifest(source)
    write_outputs(manifest, output_dir)
    return manifest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.1B Promotion Manifest Builder"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = run(args.input, args.output_dir)
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "promotion_manifest_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": manifest["status"],
        "decision": manifest["decision"],
        "manifest_state": manifest["manifest_state"],
        "champion_candidate_id": manifest["champion_candidate_id"],
        "runner_up_candidate_id": manifest["runner_up_candidate_id"],
        "activation_step_count": len(manifest["activation_sequence"]),
        "ledger_entry_count": len(manifest["promotion_ledger"]),
        "requires_rollback_manifest": manifest[
            "requires_rollback_manifest"
        ],
        "requires_paper_session_bootstrap": manifest[
            "requires_paper_session_bootstrap"
        ],
        "approved_for_live": manifest["approved_for_live"],
        "network_used": manifest["network_used"],
        "promotion_manifest_sha256": manifest[
            "promotion_manifest_sha256"
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
