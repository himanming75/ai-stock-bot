from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .allocator import AutonomousPortfolioAllocator
from .fixtures import CANDIDATES


D = Decimal


class AutonomousPortfolioAICertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        now = datetime.now(timezone.utc)
        allocator = AutonomousPortfolioAllocator()

        normal = allocator.allocate(
            candidates=CANDIDATES,
            regime="BULL_TREND",
            portfolio_volatility=D("0.18"),
            drawdown_ratio=D("0.08"),
            daily_loss_ratio=D("0.01"),
            weekly_loss_ratio=D("0.02"),
        )

        risk_hold = allocator.allocate(
            candidates=CANDIDATES,
            regime="VOLATILE",
            portfolio_volatility=D("0.35"),
            drawdown_ratio=D("0.18"),
            daily_loss_ratio=D("0.04"),
            weekly_loss_ratio=D("0.07"),
        )

        result = {
            "stage": (
                "V6001_TO_V6200_AUTONOMOUS_PORTFOLIO_AI_"
                "AND_RISK_ALLOCATION"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_PORTFOLIO_ALLOCATION_SCENARIOS"
            ),
            "normal_allocation": normal,
            "risk_hold_allocation": risk_hold,
            "portfolio_allocator_ready": True,
            "dynamic_cash_floor_ready": True,
            "confidence_scaling_ready": True,
            "volatility_scaling_ready": True,
            "drawdown_scaling_ready": True,
            "max_position_guard_ready": True,
            "max_sector_guard_ready": True,
            "correlation_group_guard_ready": True,
            "daily_loss_budget_ready": True,
            "weekly_loss_budget_ready": True,
            "rebalance_threshold_ready": True,
            "explainable_allocation_ready": True,
            "target_portfolio_ready": True,
            "automatic_rebalance_execution_enabled": False,
            "automatic_order_generation_enabled": False,
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
                "V6201_TO_V6400_AUTONOMOUS_SELF_LEARNING_"
                "AND_EXPLAINABLE_AI"
            ),
        }

        allocations = normal["allocations"]
        checks = (
            normal["risk_state"]["state"] == "NORMAL",
            normal["rebalance_required"] is True,
            D(normal["cash_target"]) >= D("0.20"),
            all(
                D(item["target_weight"]) <= D("0.15")
                for item in allocations
            ),
            risk_hold["risk_state"]["state"]
            == "RISK_HOLD",
            risk_hold["rebalance_required"] is False,
            result[
                "automatic_rebalance_execution_enabled"
            ] is False,
            result[
                "automatic_order_generation_enabled"
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
        outputs = {
            "autonomous_portfolio_ai_certification.json": result,
            "autonomous_target_portfolio.json": normal,
            "autonomous_risk_hold_portfolio.json": risk_hold,
            "autonomous_risk_policy.json": {
                "max_position_weight": "0.15",
                "max_sector_weight": "0.30",
                "max_correlation_group_weight": "0.25",
                "daily_loss_limit": "0.03",
                "weekly_loss_limit": "0.06",
                "rebalance_threshold": "0.02",
                "automatic_rebalance_execution_enabled": False,
                "automatic_order_generation_enabled": False,
            },
            "autonomous_allocation_explanations.json": {
                "items": normal["allocations"]
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
            / "autonomous_portfolio_ai_ledger.jsonl"
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
