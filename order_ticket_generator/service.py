from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from .models import D, OrderTicket, TicketPolicy


class OrderTicketGeneratorService:
    def _stable_id(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        limit_price: Decimal | None,
        slice_number: int,
        slice_count: int,
        prefix: str,
    ) -> tuple[str, str, str]:
        canonical = "|".join(
            [
                symbol,
                side,
                order_type,
                str(quantity),
                str(limit_price or ""),
                str(slice_number),
                str(slice_count),
            ]
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        ticket_id = f"ticket_{digest[:20]}"
        client_order_id = f"{prefix}-{digest[:24]}"
        idempotency_key = digest
        return ticket_id, client_order_id, idempotency_key

    def _split_quantity(
        self, quantity: Decimal, slice_count: int, precision: int
    ) -> list[Decimal]:
        if slice_count <= 0:
            return []
        quantum = Decimal("1").scaleb(-precision)
        base = (quantity / Decimal(slice_count)).quantize(
            quantum, rounding=ROUND_DOWN
        )
        slices = [base for _ in range(slice_count)]
        assigned = sum(slices, Decimal("0"))
        remainder = quantity - assigned
        if slices:
            slices[-1] = (slices[-1] + remainder).quantize(
                quantum, rounding=ROUND_DOWN
            )
        return slices

    def generate(
        self, execution_payload: dict, policy_payload: dict | None = None
    ) -> list[OrderTicket]:
        policy = TicketPolicy.from_mapping(policy_payload)
        tickets: list[OrderTicket] = []

        for plan in execution_payload.get("execution_plans", []):
            if plan.get("blocked", False):
                continue

            symbol = str(plan.get("symbol", "")).upper()
            side = str(plan.get("side", "")).lower()
            order_type = str(plan.get("order_type", "")).lower()
            total_quantity = D(plan.get("quantity"))
            reference_price = D(plan.get("reference_price"))
            limit_price_raw = plan.get("limit_price")
            limit_price = D(limit_price_raw) if limit_price_raw is not None else None
            slice_count = int(plan.get("slice_count", 1))
            quantities = self._split_quantity(
                total_quantity, slice_count, policy.fractional_precision
            )

            for index, quantity in enumerate(quantities, start=1):
                blockers: list[str] = []
                if not symbol:
                    blockers.append("SYMBOL_MISSING")
                if side not in {"buy", "sell"}:
                    blockers.append("INVALID_SIDE")
                if order_type not in {"market", "limit"}:
                    blockers.append("INVALID_ORDER_TYPE")
                if quantity < policy.minimum_quantity:
                    blockers.append("QUANTITY_BELOW_MINIMUM")
                if order_type == "limit" and (limit_price is None or limit_price <= 0):
                    blockers.append("LIMIT_PRICE_REQUIRED")

                price_for_notional = (
                    limit_price if limit_price is not None else reference_price
                )
                estimated_notional = (
                    quantity * price_for_notional
                    if price_for_notional > 0
                    else Decimal("0")
                )
                if estimated_notional > policy.maximum_ticket_notional:
                    blockers.append("MAXIMUM_TICKET_NOTIONAL_EXCEEDED")

                ticket_id, client_order_id, idempotency_key = self._stable_id(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    limit_price=limit_price,
                    slice_number=index,
                    slice_count=slice_count,
                    prefix=policy.client_order_prefix,
                )

                payload = {
                    "symbol": symbol,
                    "qty": format(quantity, "f"),
                    "side": side,
                    "type": order_type,
                    "time_in_force": policy.time_in_force,
                    "client_order_id": client_order_id,
                    "extended_hours": policy.extended_hours,
                }
                if order_type == "limit":
                    payload["limit_price"] = format(limit_price, "f")

                tickets.append(
                    OrderTicket(
                        ticket_id=ticket_id,
                        client_order_id=client_order_id,
                        parent_symbol=symbol,
                        slice_number=index,
                        slice_count=slice_count,
                        payload=payload,
                        estimated_notional=estimated_notional.quantize(
                            Decimal("0.01")
                        ),
                        idempotency_key=idempotency_key,
                        blocked=bool(blockers),
                        blockers=tuple(sorted(set(blockers))),
                    )
                )

        return tickets

    def run_file(
        self, execution_path: Path, policy_path: Path, output_path: Path
    ) -> dict:
        execution_payload = json.loads(execution_path.read_text(encoding="utf-8"))
        policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
        tickets = self.generate(execution_payload, policy_payload)
        ready = [ticket for ticket in tickets if not ticket.blocked]

        payload = {
            "stage": "EXECUTION_PLAN_TO_ORDER_TICKET_GENERATOR_MEGA_BUNDLE",
            "status": "PASS" if ready else "BLOCKED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ticket_count": len(tickets),
            "ready_ticket_count": len(ready),
            "tickets": [ticket.as_json() for ticket in tickets],
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "PAPER_ORDER_SUBMISSION_GATE_AND_RECONCILIATION",
            "next_market_dependent_action": "P3_ACTUAL_PAPER_ORDER_VALIDATION",
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ledger = output_path.parent / "order_ticket_ledger.jsonl"
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload
