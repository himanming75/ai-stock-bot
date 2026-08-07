from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MarketMemoryExitIntelligence:
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
    def _load_jsonl(path: Path, limit: int = 1000) -> list[dict[str, Any]]:
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

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    def _observability(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_observability_intelligence/"
              "latest_observability_report.json"
        )

    def _positions(self) -> list[dict[str, Any]]:
        guard = self._guard()
        risk = guard.get("risk_snapshot", {})
        symbol = str(
            guard.get("candidate", {}).get("symbol", "")
        ).upper()
        exposure = self._float(risk.get("symbol_exposure"))
        if symbol and exposure > 0:
            return [{
                "symbol": symbol,
                "market_value": exposure,
                "unrealized_pl": self._float(risk.get("daily_pnl")),
            }]
        return []

    def market_memory(self) -> dict[str, Any]:
        obs_rows = self._load_jsonl(
            self.root
            / "runtime/paper_observability_intelligence/"
              "trade_journal.jsonl"
        )
        intel_rows = self._load_jsonl(
            self.root
            / "runtime/ai_intelligence_safety_v2/"
              "intelligence_ledger.jsonl"
        )
        guard_rows = self._load_jsonl(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "shadow_guard_ledger.jsonl"
        )

        symbol_counts: dict[str, int] = {}
        issue_counts: dict[str, int] = {}
        regime_counts: dict[str, int] = {}
        score_history: list[float] = []

        for row in obs_rows:
            candidate = row.get("selected_candidate", {})
            symbol = str(candidate.get("symbol", "")).upper()
            if symbol:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        for row in intel_rows:
            regime = str(
                row.get("market_regime", {}).get("label", "")
            )
            if regime:
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            score = self._float(
                row.get("multi_score", {}).get("total_score"), -1
            )
            if 0 <= score <= 1:
                score_history.append(score)

        for row in guard_rows:
            for issue in row.get("issues", []):
                code = issue.get("code")
                if code:
                    issue_counts[code] = issue_counts.get(code, 0) + 1

        return {
            "observability_samples": len(obs_rows),
            "intelligence_samples": len(intel_rows),
            "guard_samples": len(guard_rows),
            "candidate_frequency": [
                {"symbol": k, "count": v}
                for k, v in sorted(
                    symbol_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:20]
            ],
            "regime_frequency": [
                {"regime": k, "count": v}
                for k, v in sorted(
                    regime_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:20]
            ],
            "recurring_risk_patterns": [
                {"code": k, "count": v}
                for k, v in sorted(
                    issue_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )[:20]
            ],
            "mean_total_score": (
                round(sum(score_history) / len(score_history), 6)
                if score_history else None
            ),
            "memory_mode": "READ_ONLY",
            "automatic_strategy_changes": False,
        }

    def ensemble_vote(self) -> dict[str, Any]:
        v2 = self._v2()
        score = v2.get("multi_score", {})
        regime = v2.get("market_regime", {})
        heat = v2.get("safety_heatmap", {})

        votes = {
            "trend": "BUY" if self._float(score.get("trend_score")) >= 0.75 else "HOLD",
            "momentum": "BUY" if self._float(score.get("momentum_score")) >= 0.75 else "HOLD",
            "breakout": "BUY" if self._float(score.get("breakout_score")) >= 0.65 else "HOLD",
            "risk": "HOLD" if heat.get("level") in {"HIGH", "EXTREME"} else "BUY",
            "regime": "BUY" if self._float(regime.get("market_regime_fit")) >= 0.65 else "HOLD",
        }

        buy_votes = sum(1 for value in votes.values() if value == "BUY")
        hold_votes = sum(1 for value in votes.values() if value == "HOLD")

        if buy_votes >= 4:
            decision = "STRONG_BUY_OBSERVATION"
        elif buy_votes >= 3:
            decision = "BUY_OBSERVATION"
        else:
            decision = "HOLD_OR_SKIP_OBSERVATION"

        return {
            "votes": votes,
            "buy_votes": buy_votes,
            "hold_votes": hold_votes,
            "decision": decision,
            "enforced": False,
            "order_effect": "NONE",
        }

    def confidence_calibration_memory(self) -> dict[str, Any]:
        rows = self._load_jsonl(
            self.root
            / "runtime/paper_observability_intelligence/"
              "trade_journal.jsonl"
        )
        buckets = {
            "0.50-0.69": [],
            "0.70-0.79": [],
            "0.80-0.89": [],
            "0.90-1.00": [],
        }

        for row in rows:
            candidate = row.get("selected_candidate", {})
            confidence = self._float(candidate.get("confidence"), -1)
            if confidence < 0:
                continue
            if confidence < 0.70:
                key = "0.50-0.69"
            elif confidence < 0.80:
                key = "0.70-0.79"
            elif confidence < 0.90:
                key = "0.80-0.89"
            else:
                key = "0.90-1.00"
            buckets[key].append(confidence)

        return {
            "buckets": {
                key: {
                    "sample_count": len(values),
                    "mean_reported_confidence": (
                        round(sum(values) / len(values), 6)
                        if values else None
                    ),
                    "realized_win_rate": None,
                }
                for key, values in buckets.items()
            },
            "outcome_linked": False,
            "status": "WAITING_FOR_CLOSED_TRADE_OUTCOMES",
            "automatic_adjustment": False,
        }

    def exit_intelligence(self) -> dict[str, Any]:
        v2 = self._v2()
        guard = self._guard()
        candidate = guard.get("candidate", {})
        total_score = self._float(
            v2.get("multi_score", {}).get("total_score")
        )
        heat = str(
            v2.get("safety_heatmap", {}).get("level", "UNKNOWN")
        )
        rr = self._float(candidate.get("reward_risk"))
        positions = self._positions()

        scenarios: list[dict[str, Any]] = []
        for position in positions:
            symbol = position.get("symbol")
            unrealized = self._float(position.get("unrealized_pl"))

            if heat in {"EXTREME", "HIGH"}:
                action = "REVIEW_REDUCE_OR_HOLD"
                reason = "SAFETY_HEAT_HIGH"
            elif unrealized < 0 and total_score < 0.72:
                action = "REVIEW_STOP_LOSS"
                reason = "WEAK_SCORE_AND_NEGATIVE_PNL"
            elif unrealized > 0 and rr >= 2.0:
                action = "REVIEW_PARTIAL_PROFIT"
                reason = "POSITIVE_PNL_AND_FAVORABLE_RR"
            else:
                action = "REVIEW_HOLD"
                reason = "NO_STRONG_EXIT_SIGNAL"

            scenarios.append({
                "symbol": symbol,
                "suggested_action": action,
                "reason": reason,
                "unrealized_pl": unrealized,
                "enforced": False,
                "broker_action_performed": False,
            })

        return {
            "position_count": len(positions),
            "scenarios": scenarios,
            "exit_orders_submitted": 0,
            "cancel_orders_submitted": 0,
            "position_changes_performed": 0,
            "mode": "SHADOW_EXIT_ADVISORY",
        }

    def live_readiness_memory(self) -> dict[str, Any]:
        memory = self.market_memory()
        calibration = self.confidence_calibration_memory()

        checks = {
            "observability_samples_20": memory["observability_samples"] >= 20,
            "intelligence_samples_20": memory["intelligence_samples"] >= 20,
            "guard_samples_20": memory["guard_samples"] >= 20,
            "confidence_outcomes_available": calibration["outcome_linked"],
            "automatic_strategy_changes_off": True,
            "live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)
        return {
            "status": (
                "MEMORY_READY_FOR_REVIEW"
                if passed == len(checks)
                else "COLLECTING_DATA"
            ),
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "live_submission_enabled": False,
            "advisory_only": True,
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/ai_market_memory_v3"

        result = {
            "stage": "AI_MARKET_MEMORY_EXIT_INTELLIGENCE_V3_0",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "market_memory": self.market_memory(),
            "ensemble_vote": self.ensemble_vote(),
            "confidence_calibration_memory": (
                self.confidence_calibration_memory()
            ),
            "exit_intelligence": self.exit_intelligence(),
            "live_readiness_memory": self.live_readiness_memory(),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_market_memory_report.json", result)
        self._append(runtime / "market_memory_ledger.jsonl", result)

        daily = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "ensemble_decision": result["ensemble_vote"]["decision"],
            "exit_scenario_count": len(
                result["exit_intelligence"]["scenarios"]
            ),
            "memory_status": result["live_readiness_memory"]["status"],
            "broker_write_performed": False,
        }
        self._write(runtime / "daily_memory_review.json", daily)

        return result
