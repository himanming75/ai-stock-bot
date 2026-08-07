from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DataQualityDecisionRobustness:
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
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
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
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

    def _brain(self) -> dict[str, Any]:
        return self._load(
            self.root / "runtime/ai_brain_v4/latest_ai_brain_report.json"
        )

    def _execution(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/execution_quality_v26_v30/"
              "latest_execution_quality_report.json"
        )

    def _market(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/market_context_v16_v20/"
              "latest_market_context_report.json"
        )

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    @staticmethod
    def _parse_ts(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def v31_data_quality_audit(self) -> dict[str, Any]:
        sources = {
            "brain": self._brain(),
            "execution": self._execution(),
            "market": self._market(),
            "guard": self._guard(),
        }

        now = datetime.now(timezone.utc)
        freshness = {}
        missing = []
        stale = []

        for name, payload in sources.items():
            ts = (
                payload.get("generated_at_utc")
                or payload.get("updated_at_utc")
                or payload.get("observed_at_utc")
            )
            dt = self._parse_ts(ts)
            age_minutes = None
            if dt is not None:
                age_minutes = (now - dt.astimezone(timezone.utc)).total_seconds() / 60.0
                if age_minutes > 1440:
                    stale.append(name)

            freshness[name] = {
                "present": bool(payload),
                "timestamp": ts,
                "age_minutes": (
                    round(age_minutes, 3)
                    if age_minutes is not None else None
                ),
            }

            if not payload:
                missing.append(name)

        brain = sources["brain"]
        top = brain.get("multi_factor_ranking", {}).get("top_candidate") or {}
        required_fields = {
            "brain_score": brain.get(
                "explainable_final_decision", {}
            ).get("brain_score"),
            "candidate_symbol": top.get("symbol"),
            "candidate_confidence": top.get("confidence"),
            "candidate_consensus": top.get("consensus_score"),
            "reward_risk": top.get("reward_risk"),
        }

        missing_fields = [
            key for key, value in required_fields.items()
            if value in (None, "")
        ]

        issues = []
        if missing:
            issues.append("SOURCE_MISSING")
        if stale:
            issues.append("SOURCE_STALE")
        if missing_fields:
            issues.append("REQUIRED_FIELD_MISSING")

        status = "PASS" if not issues else "WARN"

        return {
            "status": status,
            "freshness": freshness,
            "missing_sources": missing,
            "stale_sources": stale,
            "missing_required_fields": missing_fields,
            "issue_codes": issues,
            "enforced": False,
            "order_effect": "NONE",
        }

    def v32_signal_conflict_detector(self) -> dict[str, Any]:
        brain = self._brain()
        execution = self._execution()
        market = self._market()

        final_decision = str(
            brain.get("explainable_final_decision", {}).get(
                "decision", ""
            )
        )
        mtf_direction = str(
            brain.get("multi_timeframe_ai", {}).get(
                "direction", "UNKNOWN"
            )
        )
        timing = str(
            execution.get("v26_entry_timing_quality", {}).get(
                "timing_state", "UNKNOWN"
            )
        )
        market_context = str(
            market.get("market_context_summary", {}).get(
                "market_entry_context", "UNKNOWN"
            )
        )

        conflicts = []

        if mtf_direction == "BULLISH" and final_decision == "SKIP_OBSERVATION":
            conflicts.append("BULLISH_MTF_VS_SKIP")
        if market_context == "UNFAVORABLE" and final_decision in {
            "BUY_OR_WATCH_OBSERVATION",
            "STRONG_BUY_OBSERVATION",
        }:
            conflicts.append("BUY_VS_UNFAVORABLE_MARKET")
        if timing in {"POOR_WINDOW", "WAIT_FOR_BETTER_ALIGNMENT"} and final_decision == "STRONG_BUY_OBSERVATION":
            conflicts.append("STRONG_BUY_VS_WEAK_TIMING")

        conflict_score = min(len(conflicts) / 3.0, 1.0)
        level = (
            "HIGH" if conflict_score >= 0.67
            else "MEDIUM" if conflict_score > 0
            else "LOW"
        )

        return {
            "status": "PASS",
            "conflict_level": level,
            "conflict_score": round(conflict_score, 6),
            "conflicts": conflicts,
            "final_decision": final_decision,
            "multi_timeframe_direction": mtf_direction,
            "timing_state": timing,
            "market_context": market_context,
            "enforced": False,
            "order_effect": "NONE",
        }

    def v33_score_sensitivity(self) -> dict[str, Any]:
        brain = self._brain()
        top = brain.get("multi_factor_ranking", {}).get("top_candidate") or {}
        base = self._float(top.get("score"), 0.0)

        components = top.get("components", {})
        numeric = {
            key: self._float(value)
            for key, value in components.items()
            if isinstance(value, (int, float))
        }

        scenarios = []
        for pct in (-0.10, -0.05, 0.05, 0.10):
            shifted = {}
            delta_sum = 0.0
            for key, value in numeric.items():
                if "penalty" in key:
                    nv = min(max(value * (1.0 + pct), 0.0), 1.0)
                    delta_sum -= (nv - value)
                else:
                    nv = min(max(value * (1.0 + pct), 0.0), 1.0)
                    delta_sum += (nv - value) / max(len(numeric), 1)
                shifted[key] = round(nv, 6)

            simulated = min(max(base + delta_sum, 0.0), 1.0)
            scenarios.append({
                "shock_pct": pct,
                "simulated_score": round(simulated, 6),
                "components": shifted,
            })

        values = [row["simulated_score"] for row in scenarios] + [base]
        spread = max(values) - min(values) if values else 0.0

        if spread <= 0.10:
            stability = "HIGH"
        elif spread <= 0.20:
            stability = "MEDIUM"
        else:
            stability = "LOW"

        return {
            "status": "PASS",
            "base_score": round(base, 6),
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
            "score_spread": round(spread, 6),
            "sensitivity_stability": stability,
            "automatic_threshold_changes": False,
        }

    def v34_decision_repeatability(self) -> dict[str, Any]:
        rows = self._load_jsonl(
            self.root / "runtime/ai_brain_v4/ai_brain_ledger.jsonl"
        )
        if not rows:
            return {
                "status": "COLLECTING_DATA",
                "sample_count": 0,
                "repeatability_ratio": None,
                "decision_frequency": {},
                "stable": None,
            }

        decisions = []
        for row in rows[-50:]:
            decision = row.get(
                "explainable_final_decision", {}
            ).get("decision")
            if decision:
                decisions.append(str(decision))

        freq: dict[str, int] = {}
        for decision in decisions:
            freq[decision] = freq.get(decision, 0) + 1

        if decisions:
            dominant = max(freq.values())
            ratio = dominant / len(decisions)
        else:
            ratio = None

        stable = None if ratio is None else ratio >= 0.70

        return {
            "status": "PASS" if decisions else "COLLECTING_DATA",
            "sample_count": len(decisions),
            "repeatability_ratio": (
                round(ratio, 6) if ratio is not None else None
            ),
            "decision_frequency": freq,
            "stable": stable,
            "automatic_decision_lock": False,
        }

    def v35_robustness_gate(self) -> dict[str, Any]:
        dq = self.v31_data_quality_audit()
        conflicts = self.v32_signal_conflict_detector()
        sensitivity = self.v33_score_sensitivity()
        repeatability = self.v34_decision_repeatability()

        checks = {
            "data_quality_not_failed": dq["status"] in {"PASS", "WARN"},
            "no_high_signal_conflict": conflicts["conflict_level"] != "HIGH",
            "score_sensitivity_not_low": (
                sensitivity["sensitivity_stability"] != "LOW"
            ),
            "repeatability_sample_available": (
                repeatability["sample_count"] >= 5
            ),
            "broker_write_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for v in checks.values() if v)
        blockers = [k for k, v in checks.items() if not v]

        if passed == len(checks):
            status = "ROBUSTNESS_REVIEW_READY"
        else:
            status = "COLLECTING_OR_REVIEW_REQUIRED"

        return {
            "status": status,
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "blockers": blockers,
            "deployment_effect": "ADVISORY_ONLY",
            "live_submission_enabled": False,
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/decision_robustness_v31_v35"

        result = {
            "stage": "DATA_QUALITY_DECISION_ROBUSTNESS_V31_TO_V35",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v31_data_quality_audit": self.v31_data_quality_audit(),
            "v32_signal_conflict_detector": (
                self.v32_signal_conflict_detector()
            ),
            "v33_score_sensitivity": self.v33_score_sensitivity(),
            "v34_decision_repeatability": (
                self.v34_decision_repeatability()
            ),
            "v35_robustness_gate": self.v35_robustness_gate(),
            "generated_at_utc": self._now(),
        }

        self._write(
            runtime / "latest_robustness_report.json",
            result,
        )
        self._append(
            runtime / "robustness_ledger.jsonl",
            result,
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "data_quality_status": result[
                "v31_data_quality_audit"
            ]["status"],
            "signal_conflict_level": result[
                "v32_signal_conflict_detector"
            ]["conflict_level"],
            "sensitivity_stability": result[
                "v33_score_sensitivity"
            ]["sensitivity_stability"],
            "repeatability_status": result[
                "v34_decision_repeatability"
            ]["status"],
            "robustness_gate": result[
                "v35_robustness_gate"
            ]["status"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }

        self._write(
            runtime / "daily_robustness_summary.json",
            summary,
        )

        return result
