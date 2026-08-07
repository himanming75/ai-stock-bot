from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ShadowValidationIntelligence:
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

    def _v6_v10(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/shadow_intelligence_v6_v10/"
              "latest_shadow_intelligence_report.json"
        )

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    def _session(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/latest_status.json"
        )

    def confidence_calibration_2(self) -> dict[str, Any]:
        v4 = self._v4()
        calibration = v4.get("confidence_calibration", {})
        buckets = calibration.get("buckets", {})

        bucket_reviews = []
        total_samples = 0
        for name in ["0.50-0.69", "0.70-0.79", "0.80-0.89", "0.90-1.00"]:
            stats = buckets.get(name, {})
            count = int(stats.get("sample_count", 0) or 0)
            win_rate = stats.get("realized_win_rate")
            expectancy = stats.get("expectancy")
            total_samples += count

            if count < 10:
                state = "INSUFFICIENT_DATA"
            elif win_rate is None:
                state = "OUTCOME_LINK_MISSING"
            elif name == "0.90-1.00" and float(win_rate) < 0.70:
                state = "POSSIBLE_OVERCONFIDENCE"
            elif float(win_rate) >= 0.70:
                state = "HEALTHY"
            else:
                state = "MONITOR"

            bucket_reviews.append({
                "bucket": name,
                "sample_count": count,
                "realized_win_rate": win_rate,
                "expectancy": expectancy,
                "review_state": state,
            })

        return {
            "total_linked_samples": total_samples,
            "bucket_reviews": bucket_reviews,
            "status": (
                "CALIBRATION_REVIEW_READY"
                if total_samples >= 50
                else "COLLECTING_DATA"
            ),
            "automatic_confidence_changes": False,
            "human_approval_required": True,
        }

    def false_signal_detector(self) -> dict[str, Any]:
        v5 = self._v5()
        v6 = self._v6_v10()
        guard = self._guard()

        ensemble = v5.get("ensemble", {})
        explain = v6.get("explainable_ai_report", {})
        position = v6.get("position_quality_analyzer", {})

        score = self._float(ensemble.get("weighted_score"), 0.5)
        avoid_votes = int(ensemble.get("avoid_votes", 0) or 0)
        agreement = self._float(ensemble.get("agreement_ratio"), 0.0)
        candidate_side = str(
            v5.get("candidate", {}).get("side", "HOLD")
        ).upper()

        issues = {
            str(item.get("code"))
            for item in guard.get("issues", [])
            if item.get("code")
        }
        cautions = set(explain.get("caution_reasons", []))
        flags: list[str] = []

        if candidate_side == "BUY" and score < 0.65:
            flags.append("BUY_SCORE_CONFLICT")
        if avoid_votes >= 3:
            flags.append("MULTIPLE_STRATEGIES_AVOID")
        if agreement < 0.60:
            flags.append("LOW_ENSEMBLE_AGREEMENT")
        if "DUPLICATE_SYMBOL_BUY" in issues:
            flags.append("DUPLICATE_ENTRY_RISK")
        if "SYMBOL_EXPOSURE_LIMIT" in issues:
            flags.append("EXPOSURE_DRIVEN_FALSE_SIGNAL_RISK")
        if position.get("grade") in {"D", "F"}:
            flags.append("LOW_POSITION_QUALITY")
        if "REGIME_UNCERTAIN" in cautions:
            flags.append("UNCERTAIN_MARKET_CONTEXT")

        risk_score = min(len(flags) / 6.0, 1.0)
        if risk_score >= 0.75:
            level = "HIGH"
        elif risk_score >= 0.40:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "false_signal_risk": level,
            "risk_score": round(risk_score, 6),
            "flags": flags,
            "recommended_observation": (
                "SKIP_OR_REQUIRE_STRONGER_CONFIRMATION"
                if level == "HIGH"
                else "MONITOR"
            ),
            "enforced": False,
            "order_effect": "NONE",
        }

    def context_similarity_memory(self) -> dict[str, Any]:
        current = self._v6_v10()
        current_regime = str(
            current.get("market_regime_engine", {}).get("label", "")
        )
        current_alignment = str(
            current.get("multi_timeframe_intelligence", {}).get(
                "alignment", ""
            )
        )
        current_grade = str(
            current.get("position_quality_analyzer", {}).get("grade", "")
        )

        rows = self._load_jsonl(
            self.root
            / "runtime/shadow_intelligence_v6_v10/"
              "shadow_intelligence_ledger.jsonl"
        )

        similar = []
        for row in rows:
            regime = str(
                row.get("market_regime_engine", {}).get("label", "")
            )
            alignment = str(
                row.get("multi_timeframe_intelligence", {}).get(
                    "alignment", ""
                )
            )
            grade = str(
                row.get("position_quality_analyzer", {}).get("grade", "")
            )

            matches = sum([
                regime == current_regime and bool(current_regime),
                alignment == current_alignment and bool(current_alignment),
                grade == current_grade and bool(current_grade),
            ])
            similarity = matches / 3.0

            if similarity > 0:
                similar.append({
                    "generated_at_utc": row.get("generated_at_utc"),
                    "similarity": round(similarity, 6),
                    "market_regime": regime,
                    "timeframe_alignment": alignment,
                    "position_grade": grade,
                    "ensemble_decision": row.get(
                        "explainable_ai_report", {}
                    ).get("ensemble_decision"),
                })

        similar.sort(
            key=lambda item: (
                -item["similarity"],
                str(item.get("generated_at_utc", "")),
            )
        )

        return {
            "current_context": {
                "market_regime": current_regime,
                "timeframe_alignment": current_alignment,
                "position_grade": current_grade,
            },
            "similar_context_count": len(similar),
            "top_similar_contexts": similar[:20],
            "outcome_linked_count": 0,
            "status": (
                "CONTEXT_MEMORY_READY"
                if len(similar) >= 10
                else "COLLECTING_CONTEXTS"
            ),
            "automatic_strategy_changes": False,
        }

    def trade_replay(self) -> dict[str, Any]:
        session_rows = self._load_jsonl(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "session_ledger.jsonl"
        )
        guard_rows = self._load_jsonl(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "shadow_guard_ledger.jsonl"
        )
        ensemble_rows = self._load_jsonl(
            self.root
            / "runtime/ai_strategy_ensemble_v5/ensemble_ledger.jsonl"
        )
        intel_rows = self._load_jsonl(
            self.root
            / "runtime/shadow_intelligence_v6_v10/"
              "shadow_intelligence_ledger.jsonl"
        )

        timeline = []
        for label, rows in [
            ("SESSION", session_rows[-20:]),
            ("GUARD", guard_rows[-20:]),
            ("ENSEMBLE", ensemble_rows[-20:]),
            ("SHADOW_INTELLIGENCE", intel_rows[-20:]),
        ]:
            for row in rows:
                timestamp = (
                    row.get("generated_at_utc")
                    or row.get("observed_at_utc")
                    or row.get("updated_at_utc")
                )
                timeline.append({
                    "timestamp": timestamp,
                    "source": label,
                    "stage": row.get("stage"),
                    "status": row.get("status"),
                    "action": (
                        row.get("action")
                        or row.get("ensemble", {}).get("decision")
                        or row.get("explainable_ai_report", {}).get(
                            "ensemble_decision"
                        )
                    ),
                    "broker_write_performed": bool(
                        row.get("broker_write_performed", False)
                    ),
                })

        timeline.sort(key=lambda item: str(item.get("timestamp") or ""))

        return {
            "event_count": len(timeline),
            "timeline": timeline[-100:],
            "replay_mode": "READ_ONLY_AUDIT",
            "broker_actions_replayed": False,
            "orders_submitted_during_replay": 0,
        }

    def live_readiness_dashboard(self) -> dict[str, Any]:
        v4 = self._v4()
        perf = v4.get("performance_summary", {})
        guard_compare = v4.get("guard_comparison", {})
        calibration = self.confidence_calibration_2()
        context = self.context_similarity_memory()

        closed_trades = int(perf.get("closed_trade_count", 0) or 0)
        win_rate = perf.get("win_rate")
        profit_factor = perf.get("profit_factor")

        checks = {
            "closed_trades_at_least_50": closed_trades >= 50,
            "calibration_samples_at_least_50": (
                calibration["total_linked_samples"] >= 50
            ),
            "profit_factor_at_least_1_20": (
                profit_factor is not None and float(profit_factor) >= 1.20
            ),
            "win_rate_at_least_0_50": (
                win_rate is not None and float(win_rate) >= 0.50
            ),
            "guard_comparison_ready": (
                guard_compare.get("comparison_status") == "READY"
            ),
            "context_memory_at_least_10": (
                context["similar_context_count"] >= 10
            ),
            "automatic_changes_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)
        ready = passed == len(checks)

        blockers = [
            name for name, value in checks.items() if not value
        ]

        return {
            "status": "LIVE_READY_FOR_HUMAN_REVIEW" if ready else "NOT_READY",
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "blockers": blockers,
            "live_submission_enabled": False,
            "certification_effect": "ADVISORY_ONLY",
            "human_approval_required": True,
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/shadow_validation_v11_v15"

        result = {
            "stage": "SHADOW_VALIDATION_INTELLIGENCE_V11_TO_V15",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v11_confidence_calibration_2": (
                self.confidence_calibration_2()
            ),
            "v12_false_signal_detector": self.false_signal_detector(),
            "v13_context_similarity_memory": (
                self.context_similarity_memory()
            ),
            "v14_trade_replay": self.trade_replay(),
            "v15_live_readiness_dashboard": (
                self.live_readiness_dashboard()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(runtime / "latest_validation_report.json", result)
        self._append(runtime / "validation_ledger.jsonl", result)

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "false_signal_risk": result[
                "v12_false_signal_detector"
            ]["false_signal_risk"],
            "context_memory_status": result[
                "v13_context_similarity_memory"
            ]["status"],
            "replay_event_count": result[
                "v14_trade_replay"
            ]["event_count"],
            "live_readiness_status": result[
                "v15_live_readiness_dashboard"
            ]["status"],
            "live_readiness_passed_checks": result[
                "v15_live_readiness_dashboard"
            ]["passed_checks"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(runtime / "daily_validation_summary.json", summary)

        return result
