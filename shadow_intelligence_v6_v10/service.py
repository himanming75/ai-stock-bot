from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ShadowIntelligencePack:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    @staticmethod
    def _load_jsonl(path: Path, limit: int = 5000) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines()[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        rows.append(payload)
                except Exception:
                    continue
        except Exception:
            return []
        return rows

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _v2(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/ai_intelligence_safety_v2/"
              "latest_intelligence_report.json"
        )

    def _v3(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/ai_market_memory_v3/"
              "latest_market_memory_report.json"
        )

    def _v4(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/closed_trade_calibration_v4/"
              "latest_calibration_report.json"
        )

    def _v5(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/ai_strategy_ensemble_v5/"
              "latest_ensemble_report.json"
        )

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    def candidate(self) -> dict[str, Any]:
        candidate = self._guard().get("candidate", {})
        if not candidate:
            candidate = self._v5().get("candidate", {})
        return {
            "symbol": str(candidate.get("symbol", "")).upper(),
            "side": str(candidate.get("side", "HOLD")).upper(),
            "confidence": self._float(candidate.get("confidence")),
            "consensus_score": self._float(candidate.get("consensus_score")),
            "reward_risk": self._float(candidate.get("reward_risk")),
            "quantity": self._float(candidate.get("quantity")),
            "reference_price": self._float(candidate.get("reference_price")),
        }

    def multi_timeframe(self) -> dict[str, Any]:
        v2 = self._v2()
        v5 = self._v5()
        multi = v2.get("multi_score", {})
        ensemble = v5.get("ensemble", {})

        trend = self._float(multi.get("trend_score"), 0.5)
        momentum = self._float(multi.get("momentum_score"), 0.5)
        breakout = self._float(multi.get("breakout_score"), 0.5)
        weighted = self._float(ensemble.get("weighted_score"), 0.5)

        frames = {
            "1m": round(min(max(momentum, 0.0), 1.0), 6),
            "5m": round(min(max((momentum + breakout) / 2.0, 0.0), 1.0), 6),
            "15m": round(min(max((trend + momentum) / 2.0, 0.0), 1.0), 6),
            "1h": round(min(max((trend + weighted) / 2.0, 0.0), 1.0), 6),
        }

        bullish = sum(1 for score in frames.values() if score >= 0.70)
        bearish = sum(1 for score in frames.values() if score < 0.45)

        if bullish >= 3:
            alignment = "BULLISH_ALIGNMENT"
        elif bearish >= 2:
            alignment = "BEARISH_ALIGNMENT"
        else:
            alignment = "MIXED_ALIGNMENT"

        return {
            "timeframes": frames,
            "bullish_timeframes": bullish,
            "bearish_timeframes": bearish,
            "alignment": alignment,
            "enforced": False,
            "order_effect": "NONE",
            "source": "DERIVED_FROM_EXISTING_SHADOW_SIGNALS",
        }

    def market_regime(self) -> dict[str, Any]:
        v2 = self._v2()
        regime = v2.get("market_regime", {})
        multi = v2.get("multi_score", {})

        regime_fit = self._float(regime.get("market_regime_fit"), 0.5)
        vol = self._float(regime.get("volatility_risk"), 0.5)
        trend = self._float(multi.get("trend_score"), 0.5)

        if vol >= 0.85:
            label = "EXTREME_VOLATILITY"
        elif vol >= 0.70:
            label = "HIGH_VOLATILITY"
        elif trend >= 0.80 and regime_fit >= 0.65:
            label = "TRENDING_BULL"
        elif trend < 0.40 and regime_fit < 0.45:
            label = "WEAK_OR_BEARISH"
        elif 0.45 <= trend <= 0.65:
            label = "SIDEWAYS"
        else:
            label = "UNCERTAIN"

        recommended_bias = {
            "TRENDING_BULL": "FAVOR_TREND_AND_MOMENTUM",
            "SIDEWAYS": "FAVOR_MEAN_REVERSION_AND_SKIP_BREAKOUT",
            "HIGH_VOLATILITY": "REDUCE_RISK_AND_REQUIRE_STRONGER_CONFIRMATION",
            "EXTREME_VOLATILITY": "AVOID_NEW_ENTRIES",
            "WEAK_OR_BEARISH": "DEFENSIVE_OR_NO_TRADE",
            "UNCERTAIN": "WAIT_FOR_ALIGNMENT",
        }[label]

        return {
            "label": label,
            "market_regime_fit": regime_fit,
            "volatility_risk": vol,
            "trend_score": trend,
            "recommended_bias": recommended_bias,
            "enforced": False,
            "strategy_weights_changed": False,
        }

    def position_quality(self) -> dict[str, Any]:
        guard = self._guard()
        v3 = self._v3()
        candidate = self.candidate()
        risk = guard.get("risk_snapshot", {})
        exit_data = v3.get("exit_intelligence", {})

        exposure = self._float(risk.get("symbol_exposure"))
        daily_pnl = self._float(risk.get("daily_pnl"))
        open_positions = int(self._float(risk.get("open_positions")))
        max_exposure = self._float(
            guard.get("policy", {}).get("maximum_symbol_exposure"), 500.0
        )

        exposure_ratio = (
            exposure / max_exposure if max_exposure > 0 else 0.0
        )

        flags: list[str] = []
        if exposure_ratio > 1.0:
            flags.append("OVER_SYMBOL_EXPOSURE")
        if open_positions >= int(
            self._float(
                guard.get("policy", {}).get("maximum_open_positions"), 2
            )
        ):
            flags.append("OPEN_POSITION_LIMIT_REACHED")
        if daily_pnl < 0:
            flags.append("NEGATIVE_DAILY_PNL")
        if candidate["symbol"]:
            flags.append("ACTIVE_CANDIDATE_OR_POSITION")

        if "OVER_SYMBOL_EXPOSURE" in flags:
            grade = "D"
            action = "REVIEW_REDUCE_OR_HOLD"
        elif "NEGATIVE_DAILY_PNL" in flags:
            grade = "C"
            action = "REVIEW_HOLD_OR_STOP"
        elif daily_pnl > 0 and exposure_ratio <= 1.0:
            grade = "B"
            action = "REVIEW_HOLD"
        else:
            grade = "C"
            action = "REVIEW_HOLD"

        return {
            "symbol": candidate["symbol"],
            "grade": grade,
            "suggested_action": action,
            "flags": flags,
            "symbol_exposure": round(exposure, 6),
            "exposure_ratio": round(exposure_ratio, 6),
            "daily_pnl": round(daily_pnl, 6),
            "existing_exit_advisory": exit_data.get("scenarios", []),
            "enforced": False,
            "position_changes_performed": 0,
        }

    def explainable_ai(self) -> dict[str, Any]:
        candidate = self.candidate()
        mtf = self.multi_timeframe()
        regime = self.market_regime()
        position = self.position_quality()
        v5 = self._v5()
        ensemble = v5.get("ensemble", {})
        comparison = v5.get("decision_comparison", {})

        positive: list[str] = []
        negative: list[str] = []

        if candidate["confidence"] >= 0.80:
            positive.append("HIGH_CONFIDENCE")
        if candidate["consensus_score"] >= 0.75:
            positive.append("STRONG_CONSENSUS")
        if candidate["reward_risk"] >= 1.50:
            positive.append("ACCEPTABLE_REWARD_RISK")
        if mtf["alignment"] == "BULLISH_ALIGNMENT":
            positive.append("MULTI_TIMEFRAME_BULLISH_ALIGNMENT")

        if mtf["alignment"] == "MIXED_ALIGNMENT":
            negative.append("MULTI_TIMEFRAME_MIXED")
        if regime["label"] in {
            "UNCERTAIN",
            "HIGH_VOLATILITY",
            "EXTREME_VOLATILITY",
        }:
            negative.append(f"REGIME_{regime['label']}")
        negative.extend(position["flags"])

        return {
            "headline": (
                f"{candidate['side']} {candidate['symbol']}"
                if candidate["symbol"]
                else "NO_ACTIVE_CANDIDATE"
            ),
            "positive_reasons": sorted(set(positive)),
            "caution_reasons": sorted(set(negative)),
            "ensemble_decision": ensemble.get("decision"),
            "ensemble_score": ensemble.get("weighted_score"),
            "decision_comparison": comparison.get("comparison"),
            "market_regime": regime["label"],
            "multi_timeframe_alignment": mtf["alignment"],
            "position_grade": position["grade"],
            "final_interpretation": "READ_ONLY_EXPLANATION_NO_ORDER_EFFECT",
        }

    def performance_dashboard(self) -> dict[str, Any]:
        v4 = self._v4()
        perf = v4.get("performance_summary", {})
        calibration = v4.get("confidence_calibration", {})
        guard_compare = v4.get("guard_comparison", {})
        ensemble_rows = self._load_jsonl(
            self.root
            / "runtime/ai_strategy_ensemble_v5/ensemble_ledger.jsonl"
        )

        decision_counts: dict[str, int] = {}
        symbol_counts: dict[str, int] = {}
        for row in ensemble_rows:
            decision = str(
                row.get("ensemble", {}).get("decision", "")
            )
            symbol = str(
                row.get("candidate", {}).get("symbol", "")
            ).upper()
            if decision:
                decision_counts[decision] = decision_counts.get(decision, 0) + 1
            if symbol:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        return {
            "closed_trade_count": perf.get("closed_trade_count", 0),
            "win_rate": perf.get("win_rate"),
            "profit_factor": perf.get("profit_factor"),
            "average_win": perf.get("average_win"),
            "average_loss": perf.get("average_loss"),
            "total_realized_pl": perf.get("total_realized_pl", 0),
            "calibration_status": calibration.get("status"),
            "guard_comparison_status": guard_compare.get("comparison_status"),
            "ensemble_sample_count": len(ensemble_rows),
            "ensemble_decision_frequency": [
                {"decision": key, "count": value}
                for key, value in sorted(
                    decision_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "candidate_symbol_frequency": [
                {"symbol": key, "count": value}
                for key, value in sorted(
                    symbol_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "dashboard_status": (
                "COLLECTING_DATA"
                if int(perf.get("closed_trade_count", 0) or 0) < 20
                else "PERFORMANCE_REVIEW_READY"
            ),
            "automatic_changes": False,
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/shadow_intelligence_v6_v10"

        result = {
            "stage": "SHADOW_INTELLIGENCE_PACK_V6_TO_V10",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "multi_timeframe_intelligence": self.multi_timeframe(),
            "market_regime_engine": self.market_regime(),
            "position_quality_analyzer": self.position_quality(),
            "explainable_ai_report": self.explainable_ai(),
            "performance_dashboard": self.performance_dashboard(),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_shadow_intelligence_report.json", result)
        self._append(runtime / "shadow_intelligence_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "timeframe_alignment": result[
                "multi_timeframe_intelligence"
            ]["alignment"],
            "market_regime": result["market_regime_engine"]["label"],
            "position_grade": result["position_quality_analyzer"]["grade"],
            "ensemble_decision": result["explainable_ai_report"][
                "ensemble_decision"
            ],
            "dashboard_status": result["performance_dashboard"][
                "dashboard_status"
            ],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_shadow_intelligence_summary.json", summary)

        return result
