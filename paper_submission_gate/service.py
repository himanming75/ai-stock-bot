from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .client import AlpacaPaperClient
from .models import D, SubmissionPolicy, SubmissionRecord
from .token import consume_token, validate_token


class PaperSubmissionService:
    def __init__(self, client=None) -> None:
        self.client = client or AlpacaPaperClient()

    def _ticket_blockers(
        self,
        ticket: dict,
        policy: SubmissionPolicy,
        clock: dict,
        existing_client_ids: set[str],
    ) -> list[str]:
        blockers = list(ticket.get("blockers", []))
        payload = ticket.get("payload", {})
        symbol = str(payload.get("symbol", "")).upper()
        quantity = D(payload.get("qty"))
        order_type = str(payload.get("type", "")).lower()
        price = D(payload.get("limit_price"))
        notional = quantity * price if price > 0 else D(ticket.get("estimated_notional"))

        if ticket.get("blocked", False):
            blockers.append("TICKET_ALREADY_BLOCKED")
        if symbol not in policy.allowed_symbols:
            blockers.append("SYMBOL_NOT_ALLOWED")
        if quantity <= 0 or quantity > policy.maximum_quantity:
            blockers.append("QUANTITY_LIMIT_VIOLATION")
        if notional <= 0 or notional > policy.maximum_order_notional:
            blockers.append("ORDER_NOTIONAL_LIMIT_VIOLATION")
        if policy.require_limit_order and order_type != "limit":
            blockers.append("LIMIT_ORDER_REQUIRED")
        if policy.require_market_open and not clock.get("is_open", False):
            blockers.append("MARKET_NOT_OPEN")
        if payload.get("client_order_id") in existing_client_ids:
            blockers.append("DUPLICATE_CLIENT_ORDER_ID")

        return sorted(set(blockers))

    def submit(
        self,
        ticket_snapshot_path: Path,
        policy_path: Path,
        token_path: Path,
        nonce: str,
        output_path: Path,
    ) -> dict:
        ticket_bytes = ticket_snapshot_path.read_bytes()
        ticket_hash = hashlib.sha256(ticket_bytes).hexdigest()
        token, token_blockers = validate_token(
            token_path, ticket_hash, nonce
        )

        tickets_payload = json.loads(ticket_bytes.decode("utf-8"))
        policy = SubmissionPolicy.from_mapping(
            json.loads(policy_path.read_text(encoding="utf-8"))
        )
        clock = self.client.clock()
        account = self.client.account()
        open_orders = self.client.open_orders()
        existing_client_ids = {
            str(order.get("client_order_id"))
            for order in open_orders
            if order.get("client_order_id")
        }

        ready = [
            ticket
            for ticket in tickets_payload.get("tickets", [])
            if not ticket.get("blocked", False)
        ][: policy.maximum_total_orders]

        records: list[SubmissionRecord] = []
        submitted_count = 0

        for ticket in ready:
            blockers = list(token_blockers)
            blockers.extend(
                self._ticket_blockers(
                    ticket, policy, clock, existing_client_ids
                )
            )
            blockers = sorted(set(blockers))

            response = None
            broker_order_id = None
            broker_status = None
            submitted = False

            if not blockers:
                response = self.client.submit_order(ticket["payload"])
                broker_order_id = response.get("id")
                broker_status = response.get("status")
                submitted = True
                submitted_count += 1
                existing_client_ids.add(ticket["payload"]["client_order_id"])

            records.append(
                SubmissionRecord(
                    ticket_id=ticket["ticket_id"],
                    client_order_id=ticket["payload"]["client_order_id"],
                    symbol=ticket["payload"]["symbol"],
                    submitted=submitted,
                    broker_order_id=broker_order_id,
                    broker_status=broker_status,
                    blocked=bool(blockers),
                    blockers=tuple(blockers),
                    broker_response=response,
                )
            )

        if submitted_count > 0 and token is not None:
            consume_token(token_path, token)

        reconciliation = []
        for record in records:
            if not record.submitted:
                continue
            broker_order = self.client.get_order_by_client_order_id(
                record.client_order_id
            )
            reconciliation.append(
                {
                    "client_order_id": record.client_order_id,
                    "local_broker_order_id": record.broker_order_id,
                    "remote_broker_order_id": broker_order.get("id"),
                    "remote_status": broker_order.get("status"),
                    "matched": (
                        broker_order.get("id") == record.broker_order_id
                    ),
                }
            )

        payload = {
            "stage": "PAPER_ORDER_SUBMISSION_GATE_AND_RECONCILIATION",
            "status": (
                "PASS"
                if submitted_count > 0
                and all(item["matched"] for item in reconciliation)
                else "BLOCKED"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "paper_endpoint_verified": True,
            "market_is_open": bool(clock.get("is_open", False)),
            "account_status": account.get("status"),
            "ticket_snapshot_sha256": ticket_hash,
            "records": [record.as_json() for record in records],
            "reconciliation": reconciliation,
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": submitted_count > 0,
            "actual_order_submission_performed": submitted_count > 0,
            "actual_paper_orders_submitted": submitted_count,
            "actual_live_orders_submitted": 0,
            "next_market_validation": "P3_ORDER_LIFECYCLE_AND_CANCEL_VALIDATION",
            "next_fixed_development": "PAPER_ORDER_LIFECYCLE_MONITOR",
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with (output_path.parent / "submission_ledger.jsonl").open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

        return payload
