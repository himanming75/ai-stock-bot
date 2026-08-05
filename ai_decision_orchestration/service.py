from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .allocation import allocate
from .models import DecisionPolicy, OrchestrationResult, SymbolDecision
from .policy import DecisionPolicyGate
from .routing import choose_strategy_route


class AIDecisionOrchestrationService:
    def __init__(self) -> None:
        self.policy_gate = DecisionPolicyGate()

    def orchestrate(self, market_payload: dict, policy_payload: dict | None = None) -> OrchestrationResult:
        policy = DecisionPolicy.from_mapping(policy_payload)
        context = market_payload.get("market_context", market_payload)
        regime = str(context.get("market_regime", "UNKNOWN"))
        risk_mode = str(context.get("risk_mode", "RISK_OFF"))
        ranked = list(context.get("ranked_symbols", []))
        global_blockers = list(context.get("blockers", []))
        warnings = list(context.get("warnings", []))

        eligible: list[dict] = []
        evaluations: dict[str, tuple[list[str], list[str]]] = {}
        for item in ranked:
            reasons, blockers = self.policy_gate.evaluate_symbol(item, policy, risk_mode)
            evaluations[str(item["symbol"])] = (reasons, blockers)
            if not blockers:
                eligible.append(item)

        eligible = sorted(
            eligible,
            key=lambda x: (
                Decimal(str(x.get("composite_score", "0"))),
                Decimal(str(x.get("confidence", "0"))),
                str(x.get("symbol", "")),
            ),
            reverse=True,
        )[: policy.maximum_symbols]

        allocations = allocate(eligible, policy, risk_mode)
        selected_symbols = tuple(str(x["symbol"]) for x in eligible)
        decisions: list[SymbolDecision] = []

        for item in ranked:
            symbol = str(item["symbol"])
            reasons, blockers = evaluations[symbol]
            selected = symbol in selected_symbols
            rank = selected_symbols.index(symbol) + 1 if selected else None
            if selected:
                reasons = sorted(set(reasons + ["SELECTED_BY_AI_ORCHESTRATOR"]))
            else:
                blockers = sorted(set(blockers + ["NOT_SELECTED"]))
            decisions.append(
                SymbolDecision(
                    symbol=symbol,
                    selected=selected,
                    rank=rank,
                    composite_score=Decimal(str(item.get("composite_score", "0"))),
                    confidence=Decimal(str(item.get("confidence", "0"))),
                    trade_bias=str(item.get("trade_bias", "BLOCKED")),
                    target_weight=allocations.get(symbol, Decimal("0")),
                    strategy_route=choose_strategy_route(item, regime),
                    risk_mode=risk_mode,
                    reason_codes=tuple(reasons),
                    blockers=tuple(blockers),
                )
            )

        if not selected_symbols:
            global_blockers.append("NO_SYMBOLS_SELECTED")
        portfolio_weight = sum(allocations.values(), Decimal("0"))
        status = "PASS" if selected_symbols and not global_blockers else "BLOCKED"
        return OrchestrationResult(
            status=status,
            market_regime=regime,
            risk_mode=risk_mode,
            selected_symbols=selected_symbols,
            decisions=tuple(decisions),
            portfolio_weight=portfolio_weight,
            blockers=tuple(sorted(set(global_blockers))),
            warnings=tuple(sorted(set(warnings))),
        )

    def run_file(self, market_path: Path, policy_path: Path, output_path: Path) -> dict:
        market_payload = json.loads(market_path.read_text(encoding="utf-8"))
        policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
        result = self.orchestrate(market_payload, policy_payload)
        payload = {
            "stage": "AI_SYMBOL_SELECTION_AND_DECISION_ORCHESTRATION_MEGA_BUNDLE",
            "status": result.status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "decision_orchestration": result.as_json(),
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "AI_DECISION_TO_STRATEGY_RISK_PORTFOLIO_BRIDGE",
            "next_market_dependent_action": "P3_ACTUAL_PAPER_ORDER_VALIDATION",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload
