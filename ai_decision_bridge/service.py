from __future__ import annotations
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from .candidates import build_candidates, normalize_regime
from .models import BridgeConfig, BridgeResult, SymbolBridgeDecision

class DecisionBridgeService:
    def __init__(self, ensemble=None, risk=None, portfolio=None) -> None:
        if ensemble is None:
            from intelligence_v4.ensemble import StrategyEnsembleV4
            ensemble = StrategyEnsembleV4()
        if risk is None:
            from intelligence_v4.risk import AdaptiveRiskEngineV3
            risk = AdaptiveRiskEngineV3()
        if portfolio is None:
            from intelligence_v4.portfolio import PortfolioIntelligenceV2
            portfolio = PortfolioIntelligenceV2()
        self.ensemble = ensemble
        self.risk = risk
        self.portfolio = portfolio

    def bridge(self, decision_payload: dict, config_payload: dict | None = None) -> BridgeResult:
        cfg = BridgeConfig.from_mapping(config_payload)
        orchestration = decision_payload.get("decision_orchestration", decision_payload)
        regime = normalize_regime(str(orchestration.get("market_regime", "MIXED")))
        decisions = []
        global_blockers = list(orchestration.get("blockers", []))

        for item in orchestration.get("decisions", []):
            if not item.get("selected", False):
                continue
            symbol = str(item["symbol"])
            score = Decimal(str(item.get("composite_score", "0")))
            confidence = Decimal(str(item.get("confidence", "0")))
            desired_weight = Decimal(str(item.get("target_weight", "0")))
            route = str(item.get("strategy_route", "BALANCED_MULTI_FACTOR_ENSEMBLE"))

            ensemble = self.ensemble.decide(
                candidates=build_candidates(route, score, confidence),
                market_regime=regime,
            )
            base_notional = min(
                cfg.maximum_base_notional,
                cfg.portfolio_value * desired_weight,
            )
            risk = self.risk.evaluate(
                symbol=symbol,
                base_notional=base_notional,
                volatility=cfg.default_volatility,
                sector_exposure=cfg.current_sector_exposure,
                portfolio_exposure=cfg.current_portfolio_exposure,
                drawdown_ratio=cfg.drawdown_ratio,
                consecutive_losses=cfg.consecutive_losses,
                daily_loss_limit_reached=cfg.daily_loss_limit_reached,
                strategy_risk_budget=cfg.strategy_risk_budget,
            )
            portfolio = self.portfolio.allocate(
                symbol=symbol,
                portfolio_value=cfg.portfolio_value,
                current_weight=Decimal("0"),
                desired_weight=desired_weight,
                sector_weight_after=cfg.current_sector_exposure + min(desired_weight, Decimal("0.20")),
                correlated_exposure_after=cfg.correlated_exposure_after,
            )
            blockers = sorted(set(
                list(getattr(ensemble, "blockers", ()))
                + list(getattr(risk, "blockers", ()))
                + list(getattr(portfolio, "blockers", ()))
            ))
            approved_notional = min(
                getattr(risk, "approved_notional", Decimal("0")),
                getattr(portfolio, "target_notional", Decimal("0")),
            )
            approved = not blockers and ensemble.action == "TRADE" and approved_notional > 0
            explanation = list(getattr(ensemble, "explanation", ()))
            explanation.extend([
                f"AI_ROUTE:{route}",
                f"AI_TARGET_WEIGHT:{desired_weight}",
                f"BRIDGE_APPROVED:{approved}",
            ])
            decisions.append(SymbolBridgeDecision(
                symbol=symbol,
                approved=approved,
                strategy_route=route,
                ensemble_action=ensemble.action,
                ensemble_confidence=ensemble.confidence,
                approved_notional=approved_notional if approved else Decimal("0"),
                risk_multiplier=risk.risk_multiplier,
                target_weight=portfolio.target_weight,
                target_notional=portfolio.target_notional,
                rebalance_required=portfolio.rebalance_required,
                blockers=tuple(blockers),
                explanation=tuple(explanation),
            ))

        approved_symbols = tuple(x.symbol for x in decisions if x.approved)
        total = sum((x.approved_notional for x in decisions), Decimal("0"))
        if not decisions: global_blockers.append("NO_SELECTED_AI_DECISIONS")
        if decisions and not approved_symbols: global_blockers.append("NO_BRIDGE_APPROVALS")
        return BridgeResult(
            status="PASS" if approved_symbols and not global_blockers else "BLOCKED",
            decisions=tuple(decisions),
            approved_symbols=approved_symbols,
            total_approved_notional=total,
            blockers=tuple(sorted(set(global_blockers))),
        )

    def run_file(self, decision_path: Path, config_path: Path, output_path: Path) -> dict:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        result = self.bridge(decision, config)
        payload = {
            "stage": "AI_DECISION_TO_STRATEGY_RISK_PORTFOLIO_BRIDGE_MEGA_BUNDLE",
            "status": result.status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "bridge": result.as_json(),
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "AI_APPROVED_DECISION_TO_EXECUTION_PLAN_BRIDGE",
            "next_market_dependent_action": "P3_ACTUAL_PAPER_ORDER_VALIDATION",
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload
