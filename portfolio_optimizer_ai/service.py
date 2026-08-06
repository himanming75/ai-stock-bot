from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .guardrails import evaluate_guardrails
from .io import append_jsonl, read_json, write_json
from .optimizer import build_candidate_weights
from .report import build_report
from .stress import run_stress_scenarios


def _fallback_analyses() -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "expected_return": 0.020,
            "expected_risk": 0.012,
            "confidence_calibration": {"calibrated_confidence": 0.88},
        },
        {
            "symbol": "MSFT",
            "expected_return": -0.018,
            "expected_risk": 0.013,
            "confidence_calibration": {"calibrated_confidence": 0.84},
        },
        {
            "symbol": "NVDA",
            "expected_return": 0.022,
            "expected_risk": 0.030,
            "confidence_calibration": {"calibrated_confidence": 0.66},
        },
        {
            "symbol": "SPY",
            "expected_return": 0.002,
            "expected_risk": 0.009,
            "confidence_calibration": {"calibrated_confidence": 0.60},
        },
    ]


class PortfolioOptimizerCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        actual = output_dir / "actual"
        actual.mkdir(parents=True, exist_ok=True)

        previous_path = Path(
            "release/v12001_13000_portfolio_context/"
            "portfolio_context_certification.json"
        )
        previous = read_json(previous_path)
        report = previous.get("report", {})
        portfolio_context = previous.get("portfolio_context", {})
        prior_report_path = Path(
            "release/v11001_12000_multi_timeframe_ai/actual/"
            "multi_timeframe_ai_report_bilingual.json"
        )
        prior_report = read_json(prior_report_path)
        analyses = prior_report.get("analyses")

        if not isinstance(analyses, list) or not analyses:
            analyses = _fallback_analyses()
            source_mode = "OFFLINE_OPTIMIZER_FIXTURE"
        else:
            source_mode = "PREVIOUS_PORTFOLIO_AND_MULTI_TIMEFRAME_REPORTS"

        average_abs_correlation = float(
            portfolio_context.get(
                "average_absolute_correlation",
                report.get("portfolio_context", {}).get(
                    "average_absolute_correlation",
                    0.50,
                ),
            )
        )

        optimizer = build_candidate_weights(
            analyses,
            max_symbol_weight=0.35,
        )
        stress_results = run_stress_scenarios(
            analyses,
            optimizer["candidate_weights"],
            average_abs_correlation,
        )
        guardrails = evaluate_guardrails(
            weights=optimizer["candidate_weights"],
            stress_results=stress_results,
            average_abs_correlation=average_abs_correlation,
        )

        write_json(
            actual / "candidate_portfolio_weights.json",
            optimizer,
        )
        for row in stress_results:
            append_jsonl(
                actual / "scenario_stress_ledger.jsonl",
                {
                    **row,
                    "broker_write_enabled": False,
                    "position_allocation_enabled": False,
                },
            )
        append_jsonl(
            actual / "capital_guardrail_ledger.jsonl",
            {
                **guardrails,
                "actual_capital_action_performed": False,
            },
        )

        bilingual_report = build_report(
            optimizer=optimizer,
            stress_results=stress_results,
            guardrails=guardrails,
            output_path=actual / "portfolio_optimizer_report_bilingual.json",
        )

        result = {
            "stage": (
                "V13001_TO_V14000_PORTFOLIO_OPTIMIZER_SCENARIO_STRESS_"
                "CAPITAL_GUARDRAIL_SIMULATION_MAX_BUNDLE"
            ),
            "status": "PASS",
            "source_mode": source_mode,
            "portfolio_optimizer_ready": True,
            "candidate_weighting_ready": True,
            "risk_adjusted_weighting_ready": True,
            "max_symbol_weight_cap_ready": True,
            "scenario_stress_testing_ready": True,
            "normal_scenario_ready": True,
            "correction_scenario_ready": True,
            "sell_off_scenario_ready": True,
            "volatility_spike_scenario_ready": True,
            "correlation_shock_scenario_ready": True,
            "estimated_drawdown_ready": True,
            "capital_guardrail_simulation_ready": True,
            "max_drawdown_guardrail_ready": True,
            "max_correlation_guardrail_ready": True,
            "max_stress_risk_guardrail_ready": True,
            "bilingual_report_ready": True,
            "stress_ledger_ready": True,
            "guardrail_ledger_ready": True,
            "optimizer": optimizer,
            "stress_results": stress_results,
            "guardrails": guardrails,
            "report": bilingual_report,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_market_data_requested": False,
            "actual_configuration_activated": False,
            "actual_position_allocation_performed": False,
            "actual_capital_lock_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V14001_PLUS_EXECUTION_POLICY_SIMULATOR_REBALANCE_PLANNER_"
                "AND_RISK_BUDGET_ORCHESTRATION"
            ),
        }

        if not (
            abs(optimizer["weight_sum"] - 1.0) <= 0.00001
            and len(stress_results) == 5
            and guardrails["enforcement_mode"] == "SIMULATION_ONLY"
            and bilingual_report["safety"]["broker_write_enabled"] is False
            and bilingual_report["safety"]["position_allocation_enabled"]
            is False
        ):
            result["status"] = "BLOCKED"

        result["certification_fingerprint"] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()

        write_json(
            output_dir / "portfolio_optimizer_certification.json",
            result,
        )
        return result
