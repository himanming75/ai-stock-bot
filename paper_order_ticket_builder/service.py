from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .builder import build_ticket
from .io import append_jsonl, read_json, read_json_optional, write_json

class PaperOrderTicketBuilderService:
    def evaluate(
        self,
        *,
        execution_planning_path: Path,
        market_path: Path,
        policy_path: Path,
        prior_ticket_registry_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        planning = read_json_optional(execution_planning_path)
        market = read_json_optional(market_path)
        policy = read_json(policy_path)
        registry = read_json_optional(prior_ticket_registry_path)
        consumed_keys = set(registry.get("idempotency_keys", []))

        eligible_plans = list(planning.get("ready_plans", []))
        tickets = []
        global_blockers = []

        if not planning:
            global_blockers.append("EXECUTION_PLANNING_INPUT_MISSING")
        if planning and planning.get("status") == "INSUFFICIENT_INPUT":
            global_blockers.append("EXECUTION_PLANNING_NOT_READY")
        if not market:
            global_blockers.append("TICKET_MARKET_INPUT_MISSING")

        for plan in eligible_plans:
            symbol = str(plan.get("symbol", ""))
            symbol_market = market.get("symbols", {}).get(symbol, {})
            if not symbol_market:
                global_blockers.append(
                    f"MARKET_PRICE_MISSING:{symbol}"
                )
                continue

            for child in plan.get("child_orders", []):
                ticket = build_ticket(
                    plan=plan,
                    child=child,
                    market=symbol_market,
                    policy=policy,
                )
                if ticket["idempotency_key"] in consumed_keys:
                    ticket["status"] = "BLOCKED"
                    ticket["blockers"].append(
                        "IDEMPOTENCY_KEY_ALREADY_REGISTERED"
                    )
                tickets.append(ticket)

        valid = [t for t in tickets if t["status"] == "VALID"]
        blocked = [t for t in tickets if t["status"] == "BLOCKED"]

        status = (
            "INSUFFICIENT_INPUT"
            if global_blockers
            else "PASS"
        )

        seed = {
            "execution_planning_fingerprint": planning.get(
                "execution_planning_fingerprint"
            ),
            "ticket_ids": [t["ticket_id"] for t in tickets],
            "idempotency_keys": [t["idempotency_key"] for t in tickets],
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V641_TO_V690_PAPER_ORDER_TICKET_BUILDER",
            "status": status,
            "generated_at": now.isoformat(),
            "ticket_bundle_fingerprint": fingerprint,
            "source_execution_planning_fingerprint": planning.get(
                "execution_planning_fingerprint"
            ),
            "eligible_plan_count": len(eligible_plans),
            "ticket_count": len(tickets),
            "valid_ticket_count": len(valid),
            "blocked_ticket_count": len(blocked),
            "global_blockers": sorted(set(global_blockers)),
            "tickets": tickets,
            "valid_tickets": valid,
            "blocked_tickets": blocked,
            "paper_endpoint": "https://paper-api.alpaca.markets",
            "paper_endpoint_verified_by_configuration": True,
            "approval_token_consumed": False,
            "idempotency_registry_modified": False,
            "broker_network_enabled": False,
            "paper_order_submission_enabled": False,
            "live_order_submission_enabled": False,
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
                "V691_TO_V740_PAPER_TICKET_APPROVAL_AND_SUBMISSION_ADAPTER"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "paper_order_ticket_bundle.json", result)
        write_json(
            output_dir / "valid_ticket_queue.json",
            {
                "generated_at": now.isoformat(),
                "valid_ticket_count": len(valid),
                "tickets": valid,
                "broker_network_enabled": False,
                "submission_enabled": False,
            },
        )
        write_json(
            output_dir / "paper_order_ticket_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "eligible_plan_count": len(eligible_plans),
                "ticket_count": len(tickets),
                "valid_ticket_count": len(valid),
                "blocked_ticket_count": len(blocked),
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "paper_order_ticket_bundle_ledger.jsonl",
            result,
        )
        for ticket in tickets:
            append_jsonl(
                output_dir / "paper_order_ticket_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **ticket,
                    "submission_enabled": False,
                    "broker_write_allowed": False,
                },
            )
        return result
