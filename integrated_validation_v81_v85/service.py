from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class IntegratedValidationDailyReview:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/integrated_validation_v81_v85"
        self.runtime.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

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

    def _paths(self) -> dict[str, Path]:
        return {
            "v41_v45_outcome": (
                self.root / "runtime/closed_trade_outcome_v41_v45/"
                "latest_closed_trade_outcome_report.json"
            ),
            "v46_v50_analytics": (
                self.root / "runtime/closed_trade_analytics_v46_v50/"
                "latest_closed_trade_analytics_report.json"
            ),
            "v51_v55_eod": (
                self.root / "runtime/closed_trade_eod_v51_v55/"
                "latest_eod_pipeline_report.json"
            ),
            "v56_v60_classification": (
                self.root / "runtime/trade_classification_v56_v60/"
                "latest_trade_classification_report.json"
            ),
            "v61_v65_integrity": (
                self.root / "runtime/data_integrity_v61_v65/"
                "latest_data_integrity_report.json"
            ),
            "v66_v70_regime": (
                self.root / "runtime/market_regime_v66_v70/"
                "latest_market_regime_report.json"
            ),
            "v71_v75_reliability": (
                self.root / "runtime/operational_reliability_v71_v75/"
                "latest_operational_reliability_report.json"
            ),
            "v76_v80_counterfactual": (
                self.root / "runtime/shadow_counterfactual_v76_v80/"
                "latest_counterfactual_report.json"
            ),
        }

    def v81_cross_module_data_flow_check(self) -> dict[str, Any]:
        modules = {}
        missing = []
        bad_status = []

        for name, path in self._paths().items():
            payload = self._load(path)
            exists = bool(payload)
            status = payload.get("status") if payload else None
            modules[name] = {
                "path": str(path),
                "exists": exists,
                "status": status,
            }
            if not exists:
                missing.append(name)
            elif status not in {
                "PASS",
                "WAITING_FOR_MARKET_CLOSE",
                "COLLECTING_DATA",
            }:
                bad_status.append(name)

        return {
            "status": "PASS" if not bad_status else "WARN",
            "modules": modules,
            "missing_modules": missing,
            "bad_status_modules": bad_status,
            "broker_write_performed": False,
            "order_effect": "NONE",
        }

    def v82_closed_trade_propagation_check(self) -> dict[str, Any]:
        outcome = self._load(
            self._paths()["v41_v45_outcome"]
        )
        analytics = self._load(
            self._paths()["v46_v50_analytics"]
        )
        classification = self._load(
            self._paths()["v56_v60_classification"]
        )
        integrity = self._load(
            self._paths()["v61_v65_integrity"]
        )
        counterfactual = self._load(
            self._paths()["v76_v80_counterfactual"]
        )

        counts = {
            "outcome_closed_trade_count": (
                outcome.get("v42_fifo_round_trip_builder", {})
                .get("closed_trade_count")
            ),
            "analytics_trade_count": (
                analytics.get("v47_core_performance_metrics", {})
                .get("trade_count")
            ),
            "classification_trade_count": (
                classification.get("v56_closed_trade_classifier", {})
                .get("trade_count")
            ),
            "integrity_record_count": (
                integrity.get("v61_integrity_check", {})
                .get("record_count")
            ),
            "counterfactual_trade_count": (
                counterfactual.get(
                    "v80_counterfactual_validation_summary", {}
                ).get("trade_count")
            ),
        }

        available = [
            value for value in counts.values()
            if isinstance(value, int)
        ]
        consistent = (
            len(set(available)) <= 1
            if available else True
        )

        return {
            "status": "PASS" if consistent else "WARN",
            "counts": counts,
            "consistent": consistent,
            "closed_trade_sample_present": (
                any(value > 0 for value in available)
                if available else False
            ),
            "broker_write_performed": False,
        }

    def v83_daily_validation_snapshot(self) -> dict[str, Any]:
        integrity = self._load(
            self._paths()["v61_v65_integrity"]
        )
        regime = self._load(
            self._paths()["v66_v70_regime"]
        )
        reliability = self._load(
            self._paths()["v71_v75_reliability"]
        )
        analytics = self._load(
            self._paths()["v46_v50_analytics"]
        )

        snapshot = {
            "generated_at_utc": self._now(),
            "data_health": (
                integrity.get("v65_data_health_summary", {})
                .get("status")
            ),
            "data_health_score": (
                integrity.get("v65_data_health_summary", {})
                .get("health_score")
            ),
            "market_regime": (
                regime.get("v66_market_regime_classifier", {})
                .get("regime")
            ),
            "market_environment_health": (
                regime.get("v70_environment_health_summary", {})
                .get("status")
            ),
            "operational_health": (
                reliability.get("v75_operational_health_report", {})
                .get("status")
            ),
            "operational_health_score": (
                reliability.get("v75_operational_health_report", {})
                .get("health_score")
            ),
            "closed_trade_count": (
                analytics.get("v47_core_performance_metrics", {})
                .get("trade_count")
            ),
            "readiness_status": (
                analytics.get("v50_readiness_gate", {})
                .get("status")
            ),
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }

        useful = any(
            value not in (None, "")
            for key, value in snapshot.items()
            if key not in {
                "generated_at_utc",
                "broker_write_performed",
                "etrade_live_write_enabled",
            }
        )

        return {
            "status": "PASS" if useful else "COLLECTING_DATA",
            "snapshot": snapshot,
            "broker_write_performed": False,
        }

    def v84_multiday_collection_readiness(self) -> dict[str, Any]:
        ledgers = {
            "outcome_runs": self._load_jsonl(
                self.root / "runtime/closed_trade_outcome_v41_v45/"
                "collector_run_ledger.jsonl"
            ),
            "analytics_runs": self._load_jsonl(
                self.root / "runtime/closed_trade_analytics_v46_v50/"
                "closed_trade_analytics_ledger.jsonl"
            ),
            "integrity_runs": self._load_jsonl(
                self.root / "runtime/data_integrity_v61_v65/"
                "data_integrity_ledger.jsonl"
            ),
            "regime_runs": self._load_jsonl(
                self.root / "runtime/market_regime_v66_v70/"
                "market_regime_ledger.jsonl"
            ),
            "reliability_runs": self._load_jsonl(
                self.root / "runtime/operational_reliability_v71_v75/"
                "operational_reliability_ledger.jsonl"
            ),
            "counterfactual_runs": self._load_jsonl(
                self.root / "runtime/shadow_counterfactual_v76_v80/"
                "counterfactual_ledger.jsonl"
            ),
        }

        counts = {name: len(rows) for name, rows in ledgers.items()}

        checks = {
            "integrity_history_present": counts["integrity_runs"] >= 1,
            "regime_history_present": counts["regime_runs"] >= 1,
            "reliability_history_present": counts["reliability_runs"] >= 1,
            "analytics_history_present": counts["analytics_runs"] >= 1,
            "counterfactual_history_present": counts["counterfactual_runs"] >= 1,
            "three_day_history_available": all(
                count >= 3
                for name, count in counts.items()
                if name != "outcome_runs"
            ),
        }

        passed = sum(1 for value in checks.values() if value)

        if checks["three_day_history_available"]:
            status = "MULTIDAY_READY"
        else:
            status = "COLLECTING_HISTORY"

        return {
            "status": status,
            "run_counts": counts,
            "checks": checks,
            "passed_checks": passed,
            "total_checks": len(checks),
            "broker_write_performed": False,
        }

    def v85_integrated_validation_summary(self) -> dict[str, Any]:
        flow = self.v81_cross_module_data_flow_check()
        propagation = self.v82_closed_trade_propagation_check()
        daily = self.v83_daily_validation_snapshot()
        multiday = self.v84_multiday_collection_readiness()

        checks = {
            "cross_module_flow_not_failed": (
                flow["status"] in {"PASS", "WARN"}
            ),
            "closed_trade_counts_consistent": propagation["consistent"],
            "daily_snapshot_available": (
                daily["status"] in {"PASS", "COLLECTING_DATA"}
            ),
            "multiday_collection_not_blocked": (
                multiday["status"] in {
                    "MULTIDAY_READY",
                    "COLLECTING_HISTORY",
                }
            ),
            "broker_write_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)

        if passed == len(checks):
            status = (
                "INTEGRATED_VALIDATION_READY"
                if multiday["status"] == "MULTIDAY_READY"
                else "INTEGRATED_VALIDATION_COLLECTING_HISTORY"
            )
        else:
            status = "REVIEW_REQUIRED"

        return {
            "status": status,
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "closed_trade_sample_present": (
                propagation["closed_trade_sample_present"]
            ),
            "multiday_status": multiday["status"],
            "live_submission_enabled": False,
            "deployment_effect": "ADVISORY_ONLY",
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "INTEGRATED_VALIDATION_DAILY_REVIEW_V81_TO_V85",
            "status": "PASS",
            "mode": "READ_ONLY_INTEGRATED_VALIDATION",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v81_cross_module_data_flow_check": (
                self.v81_cross_module_data_flow_check()
            ),
            "v82_closed_trade_propagation_check": (
                self.v82_closed_trade_propagation_check()
            ),
            "v83_daily_validation_snapshot": (
                self.v83_daily_validation_snapshot()
            ),
            "v84_multiday_collection_readiness": (
                self.v84_multiday_collection_readiness()
            ),
            "v85_integrated_validation_summary": (
                self.v85_integrated_validation_summary()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_integrated_validation_report.json",
            result,
        )
        self._append(
            self.runtime / "integrated_validation_ledger.jsonl",
            result,
        )
        self._write(
            self.runtime / "daily_validation_snapshot.json",
            result["v83_daily_validation_snapshot"]["snapshot"],
        )

        return result
