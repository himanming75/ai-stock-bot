from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StrategyEnsembleShadowReview:
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
            lines = path.read_text(encoding="utf-8-sig").splitlines()[-limit:]
            for line in lines:
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

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    def candidate(self) -> dict[str, Any]:
        guard_candidate = self._guard().get("candidate", {})
        v2_candidate = self._v2().get("candidate", {})
        candidate = guard_candidate if guard_candidate else v2_candidate
        return {
            "symbol": str(candidate.get("symbol", "")).upper(),
            "side": str(candidate.get("side", "HOLD")).upper(),
            "confidence": self._float(candidate.get("confidence")),
            "consensus_score": self._float(candidate.get("consensus_score")),
            "reward_risk": self._float(candidate.get("reward_risk")),
            "quantity": self._float(candidate.get("quantity")),
            "reference_price": self._float(candidate.get("reference_price")),
        }

    def strategy_scores(self) -> dict[str, Any]:
        v2 = self._v2()
        multi = v2.get("multi_score", {})
        regime = v2.get("market_regime", {})
        heat = v2.get("safety_heatmap", {})
        candidate = self.candidate()

        confidence = candidate["confidence"]
        consensus = candidate["consensus_score"]
        reward_risk = min(max(candidate["reward_risk"] / 3.0, 0.0), 1.0)
        trend = self._float(multi.get("trend_score"), (confidence + consensus) / 2)
        momentum = self._float(multi.get("momentum_score"), consensus)
        breakout = self._float(multi.get("breakout_score"), reward_risk)
        regime_fit = self._float(regime.get("market_regime_fit"), 0.5)
        volatility_risk = self._float(regime.get("volatility_risk"), 0.5)
        risk_quality = 1.0 - min(max(volatility_risk, 0.0), 1.0)

        mean_reversion = round(
            min(max((1.0 - trend) * 0.6 + risk_quality * 0.4, 0.0), 1.0),
            6,
        )
        volatility = round(risk_quality, 6)
        risk = 0.0 if heat.get("level") in {"HIGH", "EXTREME"} else risk_quality

        scores = {
            "trend": round(min(max(trend, 0.0), 1.0), 6),
            "momentum": round(min(max(momentum, 0.0), 1.0), 6),
            "breakout": round(min(max(breakout, 0.0), 1.0), 6),
            "mean_reversion": mean_reversion,
            "volatility": volatility,
            "risk": round(min(max(risk, 0.0), 1.0), 6),
        }
        return scores

    @staticmethod
    def _vote(score: float) -> str:
        if score >= 0.75:
            return "BUY"
        if score >= 0.55:
            return "HOLD"
        return "AVOID"

    def ensemble(self) -> dict[str, Any]:
        scores = self.strategy_scores()
        weights = {
            "trend": 0.22,
            "momentum": 0.20,
            "breakout": 0.16,
            "mean_reversion": 0.12,
            "volatility": 0.14,
            "risk": 0.16,
        }

        votes = {name: self._vote(score) for name, score in scores.items()}
        weighted_score = sum(scores[name] * weights[name] for name in scores)
        buy_votes = sum(1 for vote in votes.values() if vote == "BUY")
        hold_votes = sum(1 for vote in votes.values() if vote == "HOLD")
        avoid_votes = sum(1 for vote in votes.values() if vote == "AVOID")

        if weighted_score >= 0.80 and buy_votes >= 4 and avoid_votes == 0:
            decision = "STRONG_BUY_OBSERVATION"
        elif weighted_score >= 0.70 and buy_votes >= 3:
            decision = "BUY_OBSERVATION"
        elif avoid_votes >= 2:
            decision = "SKIP_OBSERVATION"
        else:
            decision = "HOLD_OBSERVATION"

        agreement = max(buy_votes, hold_votes, avoid_votes) / len(votes)

        return {
            "strategy_scores": scores,
            "strategy_weights": weights,
            "votes": votes,
            "weighted_score": round(weighted_score, 6),
            "agreement_ratio": round(agreement, 6),
            "buy_votes": buy_votes,
            "hold_votes": hold_votes,
            "avoid_votes": avoid_votes,
            "decision": decision,
            "enforced": False,
            "order_effect": "NONE",
        }

    def decision_comparison(self) -> dict[str, Any]:
        candidate = self.candidate()
        ensemble = self.ensemble()
        original_action = candidate["side"]

        if original_action == "BUY" and ensemble["decision"] in {
            "SKIP_OBSERVATION",
            "HOLD_OBSERVATION",
        }:
            comparison = "ENSEMBLE_MORE_CONSERVATIVE"
        elif original_action in {"HOLD", ""} and ensemble["decision"] in {
            "BUY_OBSERVATION",
            "STRONG_BUY_OBSERVATION",
        }:
            comparison = "POTENTIAL_MISSED_OPPORTUNITY"
        elif original_action == "BUY" and ensemble["decision"] in {
            "BUY_OBSERVATION",
            "STRONG_BUY_OBSERVATION",
        }:
            comparison = "DIRECTIONAL_AGREEMENT"
        else:
            comparison = "NEUTRAL_COMPARISON"

        return {
            "original_candidate_side": original_action,
            "ensemble_decision": ensemble["decision"],
            "comparison": comparison,
            "enforced": False,
            "order_effect": "NONE",
        }

    def strategy_performance_memory(self) -> dict[str, Any]:
        calibration = self._v4()
        linked = calibration.get("linked_outcomes", [])
        result = {
            name: {
                "sample_count": 0,
                "wins": 0,
                "losses": 0,
                "total_realized_pl": 0.0,
                "win_rate": None,
            }
            for name in [
                "trend",
                "momentum",
                "breakout",
                "mean_reversion",
                "volatility",
                "risk",
            ]
        }

        for row in linked:
            pnl = self._float(row.get("realized_pl"))
            candidate = row.get("candidate", {})
            confidence = self._float(candidate.get("confidence"))
            consensus = self._float(candidate.get("consensus_score"))
            rr = self._float(candidate.get("reward_risk"))

            active = []
            if confidence >= 0.80:
                active.append("trend")
            if consensus >= 0.80:
                active.append("momentum")
            if rr >= 1.50:
                active.append("breakout")

            for name in active:
                result[name]["sample_count"] += 1
                result[name]["total_realized_pl"] += pnl
                if pnl > 0:
                    result[name]["wins"] += 1
                elif pnl < 0:
                    result[name]["losses"] += 1

        for stats in result.values():
            count = stats["sample_count"]
            stats["total_realized_pl"] = round(
                stats["total_realized_pl"], 6
            )
            stats["win_rate"] = (
                round(stats["wins"] / count, 6) if count else None
            )

        return {
            "strategies": result,
            "status": (
                "COLLECTING_OUTCOME_DATA"
                if sum(x["sample_count"] for x in result.values()) < 20
                else "STRATEGY_REVIEW_READY"
            ),
            "automatic_weight_changes": False,
        }

    def opportunity_review(self) -> dict[str, Any]:
        comparison = self.decision_comparison()
        guard = self._guard()
        issue_codes = [
            str(item.get("code"))
            for item in guard.get("issues", [])
            if item.get("code")
        ]

        flags: list[str] = []
        if comparison["comparison"] == "POTENTIAL_MISSED_OPPORTUNITY":
            flags.append("REVIEW_MISSED_OPPORTUNITY")
        if comparison["comparison"] == "ENSEMBLE_MORE_CONSERVATIVE":
            flags.append("REVIEW_POSSIBLE_OVERTRADING")
        if "DUPLICATE_SYMBOL_BUY" in issue_codes:
            flags.append("REVIEW_CONCENTRATION_RISK")
        if "SYMBOL_EXPOSURE_LIMIT" in issue_codes:
            flags.append("REVIEW_SYMBOL_EXPOSURE")

        return {
            "flags": flags,
            "review_required": bool(flags),
            "automatic_action": False,
            "broker_action_performed": False,
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/ai_strategy_ensemble_v5"

        result = {
            "stage": "AI_STRATEGY_ENSEMBLE_SHADOW_REVIEW_V5_0",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "candidate": self.candidate(),
            "ensemble": self.ensemble(),
            "decision_comparison": self.decision_comparison(),
            "strategy_performance_memory": (
                self.strategy_performance_memory()
            ),
            "opportunity_review": self.opportunity_review(),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_ensemble_report.json", result)
        self._append(runtime / "ensemble_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "symbol": result["candidate"]["symbol"],
            "original_side": result["candidate"]["side"],
            "ensemble_decision": result["ensemble"]["decision"],
            "weighted_score": result["ensemble"]["weighted_score"],
            "agreement_ratio": result["ensemble"]["agreement_ratio"],
            "comparison": result["decision_comparison"]["comparison"],
            "review_flags": result["opportunity_review"]["flags"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_ensemble_summary.json", summary)

        return result
