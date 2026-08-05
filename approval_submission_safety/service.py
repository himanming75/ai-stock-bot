from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .io import append_jsonl, read_json, read_json_optional, write_json
from .policy import evaluate_ticket
from .request_builder import build_broker_request
from .token import validate_token


class ApprovalSubmissionSafetyService:
    def evaluate(
        self,
        *,
        ticket_bundle_path: Path,
        token_path: Path,
        policy_path: Path,
        market_path: Path,
        risk_path: Path,
        nonce_registry_path: Path,
        idempotency_registry_path: Path,
        output_dir: Path,
        secret: str,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        ticket_bundle = read_json_optional(ticket_bundle_path)
        token = read_json_optional(token_path)
        policy = read_json(policy_path)
        market = read_json_optional(market_path)
        risk = read_json_optional(risk_path)
        nonce_registry = read_json_optional(nonce_registry_path)
        idempotency_registry = read_json_optional(idempotency_registry_path)

        valid_tickets = list(ticket_bundle.get("valid_tickets", []))
        consumed_nonces = set(nonce_registry.get("consumed_nonces", []))
        prior_keys = set(idempotency_registry.get("idempotency_keys", []))

        global_blockers = []
        if not ticket_bundle:
            global_blockers.append("TICKET_BUNDLE_INPUT_MISSING")
        if not token:
            global_blockers.append("APPROVAL_TOKEN_MISSING")
        if not market:
            global_blockers.append("MARKET_INPUT_MISSING")
        if not risk:
            global_blockers.append("RISK_INPUT_MISSING")

        decisions = []
        for ticket in valid_tickets:
            scope = {
                "environment": "paper",
                "operation": "paper_order_submission_review",
                "ticket_id": ticket.get("ticket_id"),
                "idempotency_key": ticket.get("idempotency_key"),
                "request_fingerprint": ticket.get("idempotency_key"),
            }

            token_blockers = validate_token(
                token,
                expected_scope=scope,
                secret=secret,
                consumed_nonces=consumed_nonces,
                now=now,
            )
            ticket_blockers = evaluate_ticket(
                ticket,
                policy=policy,
                market=market.get("symbols", {}).get(
                    ticket.get("payload", {}).get("symbol"), {}
                ),
                risk=risk,
                prior_keys=prior_keys,
            )
            blockers = sorted(set(token_blockers + ticket_blockers))
            broker_request = build_broker_request(ticket)

            decisions.append(
                {
                    "ticket_id": ticket.get("ticket_id"),
                    "idempotency_key": ticket.get("idempotency_key"),
                    "scope": scope,
                    "status": (
                        "APPROVED_FOR_SEPARATE_SUBMISSION_STAGE"
                        if not blockers
                        else "BLOCKED"
                    ),
                    "blockers": blockers,
                    "broker_request": broker_request,
                    "retry_queue_eligible": False,
                    "retry_reason": None,
                    "token_consumed": False,
                    "nonce_registry_modified": False,
                    "idempotency_registry_modified": False,
                    "network_call_performed": False,
                    "broker_write_performed": False,
                    "paper_order_submitted": False,
                    "live_order_submitted": False,
                }
            )

        approved = [
            item for item in decisions
            if item["status"] == "APPROVED_FOR_SEPARATE_SUBMISSION_STAGE"
        ]
        blocked = [
            item for item in decisions if item["status"] == "BLOCKED"
        ]

        status = (
            "INSUFFICIENT_INPUT"
            if global_blockers
            else "PASS"
        )

        seed = {
            "ticket_bundle_fingerprint": ticket_bundle.get(
                "ticket_bundle_fingerprint"
            ),
            "decisions": decisions,
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
            "stage": "V691_TO_V780_APPROVAL_SUBMISSION_SAFETY_LAYER",
            "status": status,
            "generated_at": now.isoformat(),
            "safety_layer_fingerprint": fingerprint,
            "source_ticket_bundle_fingerprint": ticket_bundle.get(
                "ticket_bundle_fingerprint"
            ),
            "global_blockers": global_blockers,
            "ticket_decision_count": len(decisions),
            "approved_for_separate_submission_count": len(approved),
            "blocked_ticket_count": len(blocked),
            "decisions": decisions,
            "approved_queue": approved,
            "blocked_queue": blocked,
            "retry_queue": [],
            "approval_token_consumed": False,
            "nonce_registry_modified": False,
            "idempotency_registry_modified": False,
            "broker_request_json_created": len(decisions) > 0,
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "paper_submission_enabled": False,
            "live_submission_enabled": False,
            "actual_external_network_used": False,
            "actual_market_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V781_TO_V860_PAPER_SUBMIT_ENGINE"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "submission_safety_latest.json", result)
        write_json(
            output_dir / "approved_submission_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(approved),
                "items": approved,
                "submission_enabled": False,
            },
        )
        write_json(
            output_dir / "blocked_submission_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": len(blocked),
                "items": blocked,
            },
        )
        write_json(
            output_dir / "retry_queue.json",
            {
                "generated_at": now.isoformat(),
                "count": 0,
                "items": [],
                "automatic_retry_enabled": False,
            },
        )
        write_json(
            output_dir / "submission_safety_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "ticket_decision_count": len(decisions),
                "approved_for_separate_submission_count": len(approved),
                "blocked_ticket_count": len(blocked),
                "retry_queue_count": 0,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "submission_safety_ledger.jsonl",
            result,
        )
        for item in decisions:
            append_jsonl(
                output_dir / "submission_decision_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **item,
                    "network_call_performed": False,
                    "broker_write_performed": False,
                },
            )
        return result
