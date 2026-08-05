from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .envelope import build_submission_envelope
from .guards import validate_item
from .io import append_jsonl, read_json, read_json_optional, write_json
from .mapper import map_response


class PaperSubmitEngineService:
    def evaluate(
        self,
        *,
        approved_queue_path: Path,
        policy_path: Path,
        simulated_response_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        approved_input = read_json_optional(approved_queue_path)
        policy = read_json(policy_path)
        simulated = read_json_optional(simulated_response_path)

        items = list(approved_input.get("items", []))
        global_blockers = []
        if not approved_input:
            global_blockers.append("APPROVED_QUEUE_INPUT_MISSING")
        if approved_input and approved_input.get("submission_enabled") is not False:
            global_blockers.append("UPSTREAM_SUBMISSION_FLAG_INVALID")

        attempts = []
        retry_queue = []
        recovery_queue = []

        for item in items:
            blockers = validate_item(item, policy)
            built = build_submission_envelope(item)
            response_fixture = simulated.get("responses", {}).get(
                str(item.get("ticket_id")),
                simulated.get("default_response", {}),
            )
            status_code = response_fixture.get("status_code")
            body = response_fixture.get("body", {})
            mapping = map_response(status_code, body)

            if blockers:
                status = "BLOCKED"
                response_used = False
            else:
                status = "DRY_RUN_READY"
                response_used = bool(response_fixture)

            attempt = {
                **built,
                "status": status,
                "blockers": blockers,
                "simulated_response_used": response_used,
                "simulated_status_code": status_code if response_used else None,
                "simulated_body": body if response_used else {},
                "response_mapping": (
                    mapping
                    if response_used
                    else {
                        "classification": "NOT_EXECUTED",
                        "retryable": False,
                        "terminal": False,
                    }
                ),
                "actual_order_submission_performed": False,
                "actual_paper_order_submitted": False,
                "actual_live_order_submitted": False,
            }
            attempts.append(attempt)

            if status == "DRY_RUN_READY" and response_used and mapping["retryable"]:
                retry_queue.append(
                    {
                        "submission_id": built["submission_id"],
                        "ticket_id": item.get("ticket_id"),
                        "reason": mapping["classification"],
                        "automatic_retry_enabled": False,
                        "requires_reapproval": True,
                    }
                )
            if status == "DRY_RUN_READY" and response_used and not mapping["terminal"]:
                recovery_queue.append(
                    {
                        "submission_id": built["submission_id"],
                        "ticket_id": item.get("ticket_id"),
                        "state": "AWAITING_MANUAL_RECOVERY_REVIEW",
                        "automatic_action_enabled": False,
                    }
                )

        ready = [x for x in attempts if x["status"] == "DRY_RUN_READY"]
        blocked = [x for x in attempts if x["status"] == "BLOCKED"]
        status = "INSUFFICIENT_INPUT" if global_blockers else "PASS"

        seed = {
            "source_count": len(items),
            "attempts": attempts,
            "global_blockers": global_blockers,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V781_TO_V860_PAPER_SUBMIT_ENGINE",
            "status": status,
            "generated_at": now.isoformat(),
            "submit_engine_fingerprint": fingerprint,
            "engine_mode": "DRY_RUN_ONLY",
            "global_blockers": global_blockers,
            "input_item_count": len(items),
            "dry_run_ready_count": len(ready),
            "blocked_count": len(blocked),
            "retry_queue_count": len(retry_queue),
            "recovery_queue_count": len(recovery_queue),
            "attempts": attempts,
            "dry_run_ready_queue": ready,
            "blocked_queue": blocked,
            "retry_queue": retry_queue,
            "recovery_queue": recovery_queue,
            "credentials_loaded": False,
            "network_library_used": False,
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "paper_submission_enabled": False,
            "live_submission_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "nonce_registry_modified": False,
            "idempotency_registry_modified": False,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V861_TO_V940_PAPER_RECOVERY_AND_RETRY"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "paper_submit_engine_latest.json", result)
        write_json(
            output_dir / "dry_run_submission_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(ready),
                "items": ready,
                "submission_enabled": False,
            },
        )
        write_json(
            output_dir / "paper_submit_retry_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(retry_queue),
                "items": retry_queue,
                "automatic_retry_enabled": False,
            },
        )
        write_json(
            output_dir / "paper_submit_recovery_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(recovery_queue),
                "items": recovery_queue,
                "automatic_action_enabled": False,
            },
        )
        write_json(
            output_dir / "paper_submit_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "engine_mode": "DRY_RUN_ONLY",
                "input_item_count": len(items),
                "dry_run_ready_count": len(ready),
                "blocked_count": len(blocked),
                "retry_queue_count": len(retry_queue),
                "recovery_queue_count": len(recovery_queue),
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "paper_submit_engine_ledger.jsonl",
            result,
        )
        for attempt in attempts:
            append_jsonl(
                output_dir / "paper_submit_attempt_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **attempt,
                    "actual_network_call_performed": False,
                    "actual_broker_write_performed": False,
                },
            )
        return result
