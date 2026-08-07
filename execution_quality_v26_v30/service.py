from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ExecutionQualityTimingPack:
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
    def _load_jsonl(path: Path, limit: int = 10000) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        out = []
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines()[-limit:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append(obj)
                except Exception:
                    pass
        except Exception:
            pass
        return out

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
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

    def _brain(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/ai_brain_v4/latest_ai_brain_report.json"
        )

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        )

    def _market(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/market_context_v16_v20/latest_market_context_report.json"
        )

    def _performance(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/performance_intelligence_v21_v25/latest_performance_intelligence_report.json"
        )

    def _memory(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/ai_market_memory_v3/latest_market_memory_report.json"
        )

    def v26_entry_timing_quality(self) -> dict[str, Any]:
        brain = self._brain()
        mtf = brain.get("multi_timeframe_ai", {})
        market = self._market().get("market_context_summary", {})
        guard = self._guard()

        alignment = self._float(mtf.get("alignment_score"), 0.5)
        dispersion = self._float(mtf.get("dispersion"), 0.5)
        minutes_to_close = self._float(
            guard.get("market_snapshot", {}).get("minutes_to_close"),
            999.0,
        )

        score = 0.55 * alignment + 0.25 * (1.0 - min(dispersion, 1.0))
        if market.get("market_entry_context") == "FAVORABLE_OR_NEUTRAL":
            score += 0.10
        elif market.get("market_entry_context") == "UNFAVORABLE":
            score -= 0.15

        if minutes_to_close < 30:
            score -= 0.15
        elif minutes_to_close < 60:
            score -= 0.05

        score = min(max(score, 0.0), 1.0)

        if score >= 0.80:
            timing = "STRONG_WINDOW"
        elif score >= 0.65:
            timing = "ACCEPTABLE_WINDOW"
        elif score >= 0.50:
            timing = "WAIT_FOR_BETTER_ALIGNMENT"
        else:
            timing = "POOR_WINDOW"

        return {
            "status": "PASS",
            "timing_score": round(score, 6),
            "timing_state": timing,
            "minutes_to_close": minutes_to_close,
            "multi_timeframe_alignment": round(alignment, 6),
            "multi_timeframe_dispersion": round(dispersion, 6),
            "enforced": False,
            "order_effect": "NONE",
        }

    def v27_slippage_liquidity_risk(self) -> dict[str, Any]:
        brain = self._brain()
        top = brain.get("multi_factor_ranking", {}).get("top_candidate") or {}
        market = self._market()

        reference_price = self._float(top.get("reference_price"), 0.0)
        liquidity = self._float(
            market.get("v16_market_regime_predictor", {}).get("liquidity_score"),
            -1.0,
        )

        if reference_price <= 0 and liquidity < 0:
            return {
                "status": "COLLECTING_DATA",
                "slippage_risk": "UNKNOWN",
                "liquidity_score": None,
                "estimated_slippage_bps": None,
                "enforced": False,
            }

        if liquidity < 0:
            liquidity = 0.5

        estimated_bps = max(1.0, (1.0 - liquidity) * 20.0)
        if estimated_bps >= 15:
            risk = "HIGH"
        elif estimated_bps >= 8:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "status": "PASS",
            "slippage_risk": risk,
            "liquidity_score": round(liquidity, 6),
            "estimated_slippage_bps": round(estimated_bps, 6),
            "reference_price": reference_price,
            "enforced": False,
            "order_effect": "NONE",
        }

    def v28_adaptive_notional_recommendation(self) -> dict[str, Any]:
        brain = self._brain()
        decision = brain.get("explainable_final_decision", {})
        brain_score = self._float(decision.get("brain_score"), 0.0)
        timing = self.v26_entry_timing_quality()
        liquidity = self.v27_slippage_liquidity_risk()

        hard_limit = 100.0
        if brain_score < 0.55:
            notional = 0.0
        elif brain_score < 0.68:
            notional = 25.0
        elif brain_score < 0.80:
            notional = 50.0
        elif brain_score < 0.90:
            notional = 75.0
        else:
            notional = 100.0

        if timing["timing_state"] in {"POOR_WINDOW", "WAIT_FOR_BETTER_ALIGNMENT"}:
            notional *= 0.5

        if liquidity.get("slippage_risk") == "HIGH":
            notional *= 0.5
        elif liquidity.get("slippage_risk") == "MEDIUM":
            notional *= 0.75

        notional = round(min(max(notional, 0.0), hard_limit), 2)

        return {
            "status": "PASS",
            "suggested_notional": notional,
            "current_hard_limit": hard_limit,
            "basis_brain_score": round(brain_score, 6),
            "basis_timing_state": timing["timing_state"],
            "basis_slippage_risk": liquidity.get("slippage_risk"),
            "shadow_only": True,
            "enforced": False,
            "order_effect": "NONE",
        }

    def v29_exit_timing_review(self) -> dict[str, Any]:
        guard = self._guard()
        risk = guard.get("risk_snapshot", {})
        candidate = guard.get("candidate", {})
        daily_pnl = self._float(risk.get("daily_pnl"))
        exposure = self._float(risk.get("symbol_exposure"))
        rr = self._float(candidate.get("reward_risk"))
        timing = self.v26_entry_timing_quality()

        scenarios = []
        symbol = str(candidate.get("symbol", "")).upper()

        if symbol:
            if daily_pnl < 0 and timing["timing_state"] == "POOR_WINDOW":
                action = "REVIEW_STOP_OR_REDUCE"
                reason = "NEGATIVE_PNL_AND_POOR_TIMING"
            elif daily_pnl > 0 and rr >= 2.0:
                action = "REVIEW_PARTIAL_PROFIT_OR_HOLD"
                reason = "POSITIVE_PNL_AND_FAVORABLE_REWARD_RISK"
            elif exposure > 500:
                action = "REVIEW_REDUCE_EXPOSURE"
                reason = "SYMBOL_EXPOSURE_ABOVE_REFERENCE_LIMIT"
            else:
                action = "REVIEW_HOLD"
                reason = "NO_STRONG_EXIT_SIGNAL"

            scenarios.append({
                "symbol": symbol,
                "suggested_action": action,
                "reason": reason,
                "daily_pnl": round(daily_pnl, 6),
                "symbol_exposure": round(exposure, 6),
                "enforced": False,
                "broker_action_performed": False,
            })

        return {
            "status": "PASS",
            "mode": "SHADOW_EXIT_TIMING_REVIEW",
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
            "exit_orders_submitted": 0,
            "position_changes_performed": 0,
        }

    def v30_daily_replay_opportunity_cost(self) -> dict[str, Any]:
        brain_rows = self._load_jsonl(
            self.root / "runtime/ai_brain_v4/ai_brain_ledger.jsonl"
        )
        perf = self._performance()
        counter = perf.get("v25_counterfactual_shadow_review", {})

        skipped = 0
        buy_watch = 0
        strong_buy = 0

        for row in brain_rows[-100:]:
            decision = row.get("explainable_final_decision", {}).get("decision")
            if decision == "SKIP_OBSERVATION":
                skipped += 1
            elif decision == "BUY_OR_WATCH_OBSERVATION":
                buy_watch += 1
            elif decision == "STRONG_BUY_OBSERVATION":
                strong_buy += 1

        return {
            "status": "PASS",
            "brain_sample_count": len(brain_rows[-100:]),
            "decision_counts": {
                "SKIP_OBSERVATION": skipped,
                "BUY_OR_WATCH_OBSERVATION": buy_watch,
                "STRONG_BUY_OBSERVATION": strong_buy,
            },
            "counterfactual_status": counter.get("status", "COLLECTING_DATA"),
            "counterfactual_interpretation": counter.get(
                "interpretation", "INSUFFICIENT_DATA"
            ),
            "opportunity_cost_status": (
                "REVIEW_READY"
                if counter.get("status") == "REVIEW_READY"
                else "COLLECTING_DATA"
            ),
            "automatic_learning_changes": False,
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/execution_quality_v26_v30"

        result = {
            "stage": "EXECUTION_QUALITY_TIMING_V26_TO_V30",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v26_entry_timing_quality": self.v26_entry_timing_quality(),
            "v27_slippage_liquidity_risk": self.v27_slippage_liquidity_risk(),
            "v28_adaptive_notional_recommendation": (
                self.v28_adaptive_notional_recommendation()
            ),
            "v29_exit_timing_review": self.v29_exit_timing_review(),
            "v30_daily_replay_opportunity_cost": (
                self.v30_daily_replay_opportunity_cost()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_execution_quality_report.json", result)
        self._append(runtime / "execution_quality_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "timing_state": result["v26_entry_timing_quality"]["timing_state"],
            "slippage_risk": result["v27_slippage_liquidity_risk"].get(
                "slippage_risk"
            ),
            "suggested_notional": result[
                "v28_adaptive_notional_recommendation"
            ]["suggested_notional"],
            "exit_scenario_count": result[
                "v29_exit_timing_review"
            ]["scenario_count"],
            "opportunity_cost_status": result[
                "v30_daily_replay_opportunity_cost"
            ]["opportunity_cost_status"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_execution_quality_summary.json", summary)

        return result
