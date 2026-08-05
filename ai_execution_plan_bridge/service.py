from __future__ import annotations
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from .models import ExecutionBridgeConfig, ExecutionBridgeDecision

class ExecutionPlanBridgeService:
    def __init__(self, execution_engine=None) -> None:
        if execution_engine is None:
            from intelligence_v4.execution import ExecutionIntelligenceV2
            execution_engine = ExecutionIntelligenceV2()
        self.execution_engine = execution_engine

    def build(self, bridge_payload: dict, config_payload: dict) -> list[ExecutionBridgeDecision]:
        config = ExecutionBridgeConfig.from_mapping(config_payload)
        bridge = bridge_payload.get("bridge", bridge_payload)
        decisions = []

        for item in bridge.get("decisions", []):
            if not item.get("approved", False):
                continue

            symbol = str(item["symbol"]).upper()
            approved_notional = Decimal(str(item.get("approved_notional", "0")))
            reference_price = config.default_reference_prices.get(symbol, Decimal("0"))
            blockers = []

            if reference_price <= 0:
                blockers.append("REFERENCE_PRICE_MISSING")
                quantity = Decimal("0")
            else:
                quantity = approved_notional / reference_price
                if config.allow_fractional:
                    quantity = quantity.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)
                else:
                    quantity = quantity.quantize(Decimal("1"), rounding=ROUND_DOWN)

            plan = self.execution_engine.plan(
                symbol=symbol,
                side="buy",
                quantity=quantity,
                reference_price=reference_price,
                spread_bps=config.spread_bps,
                volatility=config.volatility,
                urgency=config.urgency,
                maximum_order_notional=config.maximum_order_notional,
            )

            merged = tuple(sorted(set(blockers + list(plan.blockers))))
            decisions.append(
                ExecutionBridgeDecision(
                    symbol=symbol,
                    approved_notional=approved_notional,
                    reference_price=reference_price,
                    quantity=quantity,
                    side=plan.side,
                    order_type=plan.order_type,
                    slice_count=plan.slice_count,
                    limit_price=plan.limit_price,
                    expected_slippage_bps=plan.expected_slippage_bps,
                    time_limit_seconds=plan.time_limit_seconds,
                    blocked=bool(merged),
                    blockers=merged,
                )
            )
        return decisions

    def run_file(self, bridge_path: Path, config_path: Path, output_path: Path) -> dict:
        bridge_payload = json.loads(bridge_path.read_text(encoding="utf-8"))
        config_payload = json.loads(config_path.read_text(encoding="utf-8"))
        decisions = self.build(bridge_payload, config_payload)
        ready = [x for x in decisions if not x.blocked]

        payload = {
            "stage": "AI_APPROVED_DECISION_TO_EXECUTION_PLAN_BRIDGE_MEGA_BUNDLE",
            "status": "PASS" if ready else "BLOCKED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "execution_plans": [x.as_json() for x in decisions],
            "ready_symbols": [x.symbol for x in ready],
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "EXECUTION_PLAN_TO_ORDER_TICKET_GENERATOR",
            "next_market_dependent_action": "P3_ACTUAL_PAPER_ORDER_VALIDATION",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return payload
