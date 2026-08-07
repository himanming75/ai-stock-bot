from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ShadowParameterCounterfactualPack:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/shadow_counterfactual_v76_v80"
        self.runtime.mkdir(parents=True, exist_ok=True)

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
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except Exception:
                    pass
        except Exception:
            pass
        return rows

    @staticmethod
    def _write(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")

    def _trades(self) -> list[dict[str, Any]]:
        return self._load_jsonl(
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )

    def _brain(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/ai_brain_v4/"
              "latest_ai_brain_report.json"
        )

    def _execution(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/execution_quality_v26_v30/"
              "latest_execution_quality_report.json"
        )

    def v76_parameter_scenario_generator(self) -> dict[str, Any]:
        scenarios = {
            "entry_confidence_thresholds": [0.70, 0.75, 0.80, 0.85, 0.90],
            "reward_risk_thresholds": [1.2, 1.5, 1.8, 2.0, 2.5],
            "notional_limits": [25, 50, 75, 100],
            "hold_time_minutes": [15, 30, 60, 120, 240],
            "stop_loss_pct": [0.01, 0.015, 0.02, 0.025, 0.03],
        }

        return {
            "status": "PASS",
            "scenarios": scenarios,
            "actual_parameter_changes": False,
            "automatic_parameter_changes": False,
            "broker_write_performed": False,
        }

    def v77_entry_threshold_counterfactual(self) -> dict[str, Any]:
        trades = self._trades()
        scenarios = self.v76_parameter_scenario_generator()["scenarios"]
        thresholds = scenarios["entry_confidence_thresholds"]

        results = []
        for threshold in thresholds:
            eligible = []
            for trade in trades:
                confidence = trade.get("candidate", {}).get("confidence")
                if confidence is None:
                    confidence = trade.get("signal_confidence")
                if confidence is None:
                    continue
                if self._float(confidence) >= threshold:
                    eligible.append(trade)

            pnls = [self._float(t.get("realized_pl")) for t in eligible]
            count = len(pnls)
            wins = sum(1 for x in pnls if x > 0)

            results.append({
                "confidence_threshold": threshold,
                "eligible_trade_count": count,
                "win_rate": round(wins / count, 6) if count else None,
                "total_realized_pl": round(sum(pnls), 8),
                "average_realized_pl": (
                    round(sum(pnls) / count, 8)
                    if count else None
                ),
            })

        status = "PASS" if trades else "COLLECTING_DATA"

        return {
            "status": status,
            "trade_count": len(trades),
            "scenario_results": results,
            "actual_entry_filter_changed": False,
            "order_effect": "NONE",
        }

    def v78_exit_hold_counterfactual(self) -> dict[str, Any]:
        trades = self._trades()
        hold_scenarios = self.v76_parameter_scenario_generator()[
            "scenarios"
        ]["hold_time_minutes"]

        # Only use explicit post-exit/path data when available.
        evaluated = []
        path_available = 0

        for hold in hold_scenarios:
            scenario_pnls = []
            usable = 0

            for trade in trades:
                base_pnl = self._float(trade.get("realized_pl"))
                alt_return = None

                if hold <= 60:
                    alt_return = trade.get("post_exit_1h_return")
                elif hold <= 240:
                    alt_return = trade.get("post_exit_4h_return")

                if alt_return is None:
                    continue

                exit_price = self._float(trade.get("exit_price"))
                qty = self._float(
                    trade.get("quantity", trade.get("qty"))
                )

                if exit_price <= 0 or qty <= 0:
                    continue

                alt_pnl_delta = (
                    exit_price
                    * qty
                    * self._float(alt_return)
                )

                scenario_pnls.append(base_pnl + alt_pnl_delta)
                usable += 1

            if usable:
                path_available += usable

            evaluated.append({
                "hold_minutes": hold,
                "usable_trade_count": usable,
                "simulated_total_pl": (
                    round(sum(scenario_pnls), 8)
                    if usable else None
                ),
                "simulated_average_pl": (
                    round(sum(scenario_pnls) / usable, 8)
                    if usable else None
                ),
            })

        return {
            "status": (
                "PASS" if path_available > 0
                else "COLLECTING_PATH_DATA"
            ),
            "trade_count": len(trades),
            "path_data_uses": path_available,
            "scenario_results": evaluated,
            "fabricated_path_data": False,
            "actual_exit_logic_changed": False,
            "order_effect": "NONE",
        }

    def v79_notional_risk_scenarios(self) -> dict[str, Any]:
        trades = self._trades()
        notionals = self.v76_parameter_scenario_generator()[
            "scenarios"
        ]["notional_limits"]

        results = []
        for notional in notionals:
            simulated = []

            for trade in trades:
                entry_price = self._float(trade.get("entry_price"))
                exit_price = self._float(trade.get("exit_price"))

                if entry_price <= 0 or exit_price <= 0:
                    continue

                quantity = notional / entry_price
                pnl = (exit_price - entry_price) * quantity

                simulated.append(pnl)

            count = len(simulated)
            results.append({
                "notional": notional,
                "usable_trade_count": count,
                "simulated_total_pl": (
                    round(sum(simulated), 8)
                    if count else None
                ),
                "simulated_average_pl": (
                    round(sum(simulated) / count, 8)
                    if count else None
                ),
                "simulated_max_single_loss": (
                    round(min(simulated), 8)
                    if simulated else None
                ),
            })

        return {
            "status": "PASS" if trades else "COLLECTING_DATA",
            "trade_count": len(trades),
            "scenario_results": results,
            "actual_notional_changed": False,
            "actual_risk_limits_changed": False,
            "broker_write_performed": False,
        }

    def v80_counterfactual_validation_summary(self) -> dict[str, Any]:
        entry = self.v77_entry_threshold_counterfactual()
        hold = self.v78_exit_hold_counterfactual()
        notional = self.v79_notional_risk_scenarios()

        trade_count = len(self._trades())

        checks = {
            "closed_trade_sample_present": trade_count > 0,
            "entry_scenarios_generated": len(
                entry["scenario_results"]
            ) > 0,
            "hold_scenarios_generated": len(
                hold["scenario_results"]
            ) > 0,
            "notional_scenarios_generated": len(
                notional["scenario_results"]
            ) > 0,
            "no_actual_parameter_changes": True,
            "broker_write_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)

        if trade_count == 0:
            status = "COLLECTING_DATA"
        elif passed == len(checks):
            status = "COUNTERFACTUAL_REVIEW_READY"
        else:
            status = "PARTIAL_REVIEW_READY"

        return {
            "status": status,
            "trade_count": trade_count,
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "actual_parameter_changes": False,
            "automatic_parameter_changes": False,
            "deployment_effect": "ADVISORY_ONLY",
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "SHADOW_PARAMETER_COUNTERFACTUAL_V76_TO_V80",
            "status": "PASS",
            "mode": "READ_ONLY_COUNTERFACTUAL",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v76_parameter_scenario_generator": (
                self.v76_parameter_scenario_generator()
            ),
            "v77_entry_threshold_counterfactual": (
                self.v77_entry_threshold_counterfactual()
            ),
            "v78_exit_hold_counterfactual": (
                self.v78_exit_hold_counterfactual()
            ),
            "v79_notional_risk_scenarios": (
                self.v79_notional_risk_scenarios()
            ),
            "v80_counterfactual_validation_summary": (
                self.v80_counterfactual_validation_summary()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_counterfactual_report.json",
            result,
        )
        self._append(
            self.runtime / "counterfactual_ledger.jsonl",
            result,
        )

        self._write(
            self.runtime / "counterfactual_scenario_dataset.json",
            {
                "generated_at_utc": self._now(),
                "entry_thresholds": result[
                    "v77_entry_threshold_counterfactual"
                ]["scenario_results"],
                "exit_hold": result[
                    "v78_exit_hold_counterfactual"
                ]["scenario_results"],
                "notional": result[
                    "v79_notional_risk_scenarios"
                ]["scenario_results"],
                "read_only": True,
                "actual_parameter_changes": False,
                "broker_write_performed": False,
            },
        )

        return result
