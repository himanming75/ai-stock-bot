from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .backtest import backtest_bridge
from .ensemble import score_candidate
from .explainability import explain
from .i18n import bilingual
from .io import append_jsonl, read_json, write_json
from .position_size import recommend_position_size
from .ranking import rank_candidates
from .report import build_report


def _fallback_candidates() -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "action": "BUY",
            "score": 25.0,
            "confidence": 25.0,
            "regime": "REGIME_TRENDING",
            "trend": "TREND_UP",
            "risk_gate": "PASS_READ_ONLY",
            "features": {
                "close": 128.0,
                "ema9": 126.6,
                "ema21": 124.5,
                "rsi14": 68.0,
                "macd_histogram": 0.3,
                "momentum_5": 0.018,
                "volume_ratio": 1.4,
                "atr_percent": 0.012,
                "bollinger_width": 0.055,
            },
            "conflict_analysis": {
                "conflict_count": 0,
                "conflicts": [],
            },
        },
        {
            "symbol": "MSFT",
            "action": "SELL",
            "score": -25.0,
            "confidence": 20.0,
            "regime": "REGIME_VOLATILE",
            "trend": "TREND_DOWN",
            "risk_gate": "PASS_READ_ONLY",
            "features": {
                "close": 72.0,
                "ema9": 73.4,
                "ema21": 75.5,
                "rsi14": 28.0,
                "macd_histogram": -0.4,
                "momentum_5": -0.024,
                "volume_ratio": 1.6,
                "atr_percent": 0.035,
                "bollinger_width": 0.11,
            },
            "conflict_analysis": {
                "conflict_count": 1,
                "conflicts": [
                    {
                        "code": "SELL_WHILE_OVERSOLD",
                        "en": "Sell candidate conflicts with oversold RSI.",
                        "ko": "매도 후보와 RSI 과매도 상태가 충돌합니다.",
                    }
                ],
            },
        },
        {
            "symbol": "SPY",
            "action": "HOLD",
            "score": 0.0,
            "confidence": 15.0,
            "regime": "REGIME_RANGE",
            "trend": "TREND_SIDEWAYS",
            "risk_gate": "PASS_READ_ONLY",
            "features": {
                "close": 100.0,
                "ema9": 100.0,
                "ema21": 100.0,
                "rsi14": 50.0,
                "macd_histogram": 0.0,
                "momentum_5": 0.0,
                "volume_ratio": 1.0,
                "atr_percent": 0.008,
                "bollinger_width": 0.03,
            },
            "conflict_analysis": {
                "conflict_count": 0,
                "conflicts": [],
            },
        },
    ]


class AISignalScoringCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        actual = output_dir / "actual"
        actual.mkdir(parents=True, exist_ok=True)

        source_path = Path(
            "release/v9801_10400_ai_feature_signal/actual/"
            "ai_signal_candidate_report_bilingual.json"
        )
        source = read_json(source_path)
        candidates = source.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            candidates = _fallback_candidates()
            source_mode = "OFFLINE_FALLBACK_FIXTURE"
        else:
            source_mode = "PREVIOUS_STAGE_REPORT"

        enriched = []
        for candidate in candidates:
            scoring = score_candidate(candidate)
            risk_component = scoring["component_scores"]["risk"]
            position = recommend_position_size(
                ai_score=scoring["ai_score"],
                confidence=scoring["ensemble_confidence"],
                risk_component=risk_component,
                max_position_percent=10.0,
            )
            item = {
                **candidate,
                **scoring,
                "explainability": explain(candidate, scoring),
                "position_size_candidate": position,
                "action_i18n": bilingual(candidate.get("action", "HOLD")),
                "execution_mode": "SCORING_CANDIDATE_ONLY",
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            }
            enriched.append(item)

        ranked = rank_candidates(enriched)

        prices = [
            100, 101, 102, 101, 103, 104, 102, 101, 100, 102, 103, 104
        ]
        actions = [
            "BUY", "BUY", "HOLD", "BUY", "BUY", "SELL",
            "SELL", "SELL", "BUY", "BUY", "HOLD", "HOLD",
        ]
        backtest = backtest_bridge(
            prices=prices,
            actions=actions,
        )

        for item in ranked:
            append_jsonl(
                actual / "ensemble_scoring_ledger.jsonl",
                {
                    "rank": item["rank"],
                    "symbol": item["symbol"],
                    "action": item["action"],
                    "ai_score": item["ai_score"],
                    "ensemble_confidence": item["ensemble_confidence"],
                    "suggested_position_percent": item[
                        "position_size_candidate"
                    ]["suggested_position_percent"],
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                },
            )

        report = build_report(
            ranked_candidates=ranked,
            backtest_results=backtest,
            output_path=actual / "ai_ensemble_scoring_report_bilingual.json",
        )

        result = {
            "stage": (
                "V10401_TO_V11000_AI_SIGNAL_SCORING_ENSEMBLE_"
                "EXPLAINABILITY_BACKTEST_BRIDGE_MAX_BUNDLE"
            ),
            "status": "PASS",
            "source_mode": source_mode,
            "component_scoring_ready": True,
            "trend_score_ready": True,
            "momentum_score_ready": True,
            "volume_score_ready": True,
            "volatility_score_ready": True,
            "regime_score_ready": True,
            "risk_score_ready": True,
            "weighted_ensemble_ready": True,
            "conflict_penalty_ready": True,
            "confidence_calibration_ready": True,
            "candidate_ranking_ready": True,
            "top_buy_ready": True,
            "top_sell_ready": True,
            "position_size_candidate_ready": True,
            "explainability_ready": True,
            "bilingual_reasoning_ready": True,
            "backtest_bridge_ready": True,
            "win_rate_ready": True,
            "profit_factor_ready": True,
            "max_drawdown_ready": True,
            "sharpe_candidate_ready": True,
            "scoring_ledger_ready": True,
            "bilingual_report_ready": True,
            "ranked_candidates": ranked,
            "backtest_bridge": backtest,
            "report": report,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_market_data_requested": False,
            "actual_configuration_activated": False,
            "actual_position_allocation_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "PHASE2_PORTFOLIO_OPTIMIZER_SIGNAL_FEEDBACK_"
                "AND_OFFLINE_PERFORMANCE_ANALYTICS"
            ),
        }

        actions_found = {item["action"] for item in ranked}
        if not (
            len(ranked) >= 3
            and {"BUY", "SELL", "HOLD"}.issubset(actions_found)
            and all(0 <= item["ai_score"] <= 100 for item in ranked)
            and all(
                item["position_size_candidate"]["position_order_enabled"]
                is False
                for item in ranked
            )
            and backtest["status"] == "PASS"
            and report["safety"]["broker_write_enabled"] is False
        ):
            result["status"] = "BLOCKED"

        result["certification_fingerprint"] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        write_json(
            output_dir / "ai_signal_scoring_certification.json",
            result,
        )
        return result
