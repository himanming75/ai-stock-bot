from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .backoff import calculate_backoff
from .classifier import classify_reason
from .io import append_jsonl, read_json, read_json_optional, write_json


class PaperRecoveryRetryService:
    def evaluate(
        self,
        *,
        retry_queue_path: Path,
        recovery_queue_path: Path,
        checkpoint_path: Path,
        policy_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        retry_input = read_json_optional(retry_queue_path)
        recovery_input = read_json_optional(recovery_queue_path)
        checkpoint = read_json_optional(checkpoint_path)
        policy = read_json(policy_path)

        retry_items = list(retry_input.get("items", []))
        recovery_items = list(recovery_input.get("items", []))
        prior_attempts = checkpoint.get("attempts", {})

        global_blockers = []
        if not retry_input:
            global_blockers.append("RETRY_QUEUE_INPUT_MISSING")
        if not recovery_input:
            global_blockers.append("RECOVERY_QUEUE_INPUT_MISSING")

        retry_plans = []
        dead_letter = []
        manual_recovery = []

        maximum_attempts = int(policy.get("maximum_attempts", 3))
        base_seconds = int(policy.get("base_backoff_seconds", 5))
        max_seconds = int(policy.get("maximum_backoff_seconds", 300))

        for item in retry_items:
            submission_id = str(item.get("submission_id", ""))
            reason = str(item.get("reason", "UNKNOWN"))
            previous = int(prior_attempts.get(submission_id, 0))
            next_attempt = previous + 1
            classification = classify_reason(reason)

            if (
                not classification["retryable"]
                or next_attempt > maximum_attempts
            ):
                dead_letter.append(
                    {
                        "submission_id": submission_id,
                        "ticket_id": item.get("ticket_id"),
                        "reason": reason,
                        "previous_attempts": previous,
                        "next_attempt": next_attempt,
                        "classification": classification,
                        "state": "DEAD_LETTER",
                        "automatic_action_enabled": False,
                    }
                )
                continue

            backoff_seconds = calculate_backoff(
                next_attempt,
                base_seconds=base_seconds,
                maximum_seconds=max_seconds,
            )
            retry_plans.append(
                {
                    "submission_id": submission_id,
                    "ticket_id": item.get("ticket_id"),
                    "reason": reason,
                    "previous_attempts": previous,
                    "next_attempt": next_attempt,
                    "backoff_seconds": backoff_seconds,
                    "eligible_after": (
                        now + timedelta(seconds=backoff_seconds)
                    ).isoformat(),
                    "requires_reapproval": True,
                    "requires_fresh_market_check": True,
                    "requires_fresh_risk_check": True,
                    "requires_fresh_idempotency_check": True,
                    "automatic_retry_enabled": False,
                    "network_call_allowed": False,
                    "broker_write_allowed": False,
                    "state": "PLANNED_FOR_MANUAL_RETRY_REVIEW",
                }
            )

        for item in recovery_items:
            manual_recovery.append(
                {
                    "submission_id": item.get("submission_id"),
                    "ticket_id": item.get("ticket_id"),
                    "source_state": item.get("state"),
                    "state": "MANUAL_RECOVERY_REQUIRED",
                    "requires_checkpoint_review": True,
                    "requires_reapproval": True,
                    "automatic_action_enabled": False,
                    "network_call_allowed": False,
                    "broker_write_allowed": False,
                }
            )

        checkpoint_preview = {
            "generated_at": now.isoformat(),
            "attempts": {
                **prior_attempts,
                **{
                    item["submission_id"]: item["next_attempt"]
                    for item in retry_plans
                },
            },
            "preview_only": True,
            "persisted": False,
        }

        status = (
            "INSUFFICIENT_INPUT"
            if global_blockers
            else "PASS"
        )

        seed = {
            "retry_plans": retry_plans,
            "dead_letter": dead_letter,
            "manual_recovery": manual_recovery,
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
            "stage": "V861_TO_V940_PAPER_RECOVERY_AND_RETRY",
            "status": status,
            "generated_at": now.isoformat(),
            "recovery_retry_fingerprint": fingerprint,
            "global_blockers": global_blockers,
            "retry_input_count": len(retry_items),
            "recovery_input_count": len(recovery_items),
            "manual_retry_plan_count": len(retry_plans),
            "manual_recovery_count": len(manual_recovery),
            "dead_letter_count": len(dead_letter),
            "retry_plans": retry_plans,
            "manual_recovery_queue": manual_recovery,
            "dead_letter_queue": dead_letter,
            "checkpoint_preview": checkpoint_preview,
            "checkpoint_modified": False,
            "automatic_retry_enabled": False,
            "automatic_recovery_enabled": False,
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
                "V941_TO_V1000_END_TO_END_CERTIFICATION"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "paper_recovery_retry_latest.json", result)
        write_json(
            output_dir / "manual_retry_plan_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(retry_plans),
                "items": retry_plans,
                "automatic_retry_enabled": False,
            },
        )
        write_json(
            output_dir / "manual_recovery_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(manual_recovery),
                "items": manual_recovery,
                "automatic_recovery_enabled": False,
            },
        )
        write_json(
            output_dir / "dead_letter_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(dead_letter),
                "items": dead_letter,
            },
        )
        write_json(
            output_dir / "checkpoint_preview.json",
            checkpoint_preview,
        )
        write_json(
            output_dir / "paper_recovery_retry_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "retry_input_count": len(retry_items),
                "recovery_input_count": len(recovery_items),
                "manual_retry_plan_count": len(retry_plans),
                "manual_recovery_count": len(manual_recovery),
                "dead_letter_count": len(dead_letter),
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "paper_recovery_retry_ledger.jsonl",
            result,
        )
        for item in retry_plans:
            append_jsonl(
                output_dir / "manual_retry_plan_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **item,
                    "automatic_retry_enabled": False,
                },
            )
        return result
