from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TradeOutcomeAuditDataPack:
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

    def _v4(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/closed_trade_calibration_v4/"
              "latest_calibration_report.json"
        )

    def _execution(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/execution_quality_v26_v30/"
              "latest_execution_quality_report.json"
        )

    def _brain(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/ai_brain_v4/"
              "latest_ai_brain_report.json"
        )

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    def v36_trade_lifecycle_normalizer(self) -> dict[str, Any]:
        rows = self._v4().get("linked_outcomes", [])
        if not isinstance(rows, list):
            rows = []

        normalized = []
        for row in rows:
            normalized.append({
                "trade_id": str(
                    row.get("trade_id", row.get("order_id", ""))
                ),
                "symbol": str(row.get("symbol", "")).upper(),
                "side": str(row.get("side", "")).upper(),
                "entry_time": row.get("entry_time"),
                "exit_time": row.get("exit_time"),
                "entry_price": self._float(row.get("entry_price")),
                "exit_price": self._float(row.get("exit_price")),
                "quantity": self._float(
                    row.get("quantity", row.get("qty"))
                ),
                "realized_pl": self._float(row.get("realized_pl")),
                "realized_return": self._float(
                    row.get("realized_return")
                ),
                "candidate_confidence": row.get(
                    "candidate", {}
                ).get("confidence"),
                "candidate_consensus": row.get(
                    "candidate", {}
                ).get("consensus_score"),
                "candidate_reward_risk": row.get(
                    "candidate", {}
                ).get("reward_risk"),
                "guard_action": row.get(
                    "candidate", {}
                ).get("guard_action"),
            })

        return {
            "status": "PASS" if normalized else "COLLECTING_DATA",
            "trade_count": len(normalized),
            "trades": normalized,
            "source": "V4_LINKED_OUTCOMES",
            "broker_write_performed": False,
        }

    def v37_mfe_mae_analyzer(self) -> dict[str, Any]:
        lifecycle = self.v36_trade_lifecycle_normalizer()
        analyzed = []

        for trade in lifecycle["trades"]:
            # MFE/MAE requires path data. We only use explicitly present values.
            source = None
            for raw in self._v4().get("linked_outcomes", []):
                if str(raw.get("trade_id", "")) == trade["trade_id"]:
                    source = raw
                    break

            source = source or {}
            mfe = source.get("mfe")
            mae = source.get("mae")
            mfe_pct = source.get("mfe_pct")
            mae_pct = source.get("mae_pct")

            analyzed.append({
                "trade_id": trade["trade_id"],
                "symbol": trade["symbol"],
                "mfe": mfe,
                "mae": mae,
                "mfe_pct": mfe_pct,
                "mae_pct": mae_pct,
                "path_data_available": any(
                    value is not None
                    for value in [mfe, mae, mfe_pct, mae_pct]
                ),
            })

        available = sum(
            1 for row in analyzed if row["path_data_available"]
        )

        return {
            "status": "PASS" if available else "COLLECTING_PATH_DATA",
            "trade_count": len(analyzed),
            "path_data_available_count": available,
            "trades": analyzed,
            "fabricated_path_data": False,
        }

    def v38_hold_time_post_exit_review(self) -> dict[str, Any]:
        lifecycle = self.v36_trade_lifecycle_normalizer()
        rows = self._v4().get("linked_outcomes", [])
        reviews = []

        def parse_ts(value):
            if not value:
                return None
            try:
                return datetime.fromisoformat(
                    str(value).replace("Z", "+00:00")
                )
            except Exception:
                return None

        raw_by_id = {
            str(row.get("trade_id", row.get("order_id", ""))): row
            for row in rows
            if isinstance(row, dict)
        }

        for trade in lifecycle["trades"]:
            entry = parse_ts(trade["entry_time"])
            exit_ = parse_ts(trade["exit_time"])
            hold_minutes = None

            if entry and exit_:
                hold_minutes = (
                    exit_ - entry
                ).total_seconds() / 60.0

            raw = raw_by_id.get(trade["trade_id"], {})

            reviews.append({
                "trade_id": trade["trade_id"],
                "symbol": trade["symbol"],
                "hold_minutes": (
                    round(hold_minutes, 3)
                    if hold_minutes is not None else None
                ),
                "post_exit_1h_return": raw.get(
                    "post_exit_1h_return"
                ),
                "post_exit_4h_return": raw.get(
                    "post_exit_4h_return"
                ),
                "post_exit_close_return": raw.get(
                    "post_exit_close_return"
                ),
                "post_exit_data_available": any(
                    raw.get(key) is not None
                    for key in [
                        "post_exit_1h_return",
                        "post_exit_4h_return",
                        "post_exit_close_return",
                    ]
                ),
            })

        post_exit_count = sum(
            1 for row in reviews if row["post_exit_data_available"]
        )

        return {
            "status": (
                "PASS"
                if reviews else "COLLECTING_DATA"
            ),
            "trade_count": len(reviews),
            "post_exit_data_available_count": post_exit_count,
            "reviews": reviews,
            "fabricated_post_exit_data": False,
        }

    def v39_execution_quality_record(self) -> dict[str, Any]:
        execution = self._execution()
        brain = self._brain()
        guard = self._guard()

        timing = execution.get(
            "v26_entry_timing_quality", {}
        )
        slippage = execution.get(
            "v27_slippage_liquidity_risk", {}
        )
        notional = execution.get(
            "v28_adaptive_notional_recommendation", {}
        )

        top = brain.get(
            "multi_factor_ranking", {}
        ).get("top_candidate") or {}

        record = {
            "captured_at_utc": self._now(),
            "symbol": str(
                top.get(
                    "symbol",
                    guard.get("candidate", {}).get("symbol", ""),
                )
            ).upper(),
            "timing_score": timing.get("timing_score"),
            "timing_state": timing.get("timing_state"),
            "slippage_risk": slippage.get("slippage_risk"),
            "estimated_slippage_bps": slippage.get(
                "estimated_slippage_bps"
            ),
            "liquidity_score": slippage.get("liquidity_score"),
            "suggested_notional_shadow": notional.get(
                "suggested_notional"
            ),
            "brain_score": brain.get(
                "explainable_final_decision", {}
            ).get("brain_score"),
            "actual_order_changed": False,
            "broker_write_performed": False,
        }

        useful = any(
            record.get(key) not in (None, "")
            for key in [
                "symbol",
                "timing_score",
                "slippage_risk",
                "brain_score",
            ]
        )

        return {
            "status": "PASS" if useful else "COLLECTING_DATA",
            "record": record,
            "order_effect": "NONE",
        }

    def v40_daily_trade_audit_dataset(self) -> dict[str, Any]:
        lifecycle = self.v36_trade_lifecycle_normalizer()
        mfe_mae = self.v37_mfe_mae_analyzer()
        hold = self.v38_hold_time_post_exit_review()
        execution = self.v39_execution_quality_record()

        dataset = {
            "dataset_version": "V40.0",
            "generated_at_utc": self._now(),
            "trade_count": lifecycle["trade_count"],
            "closed_trades": lifecycle["trades"],
            "mfe_mae_records": mfe_mae["trades"],
            "hold_time_post_exit_records": hold["reviews"],
            "latest_execution_quality": execution["record"],
            "read_only": True,
            "broker_write_performed": False,
        }

        readiness_checks = {
            "closed_trade_data_present": lifecycle["trade_count"] > 0,
            "mfe_mae_path_data_present": (
                mfe_mae["path_data_available_count"] > 0
            ),
            "post_exit_data_present": (
                hold["post_exit_data_available_count"] > 0
            ),
            "execution_quality_present": (
                execution["status"] == "PASS"
            ),
        }

        passed = sum(
            1 for value in readiness_checks.values()
            if value
        )

        return {
            "status": (
                "AUDIT_DATA_READY"
                if passed == len(readiness_checks)
                else "PARTIAL_DATA_COLLECTION"
            ),
            "dataset": dataset,
            "readiness_checks": readiness_checks,
            "passed_checks": passed,
            "total_checks": len(readiness_checks),
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/trade_outcome_audit_v36_v40"

        result = {
            "stage": "TRADE_OUTCOME_AUDIT_DATA_V36_TO_V40",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v36_trade_lifecycle_normalizer": (
                self.v36_trade_lifecycle_normalizer()
            ),
            "v37_mfe_mae_analyzer": (
                self.v37_mfe_mae_analyzer()
            ),
            "v38_hold_time_post_exit_review": (
                self.v38_hold_time_post_exit_review()
            ),
            "v39_execution_quality_record": (
                self.v39_execution_quality_record()
            ),
            "v40_daily_trade_audit_dataset": (
                self.v40_daily_trade_audit_dataset()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(
            runtime / "latest_trade_audit_report.json",
            result,
        )
        self._append(
            runtime / "trade_audit_ledger.jsonl",
            result,
        )

        self._write(
            runtime / "daily_trade_audit_dataset.json",
            result["v40_daily_trade_audit_dataset"]["dataset"],
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "trade_count": result[
                "v36_trade_lifecycle_normalizer"
            ]["trade_count"],
            "mfe_mae_available": result[
                "v37_mfe_mae_analyzer"
            ]["path_data_available_count"],
            "post_exit_available": result[
                "v38_hold_time_post_exit_review"
            ]["post_exit_data_available_count"],
            "audit_dataset_status": result[
                "v40_daily_trade_audit_dataset"
            ]["status"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }

        self._write(
            runtime / "daily_trade_audit_summary.json",
            summary,
        )

        return result
