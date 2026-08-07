from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from market_context_v16_v20.service import MarketContextIntelligence
from market_regime_v66_v70.service import MarketRegimeEnvironmentPack
from ai_strategy_ensemble_v5.service import StrategyEnsembleShadowReview
from decision_robustness_v31_v35.service import DataQualityDecisionRobustness
from shadow_intelligence_v6_v10.service import ShadowIntelligencePack
from shadow_counterfactual_v76_v80.service import ShadowParameterCounterfactualPack
from performance_intelligence_v21_v25.service import PerformanceIntelligencePack
from ai_market_memory_v3.service import MarketMemoryExitIntelligence


class AIResearchShadowIntegration:
    """
    Existing-AI orchestration only.
    No broker writes, no order submission, no trading-configuration mutation,
    no automatic strategy promotion, and no parameter mutation.
    """

    MODULES: tuple[tuple[str, type], ...] = (
        ("market_context", MarketContextIntelligence),
        ("market_regime", MarketRegimeEnvironmentPack),
        ("strategy_ensemble", StrategyEnsembleShadowReview),
        ("decision_robustness", DataQualityDecisionRobustness),
        ("shadow_intelligence", ShadowIntelligencePack),
        ("counterfactual", ShadowParameterCounterfactualPack),
        ("performance_intelligence", PerformanceIntelligencePack),
        ("market_memory_exit", MarketMemoryExitIntelligence),
    )

    def __init__(self, project_root: Path) -> None:
        self.root = Path(project_root)
        self.runtime = self.root / "runtime" / "ai_research_shadow_integration"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _status(payload: Any) -> str:
        if isinstance(payload, dict):
            return str(payload.get("status") or payload.get("stage") or "PASS")
        return "PASS"

    @staticmethod
    def _extract(payload: dict[str, Any], paths: list[tuple[str, ...]]) -> Any:
        for path in paths:
            cur: Any = payload
            ok = True
            for key in path:
                if not isinstance(cur, dict) or key not in cur:
                    ok = False
                    break
                cur = cur[key]
            if ok:
                return cur
        return None

    def _run_module(self, name: str, cls: type) -> dict[str, Any]:
        try:
            result = cls(self.root).run()
            return {
                "name": name,
                "status": "PASS",
                "module_status": self._status(result),
                "result": result,
                "error": None,
            }
        except Exception as exc:
            return {
                "name": name,
                "status": "ADVISORY_ERROR",
                "module_status": "ERROR",
                "result": {},
                "error": f"{type(exc).__name__}: {exc}",
            }

    @staticmethod
    def _module_result(modules: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
        row = modules.get(name, {})
        payload = row.get("result", {})
        return payload if isinstance(payload, dict) else {}

    def _comparison(self, modules: dict[str, dict[str, Any]]) -> dict[str, Any]:
        context = self._module_result(modules, "market_context")
        regime = self._module_result(modules, "market_regime")
        ensemble = self._module_result(modules, "strategy_ensemble")
        robustness = self._module_result(modules, "decision_robustness")
        shadow = self._module_result(modules, "shadow_intelligence")
        counter = self._module_result(modules, "counterfactual")
        perf = self._module_result(modules, "performance_intelligence")
        memory = self._module_result(modules, "market_memory_exit")

        return {
            "market_context": self._extract(context, [
                ("market_context_summary",),
            ]),
            "market_regime": self._extract(regime, [
                ("v66_market_regime_classifier", "regime"),
                ("market_regime",),
            ]),
            "ensemble_decision": self._extract(ensemble, [
                ("decision_comparison",),
                ("ensemble",),
            ]),
            "robustness_gate": self._extract(robustness, [
                ("v35_robustness_gate",),
                ("robustness_gate",),
            ]),
            "shadow_explanation": self._extract(shadow, [
                ("explainable_ai_report",),
                ("explainable_ai",),
                ("v10_explainable_ai",),
            ]),
            "counterfactual_summary": self._extract(counter, [
                ("v80_counterfactual_validation_summary",),
            ]),
            "performance_summary": self._extract(perf, [
                ("performance_summary",),
                ("summary",),
            ]),
            "market_memory": self._extract(memory, [
                ("market_memory",),
            ]),
            "exit_intelligence": self._extract(memory, [
                ("exit_intelligence",),
            ]),
        }

    def _normalized_decision(self, modules: dict[str, dict[str, Any]]) -> dict[str, Any]:
        ensemble = self._module_result(modules, "strategy_ensemble")
        regime = self._module_result(modules, "market_regime")
        context = self._module_result(modules, "market_context")
        robustness = self._module_result(modules, "decision_robustness")
        shadow = self._module_result(modules, "shadow_intelligence")

        candidate = ensemble.get("candidate", {}) if isinstance(ensemble, dict) else {}
        ensemble_row = ensemble.get("ensemble", {}) if isinstance(ensemble, dict) else {}
        regime_row = regime.get("v66_market_regime_classifier", {}) if isinstance(regime, dict) else {}
        context_row = context.get("market_context_summary", {}) if isinstance(context, dict) else {}
        gate = robustness.get("v35_robustness_gate", {}) if isinstance(robustness, dict) else {}
        explain = shadow.get("explainable_ai_report", {}) if isinstance(shadow, dict) else {}

        return {
            "symbol": candidate.get("symbol"),
            "original_side": candidate.get("side"),
            "candidate_confidence": candidate.get("confidence"),
            "candidate_consensus_score": candidate.get("consensus_score"),
            "candidate_reward_risk": candidate.get("reward_risk"),
            "ensemble_decision": ensemble_row.get("decision"),
            "ensemble_weighted_score": ensemble_row.get("weighted_score"),
            "ensemble_agreement_ratio": ensemble_row.get("agreement_ratio"),
            "market_regime": regime_row.get("regime"),
            "regime_confidence": regime_row.get("regime_confidence"),
            "market_entry_context": context_row.get("market_entry_context"),
            "robustness_status": gate.get("status"),
            "robustness_passed_checks": gate.get("passed_checks"),
            "robustness_total_checks": gate.get("total_checks"),
            "explainable_headline": explain.get("headline"),
            "positive_reasons": explain.get("positive_reasons", []),
            "caution_reasons": explain.get("caution_reasons", []),
            "enforced": False,
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        module_rows = [self._run_module(name, cls) for name, cls in self.MODULES]
        module_map = {row["name"]: row for row in module_rows}
        advisory_errors = [
            {"name": row["name"], "error": row["error"]}
            for row in module_rows
            if row["status"] != "PASS"
        ]

        report = {
            "stage": "AI_RESEARCH_SHADOW_INTEGRATION",
            "status": "PASS" if not advisory_errors else "PASS_WITH_ADVISORY_ERRORS",
            "mode": "RESEARCH_SHADOW_ONLY",
            "generated_at_utc": self._now(),
            "module_count": len(module_rows),
            "module_results": module_rows,
            "normalized_decision": self._normalized_decision(module_map),
            "decision_comparison": self._comparison(module_map),
            "advisory_errors": advisory_errors,
            "contracts": {
                "broker_write_performed": False,
                "order_submission_performed": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "trading_configuration_changed": False,
                "strategy_parameters_changed": False,
                "automatic_strategy_promotion": False,
                "automatic_parameter_mutation": False,
                "actual_paper_decision_path_changed": False,
                "live_auto_enable": False,
            },
        }

        self.runtime.mkdir(parents=True, exist_ok=True)
        latest = self.runtime / "latest_ai_research_shadow_report.json"
        ledger = self.runtime / "ai_research_shadow_ledger.jsonl"
        latest.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(report, default=str) + "\n")
        return report
