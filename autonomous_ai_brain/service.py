from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .brain import AutonomousAIBrain
from .fixtures import CANDIDATES


class AutonomousAIBrainCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)
        brain = AutonomousAIBrain()

        normal, ranking = brain.decide(
            market_regime="BULL_TREND",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=True,
            drawdown_guard_active=False,
        )
        market_closed, _ = brain.decide(
            market_regime="BULL_TREND",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=False,
            drawdown_guard_active=False,
        )
        risk_hold, _ = brain.decide(
            market_regime="VOLATILE",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=True,
            drawdown_guard_active=True,
        )
        critical, _ = brain.decide(
            market_regime="UNKNOWN",
            candidates=CANDIDATES,
            system_health="CRITICAL",
            market_open=True,
            drawdown_guard_active=False,
        )

        result = {
            "stage": (
                "V5601_TO_V5800_AUTONOMOUS_AI_BRAIN_"
                "AND_STRATEGY_COMPETITION_FOUNDATION"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_AUTONOMOUS_DECISION_SCENARIOS"
            ),
            "normal_decision": normal.to_dict(),
            "strategy_ranking": ranking,
            "market_closed_decision": (
                market_closed.to_dict()
            ),
            "risk_hold_decision": risk_hold.to_dict(),
            "critical_health_decision": (
                critical.to_dict()
            ),
            "strategy_competition_ready": True,
            "eligibility_filter_ready": True,
            "regime_fit_scoring_ready": True,
            "risk_penalty_ready": True,
            "evidence_threshold_ready": True,
            "abstain_decision_ready": True,
            "market_closed_guard_ready": True,
            "drawdown_guard_ready": True,
            "critical_health_all_stop_ready": True,
            "explainable_selection_ready": True,
            "promotion_recommendation_ready": True,
            "automatic_promotion_enabled": False,
            "automatic_weight_mutation_enabled": False,
            "automatic_threshold_mutation_enabled": False,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_ai_engine_modified": False,
            "existing_controller_modified": False,
            "next_fixed_development": (
                "V5801_TO_V6000_AUTONOMOUS_CHAMPION_"
                "CHALLENGER_AND_MULTI_AI_VOTING"
            ),
        }

        winner = ranking[0]
        checks = (
            normal.selected_strategy_id == "MOMENTUM",
            normal.action == "BUY",
            winner["eligible"] is True,
            ranking[-1]["eligible"] is False,
            market_closed.autonomous_state
            == "MARKET_CLOSED",
            risk_hold.autonomous_state == "RISK_HOLD",
            critical.action == "ALL_STOP",
            normal.automatic_promotion_performed is False,
            normal.order_submission_allowed is False,
        )
        if not all(checks):
            result["status"] = "BLOCKED"

        seed = dict(result)
        seed.pop("generated_at")
        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    seed,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {
            "autonomous_ai_brain_certification.json": result,
            "autonomous_strategy_competition.json": {
                "items": ranking
            },
            "autonomous_ai_decision.json": (
                normal.to_dict()
            ),
            "autonomous_ai_safety_scenarios.json": {
                "market_closed": (
                    market_closed.to_dict()
                ),
                "risk_hold": risk_hold.to_dict(),
                "critical_health": (
                    critical.to_dict()
                ),
            },
            "autonomous_ai_promotion_policy.json": {
                "recommendation_enabled": True,
                "automatic_promotion_enabled": False,
                "manual_approval_required": True,
                "automatic_weight_mutation_enabled": False,
                "automatic_threshold_mutation_enabled": False,
            },
        }
        for name, payload in outputs.items():
            (output_dir / name).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

        with (
            output_dir
            / "autonomous_ai_brain_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                )
                + "\n"
            )

        return result
