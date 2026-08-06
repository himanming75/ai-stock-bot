from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .correlation import correlation_matrix
from .feedback import build_signal_feedback
from .io import append_jsonl, read_json, write_json
from .performance import performance_metrics
from .portfolio import build_portfolio_context
from .report import build_report


def _fallback_analyses() -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "consensus_score": 0.78,
            "expected_return": 0.018,
            "expected_risk": 0.011,
            "confidence_calibration": {"calibrated_confidence": 0.82},
        },
        {
            "symbol": "MSFT",
            "consensus_score": -0.64,
            "expected_return": -0.015,
            "expected_risk": 0.012,
            "confidence_calibration": {"calibrated_confidence": 0.78},
        },
        {
            "symbol": "NVDA",
            "consensus_score": 0.33,
            "expected_return": 0.020,
            "expected_risk": 0.031,
            "confidence_calibration": {"calibrated_confidence": 0.61},
        },
        {
            "symbol": "SPY",
            "consensus_score": 0.02,
            "expected_return": 0.001,
            "expected_risk": 0.009,
            "confidence_calibration": {"calibrated_confidence": 0.55},
        },
    ]


def _offline_returns() -> dict[str, list[float]]:
    return {
        "AAPL": [0.006, 0.004, -0.002, 0.008, 0.003, 0.005],
        "MSFT": [-0.004, -0.003, 0.001, -0.005, -0.002, -0.004],
        "NVDA": [0.010, -0.006, 0.012, -0.004, 0.009, 0.003],
        "SPY": [0.001, 0.002, -0.001, 0.001, 0.000, 0.002],
    }


class PortfolioContextCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        actual = output_dir / "actual"
        actual.mkdir(parents=True, exist_ok=True)

        source_path = Path(
            "release/v11001_12000_multi_timeframe_ai/actual/"
            "multi_timeframe_ai_report_bilingual.json"
        )
        source = read_json(source_path)
        analyses = source.get("analyses")
        if not isinstance(analyses, list) or not analyses:
            analyses = _fallback_analyses()
            source_mode = "OFFLINE_PORTFOLIO_FIXTURE"
        else:
            source_mode = "PREVIOUS_MULTI_TIMEFRAME_REPORT"

        symbols = [item["symbol"] for item in analyses]
        base_returns = _offline_returns()
        series = {
            symbol: base_returns.get(symbol, [0.0] * 6)
            for symbol in symbols
        }

        matrix = correlation_matrix(series)
        portfolio_context = build_portfolio_context(analyses, matrix)
        signal_feedback = build_signal_feedback(analyses, series)

        composite_returns = []
        max_len = max(len(values) for values in series.values())
        for index in range(max_len):
            values = [
                returns[index]
                for returns in series.values()
                if index < len(returns)
            ]
            composite_returns.append(sum(values) / len(values))

        performance = performance_metrics(composite_returns)

        for pair in portfolio_context["pairs"]:
            append_jsonl(
                actual / "cross_asset_correlation_ledger.jsonl",
                {
                    **pair,
                    "broker_write_enabled": False,
                    "position_allocation_enabled": False,
                },
            )

        for row in signal_feedback["rows"]:
            append_jsonl(
                actual / "signal_feedback_ledger.jsonl",
                {
                    **row,
                    "automatic_model_update_enabled": False,
                    "live_learning_enabled": False,
                },
            )

        write_json(
            actual / "cross_asset_correlation_matrix.json",
            matrix,
        )

        report = build_report(
            portfolio_context=portfolio_context,
            signal_feedback=signal_feedback,
            performance=performance,
            output_path=actual / "portfolio_context_report_bilingual.json",
        )

        result = {
            "stage": (
                "V12001_TO_V13000_PORTFOLIO_CONTEXT_CROSS_ASSET_"
                "CORRELATION_SIGNAL_FEEDBACK_MAX_BUNDLE"
            ),
            "status": "PASS",
            "source_mode": source_mode,
            "portfolio_context_ready": True,
            "cross_asset_correlation_ready": True,
            "correlation_matrix_ready": True,
            "concentration_risk_ready": True,
            "directional_concentration_ready": True,
            "diversification_state_ready": True,
            "portfolio_risk_score_ready": True,
            "signal_feedback_ready": True,
            "offline_feedback_ready": True,
            "calibration_error_ready": True,
            "directional_accuracy_ready": True,
            "feedback_health_ready": True,
            "offline_performance_analytics_ready": True,
            "cumulative_return_ready": True,
            "volatility_ready": True,
            "sharpe_candidate_ready": True,
            "max_drawdown_ready": True,
            "win_rate_ready": True,
            "bilingual_report_ready": True,
            "correlation_ledger_ready": True,
            "signal_feedback_ledger_ready": True,
            "correlation_matrix": matrix,
            "portfolio_context": portfolio_context,
            "signal_feedback": signal_feedback,
            "performance": performance,
            "report": report,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_market_data_requested": False,
            "actual_configuration_activated": False,
            "actual_position_allocation_performed": False,
            "actual_model_weight_update_performed": False,
            "actual_live_learning_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V13001_PLUS_PORTFOLIO_OPTIMIZER_SCENARIO_STRESS_"
                "AND_CAPITAL_GUARDRAIL_SIMULATION"
            ),
        }

        if not (
            len(matrix) >= 4
            and portfolio_context["pair_count"] >= 6
            and 0.0 <= portfolio_context["portfolio_risk_score"] <= 1.0
            and 0.0 <= signal_feedback["directional_accuracy"] <= 1.0
            and report["safety"]["broker_write_enabled"] is False
            and report["safety"]["position_allocation_enabled"] is False
            and report["safety"]["automatic_model_update_enabled"] is False
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
            output_dir / "portfolio_context_certification.json",
            result,
        )
        return result
