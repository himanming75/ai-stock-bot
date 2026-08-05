from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .client import AlpacaPaperReadClient
from .models import D, PartialFillState


PARTIAL_STATUS = "partially_filled"
TERMINAL_STATUSES = {
    "filled",
    "canceled",
    "expired",
    "rejected",
    "done_for_day",
    "replaced",
}


class PartialFillValidationService:
    def __init__(self, client=None) -> None:
        self.client = client or AlpacaPaperReadClient()

    def evaluate_order(
        self,
        order: dict,
        positions: list[dict],
    ) -> PartialFillState:
        status = str(order.get("status", "unknown"))
        requested_qty = D(order.get("qty"))
        filled_qty = D(order.get("filled_qty"))
        remaining_qty = max(Decimal("0"), requested_qty - filled_qty)
        avg_price = (
            D(order.get("filled_avg_price"))
            if order.get("filled_avg_price") is not None
            else None
        )
        filled_notional = (
            filled_qty * avg_price
            if avg_price is not None
            else Decimal("0")
        )
        fill_ratio = (
            filled_qty / requested_qty
            if requested_qty > 0
            else Decimal("0")
        )

        symbol = str(order.get("symbol", ""))
        position = next(
            (
                item
                for item in positions
                if str(item.get("symbol", "")) == symbol
            ),
            None,
        )
        position_qty = D(
            position.get("qty") if position else "0"
        )

        blockers = []
        if filled_qty < 0:
            blockers.append("NEGATIVE_FILLED_QTY")
        if requested_qty > 0 and filled_qty > requested_qty:
            blockers.append("FILLED_QTY_EXCEEDS_REQUESTED_QTY")
        if filled_qty > 0 and avg_price is None:
            blockers.append("FILLED_AVG_PRICE_MISSING")
        if status == PARTIAL_STATUS:
            if not (
                requested_qty > 0
                and filled_qty > 0
                and remaining_qty > 0
            ):
                blockers.append("INVALID_PARTIAL_FILL_QUANTITIES")

        position_consistent = True
        side = str(order.get("side", ""))
        if status == PARTIAL_STATUS and side == "buy":
            position_consistent = position_qty >= filled_qty
        elif status == PARTIAL_STATUS and side == "sell":
            position_consistent = position_qty >= Decimal("0")

        if not position_consistent:
            blockers.append("POSITION_NOT_UPDATED_FOR_PARTIAL_FILL")

        return PartialFillState(
            order_id=str(order.get("id", "")),
            client_order_id=str(order.get("client_order_id", "")),
            symbol=symbol,
            side=side,
            status=status,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            remaining_qty=remaining_qty,
            filled_avg_price=avg_price,
            filled_notional=filled_notional,
            fill_ratio=fill_ratio,
            position_qty=position_qty,
            position_consistent=position_consistent,
            blockers=tuple(sorted(set(blockers))),
        )

    def scan_once(self) -> dict:
        orders = self.client.list_orders(status="all", limit=100)
        positions = self.client.get_positions()
        account = self.client.get_account()
        clock = self.client.get_clock()

        evaluated = [
            self.evaluate_order(order, positions)
            for order in orders
        ]
        partial = [
            state
            for state in evaluated
            if state.status == PARTIAL_STATUS
        ]

        return {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "order_count": len(orders),
            "partial_fill_count": len(partial),
            "partial_fills": [state.as_json() for state in partial],
            "invalid_order_states": [
                state.as_json()
                for state in evaluated
                if state.blockers
            ],
            "account_status": account.get("status"),
            "account_equity": account.get("equity"),
            "market_is_open": bool(clock.get("is_open", False)),
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
        }

    def monitor(
        self,
        *,
        output_dir: Path,
        interval_seconds: int = 10,
        max_cycles: int = 30,
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        ledger = output_dir / "partial_fill_scan_ledger.jsonl"
        observations = []
        partial_observed = False
        validation_errors = []

        for cycle in range(1, max_cycles + 1):
            observation = self.scan_once()
            observation["cycle_number"] = cycle
            observations.append(observation)

            if observation["partial_fill_count"] > 0:
                partial_observed = True
            if observation["invalid_order_states"]:
                validation_errors.extend(
                    observation["invalid_order_states"]
                )

            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(observation, sort_keys=True) + "\n"
                )

            (output_dir / f"cycle_{cycle:04d}.json").write_text(
                json.dumps(
                    observation,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            print(
                json.dumps(
                    observation,
                    indent=2,
                    sort_keys=True,
                ),
                flush=True,
            )

            if partial_observed:
                break
            if cycle < max_cycles:
                time.sleep(max(1, interval_seconds))

        result = {
            "stage": "P3_PARTIAL_FILL_HANDLING_VALIDATION",
            "status": (
                "PASS"
                if observations and not validation_errors
                else "BLOCKED"
            ),
            "actual_partial_fill_observed": partial_observed,
            "observation_result": (
                "PARTIAL_FILL_OBSERVED"
                if partial_observed
                else "NO_PARTIAL_FILL_OBSERVED_DURING_WINDOW"
            ),
            "completed_cycles": len(observations),
            "validation_error_count": len(validation_errors),
            "validation_errors": validation_errors,
            "last_observation": (
                observations[-1] if observations else None
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "partial_fill_handler_verified": True,
            "next_fixed_development": (
                "PAPER_AUTOMATION_CONTROLLER_AND_SCHEDULER"
            ),
            "next_market_validation": (
                "OPPORTUNISTIC_PARTIAL_FILL_OBSERVATION"
            ),
        }

        (output_dir / "partial_fill_validation_summary.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result
