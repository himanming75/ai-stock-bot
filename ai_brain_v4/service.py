from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AIBrainV4:
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

    def _v5(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/ai_strategy_ensemble_v5/latest_ensemble_report.json"
        )

    def _v6_10(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/shadow_intelligence_v6_v10/latest_shadow_intelligence_report.json"
        )

    def _v16_20(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/market_context_v16_v20/latest_market_context_report.json"
        )

    def _v21_25(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/performance_intelligence_v21_v25/latest_performance_intelligence_report.json"
        )

    def _observability(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/paper_observability_intelligence/latest_observability_report.json"
        )

    def multi_timeframe_ai(self) -> dict[str, Any]:
        base = self._v6_10().get("multi_timeframe_intelligence", {})
        frames = base.get("timeframes", {})
        if not isinstance(frames, dict) or not frames:
            return {
                "status": "COLLECTING_DATA",
                "timeframes": {},
                "alignment_score": None,
                "direction": "UNKNOWN",
                "enforced": False,
            }

        values = [self._float(v, 0.5) for v in frames.values()]
        avg = sum(values) / len(values)
        dispersion = max(values) - min(values) if values else 0.0

        if avg >= 0.72 and dispersion <= 0.30:
            direction = "BULLISH"
        elif avg <= 0.40:
            direction = "BEARISH"
        else:
            direction = "MIXED"

        return {
            "status": "PASS",
            "timeframes": frames,
            "alignment_score": round(avg, 6),
            "dispersion": round(dispersion, 6),
            "direction": direction,
            "enforced": False,
            "order_effect": "NONE",
        }

    def candidate_pool(self) -> list[dict[str, Any]]:
        obs = self._observability()
        rows = obs.get("top_candidates", [])
        if not isinstance(rows, list):
            rows = []

        if not rows:
            selected = obs.get("selected_candidate", {})
            if selected:
                rows = [dict(selected, rank=1)]

        pool = []
        for row in rows[:20]:
            symbol = str(row.get("symbol", "")).upper()
            if not symbol:
                continue
            pool.append({
                "symbol": symbol,
                "side": str(row.get("side", "HOLD")).upper(),
                "confidence": self._float(row.get("confidence")),
                "consensus_score": self._float(row.get("consensus_score")),
                "reward_risk": self._float(row.get("reward_risk")),
                "reference_price": self._float(row.get("reference_price")),
                "source_rank": int(row.get("rank", len(pool)+1) or len(pool)+1),
            })
        return pool

    def correlation_penalty(self, symbol: str) -> dict[str, Any]:
        perf = self._v21_25().get("v21_symbol_performance_memory", {})
        ranked = perf.get("ranked_symbols", [])
        guard = self._load(
            self.root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        )

        issue_codes = {
            str(item.get("code"))
            for item in guard.get("issues", [])
            if item.get("code")
        }

        penalty = 0.0
        reasons = []

        if "DUPLICATE_SYMBOL_BUY" in issue_codes:
            penalty += 0.20
            reasons.append("DUPLICATE_SYMBOL_RISK")
        if "SYMBOL_EXPOSURE_LIMIT" in issue_codes:
            penalty += 0.20
            reasons.append("SYMBOL_EXPOSURE_RISK")

        for row in ranked:
            if str(row.get("symbol", "")).upper() == symbol:
                pf = row.get("profit_factor")
                if pf is not None and self._float(pf) < 1.0:
                    penalty += 0.10
                    reasons.append("WEAK_SYMBOL_HISTORY")

        return {
            "penalty": round(min(penalty, 0.5), 6),
            "reasons": reasons,
        }

    def opportunity_score(self, candidate: dict[str, Any]) -> dict[str, Any]:
        mtf = self.multi_timeframe_ai()
        market = self._v16_20().get("market_context_summary", {})
        ensemble = self._v5().get("ensemble", {})

        confidence = candidate["confidence"]
        consensus = candidate["consensus_score"]
        rr = min(max(candidate["reward_risk"] / 3.0, 0.0), 1.0)
        mtf_score = self._float(mtf.get("alignment_score"), 0.5)
        ensemble_score = self._float(ensemble.get("weighted_score"), 0.5)

        market_bonus = 0.05 if market.get("market_entry_context") == "FAVORABLE_OR_NEUTRAL" else 0.0
        market_penalty = 0.15 if market.get("market_entry_context") == "UNFAVORABLE" else 0.0

        corr = self.correlation_penalty(candidate["symbol"])

        raw = (
            0.28 * confidence
            + 0.22 * consensus
            + 0.18 * rr
            + 0.17 * mtf_score
            + 0.15 * ensemble_score
            + market_bonus
            - market_penalty
            - corr["penalty"]
        )
        score = min(max(raw, 0.0), 1.0)

        return {
            "symbol": candidate["symbol"],
            "score": round(score, 6),
            "components": {
                "confidence": round(confidence, 6),
                "consensus": round(consensus, 6),
                "reward_risk_quality": round(rr, 6),
                "multi_timeframe": round(mtf_score, 6),
                "ensemble": round(ensemble_score, 6),
                "market_bonus": market_bonus,
                "market_penalty": market_penalty,
                "correlation_penalty": corr["penalty"],
            },
            "penalty_reasons": corr["reasons"],
        }

    def multi_factor_ranking(self) -> dict[str, Any]:
        pool = self.candidate_pool()
        ranked = []

        for candidate in pool:
            scored = self.opportunity_score(candidate)
            ranked.append({**candidate, **scored})

        ranked.sort(
            key=lambda x: (-x["score"], x["source_rank"], x["symbol"])
        )

        for i, row in enumerate(ranked, start=1):
            row["brain_rank"] = i

        return {
            "status": "PASS" if ranked else "COLLECTING_DATA",
            "ranked_candidates": ranked,
            "top_candidate": ranked[0] if ranked else None,
            "automatic_candidate_replacement": False,
            "order_effect": "NONE",
        }

    def trade_reflection_memory(self) -> dict[str, Any]:
        perf = self._v21_25()
        symbol_memory = perf.get("v21_symbol_performance_memory", {})
        counter = perf.get("v25_counterfactual_shadow_review", {})
        ranking = self.multi_factor_ranking()

        reflections = []

        if ranking.get("top_candidate"):
            top = ranking["top_candidate"]
            if top["score"] >= 0.80:
                reflections.append("TOP_CANDIDATE_HIGH_QUALITY")
            elif top["score"] < 0.60:
                reflections.append("TOP_CANDIDATE_WEAK_QUALITY")

        if counter.get("interpretation") == "BLOCKED_SET_OUTPERFORMS_REVIEW_GUARD_STRICTNESS":
            reflections.append("REVIEW_GUARD_STRICTNESS")
        elif counter.get("interpretation") == "GUARD_ALLOW_OUTPERFORMS_BLOCK":
            reflections.append("GUARD_FILTER_APPEARS_HELPFUL")

        best_symbol = symbol_memory.get("best_symbol")
        if best_symbol:
            reflections.append(f"BEST_HISTORICAL_SYMBOL:{best_symbol}")

        return {
            "status": "PASS",
            "reflections": reflections,
            "automatic_strategy_changes": False,
            "automatic_parameter_changes": False,
        }

    def explainable_final_decision(self) -> dict[str, Any]:
        ranking = self.multi_factor_ranking()
        market = self._v16_20().get("market_context_summary", {})
        mtf = self.multi_timeframe_ai()

        top = ranking.get("top_candidate")
        if not top:
            return {
                "decision": "NO_CANDIDATE",
                "reasoning": ["NO_CANDIDATE_DATA"],
                "enforced": False,
                "order_effect": "NONE",
            }

        reasons = []
        if top["confidence"] >= 0.8:
            reasons.append("HIGH_CONFIDENCE")
        if top["consensus_score"] >= 0.75:
            reasons.append("STRONG_CONSENSUS")
        if top["reward_risk"] >= 1.5:
            reasons.append("ACCEPTABLE_REWARD_RISK")
        if mtf.get("direction") == "BULLISH":
            reasons.append("MULTI_TIMEFRAME_BULLISH")
        if market.get("market_entry_context") == "UNFAVORABLE":
            reasons.append("MARKET_CONTEXT_UNFAVORABLE")
        reasons.extend(top.get("penalty_reasons", []))

        if top["score"] >= 0.80 and "MARKET_CONTEXT_UNFAVORABLE" not in reasons:
            decision = "STRONG_BUY_OBSERVATION"
        elif top["score"] >= 0.68:
            decision = "BUY_OR_WATCH_OBSERVATION"
        else:
            decision = "SKIP_OBSERVATION"

        return {
            "decision": decision,
            "symbol": top["symbol"],
            "brain_score": top["score"],
            "reasoning": reasons,
            "enforced": False,
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/ai_brain_v4"

        result = {
            "stage": "AI_BRAIN_V4_DECISION_INTELLIGENCE_PACK",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "multi_timeframe_ai": self.multi_timeframe_ai(),
            "multi_factor_ranking": self.multi_factor_ranking(),
            "trade_reflection_memory": self.trade_reflection_memory(),
            "explainable_final_decision": self.explainable_final_decision(),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_ai_brain_report.json", result)
        self._append(runtime / "ai_brain_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "decision": result["explainable_final_decision"]["decision"],
            "symbol": result["explainable_final_decision"].get("symbol"),
            "brain_score": result["explainable_final_decision"].get("brain_score"),
            "candidate_count": len(
                result["multi_factor_ranking"]["ranked_candidates"]
            ),
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_ai_brain_summary.json", summary)
        return result
