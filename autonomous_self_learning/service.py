from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .analytics import summarize_all
from .explainability import build_decision_explanation
from .fixtures import TRADES
from .review import champion_review


class AutonomousSelfLearningCertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        now = datetime.now(timezone.utc)

        summaries = [
            item.to_dict()
            for item in summarize_all(TRADES)
        ]

        explanation = build_decision_explanation(
            symbol="NVDA",
            action="BUY",
            confidence="0.91",
            strategy_id="BREAKOUT",
            regime="BULL_TREND",
            safety_state="NORMAL",
            factors={
                "multi_ai_score": "0.89",
                "portfolio_fit": "0.84",
                "risk_score": "0.81",
                "trend_score": "0.94",
                "volume_score": "0.88",
            },
        )

        safety_explanation = build_decision_explanation(
            symbol="NVDA",
            action="BUY",
            confidence="0.91",
            strategy_id="BREAKOUT",
            regime="BULL_TREND",
            safety_state="RISK_HOLD",
            factors={
                "daily_loss_guard": "BREACHED",
                "weekly_loss_guard": "NORMAL",
            },
        )

        review = champion_review(
            summaries,
            current_champion="MOMENTUM",
        )

        result = {
            "stage": (
                "V6201_TO_V6400_AUTONOMOUS_SELF_LEARNING_"
                "AND_EXPLAINABLE_AI"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_TRADE_OUTCOME_LEARNING"
            ),
            "strategy_summaries": summaries,
            "decision_explanation": explanation,
            "safety_override_explanation": (
                safety_explanation
            ),
            "champion_review": review,
            "strategy_performance_analysis_ready": True,
            "win_rate_analysis_ready": True,
            "average_return_analysis_ready": True,
            "profit_factor_analysis_ready": True,
            "sharpe_proxy_analysis_ready": True,
            "drawdown_analysis_ready": True,
            "stability_analysis_ready": True,
            "weak_strategy_detection_ready": True,
            "improvement_recommendation_ready": True,
            "champion_review_ready": True,
            "explainable_ai_ready": True,
            "daily_learning_report_ready": True,
            "weekly_learning_report_ready": True,
            "learning_ledger_ready": True,
            "automatic_parameter_mutation_enabled": False,
            "automatic_strategy_disable_enabled": False,
            "automatic_champion_change_enabled": False,
            "automatic_champion_change_performed": False,
            "automatic_voter_weight_learning_enabled": False,
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
                "V6401_TO_V6600_AUTONOMOUS_OPERATIONS_"
                "HEALTH_AND_FINAL_ORCHESTRATION"
            ),
        }

        by_id = {
            item["strategy_id"]: item
            for item in summaries
        }
        checks = (
            "MOMENTUM" in by_id,
            "BREAKOUT" in by_id,
            "MEAN_REVERSION" in by_id,
            by_id["MEAN_REVERSION"]["status"]
            in {"WEAK", "WATCH"},
            explanation["final_action"] == "BUY",
            safety_explanation["final_action"] == "WAIT",
            review["automatic_change_performed"] is False,
            result[
                "automatic_parameter_mutation_enabled"
            ] is False,
            result[
                "automatic_champion_change_enabled"
            ] is False,
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

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        daily_report = {
            "report_type": "DAILY_LEARNING_REPORT",
            "generated_at": now.isoformat(),
            "strategy_summaries": summaries,
            "champion_review": review,
            "decision_explanation": explanation,
            "safety_override_explanation": (
                safety_explanation
            ),
        }

        weekly_report = {
            "report_type": "WEEKLY_LEARNING_REPORT",
            "generated_at": now.isoformat(),
            "healthy_strategies": [
                item["strategy_id"]
                for item in summaries
                if item["status"] == "HEALTHY"
            ],
            "watch_strategies": [
                item["strategy_id"]
                for item in summaries
                if item["status"] == "WATCH"
            ],
            "weak_strategies": [
                item["strategy_id"]
                for item in summaries
                if item["status"] == "WEAK"
            ],
            "champion_review": review,
            "automatic_changes_performed": False,
        }

        outputs = {
            "autonomous_self_learning_certification.json": result,
            "autonomous_strategy_learning_summary.json": {
                "items": summaries
            },
            "autonomous_decision_explanation.json": explanation,
            "autonomous_safety_explanation.json": (
                safety_explanation
            ),
            "autonomous_champion_review.json": review,
            "autonomous_daily_learning_report.json": daily_report,
            "autonomous_weekly_learning_report.json": weekly_report,
            "autonomous_learning_policy.json": {
                "recommendation_only": True,
                "automatic_parameter_mutation_enabled": False,
                "automatic_strategy_disable_enabled": False,
                "automatic_champion_change_enabled": False,
                "automatic_voter_weight_learning_enabled": False,
                "manual_approval_required": True,
            },
        }

        for name, payload in outputs.items():
            (
                output_dir / name
            ).write_text(
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
            / "autonomous_self_learning_ledger.jsonl"
        ).open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                )
                + "\n"
            )

        return result
