from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DataIntegrityRecoveryPack:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/data_integrity_v61_v65"
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
    def _load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[int]]:
        if not path.exists():
            return [], []
        rows = []
        malformed = []
        try:
            for idx, line in enumerate(
                path.read_text(encoding="utf-8-sig").splitlines(),
                start=1,
            ):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        rows.append(obj)
                    else:
                        malformed.append(idx)
                except Exception:
                    malformed.append(idx)
        except Exception:
            return [], [-1]
        return rows, malformed

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

    @staticmethod
    def _sha256(path: Path) -> str | None:
        if not path.exists():
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _closed_trade_ledger(self) -> Path:
        return (
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )

    def v61_integrity_check(self) -> dict[str, Any]:
        ledger = self._closed_trade_ledger()
        rows, malformed = self._load_jsonl(ledger)

        ids = [str(r.get("trade_id", "")).strip() for r in rows]
        duplicate_ids = sorted(
            trade_id
            for trade_id, count in Counter(ids).items()
            if trade_id and count > 1
        )
        missing_id_indices = [
            idx + 1
            for idx, trade_id in enumerate(ids)
            if not trade_id
        ]

        required_fields = [
            "trade_id",
            "symbol",
            "entry_time",
            "exit_time",
            "realized_pl",
        ]
        incomplete_records = []
        for idx, row in enumerate(rows, start=1):
            missing = [
                field
                for field in required_fields
                if row.get(field) in (None, "")
            ]
            if missing:
                incomplete_records.append({
                    "record_index": idx,
                    "trade_id": row.get("trade_id"),
                    "missing_fields": missing,
                })

        issues = []
        if malformed:
            issues.append("MALFORMED_JSONL")
        if duplicate_ids:
            issues.append("DUPLICATE_TRADE_ID")
        if missing_id_indices:
            issues.append("MISSING_TRADE_ID")
        if incomplete_records:
            issues.append("INCOMPLETE_RECORD")

        return {
            "status": "PASS" if not issues else "WARN",
            "ledger_exists": ledger.exists(),
            "record_count": len(rows),
            "malformed_line_numbers": malformed,
            "duplicate_trade_ids": duplicate_ids,
            "missing_trade_id_records": missing_id_indices,
            "incomplete_records": incomplete_records,
            "issue_codes": issues,
            "ledger_sha256": self._sha256(ledger),
            "broker_write_performed": False,
        }

    def v62_incremental_processor(self) -> dict[str, Any]:
        ledger = self._closed_trade_ledger()
        rows, malformed = self._load_jsonl(ledger)
        checkpoint_path = self.runtime / "incremental_checkpoint.json"
        checkpoint = self._load(checkpoint_path)

        previous_ids = set(checkpoint.get("processed_trade_ids", []))
        current_ids = [
            str(row.get("trade_id", "")).strip()
            for row in rows
            if str(row.get("trade_id", "")).strip()
        ]

        new_rows = [
            row for row in rows
            if str(row.get("trade_id", "")).strip() not in previous_ids
        ]

        new_ids = [
            str(row.get("trade_id", "")).strip()
            for row in new_rows
            if str(row.get("trade_id", "")).strip()
        ]

        processed_ids = sorted(previous_ids.union(current_ids))

        new_ledger = self.runtime / "incremental_new_trades.jsonl"
        with new_ledger.open("w", encoding="utf-8") as f:
            for row in new_rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")

        next_checkpoint = {
            "updated_at_utc": self._now(),
            "processed_trade_ids": processed_ids,
            "processed_trade_count": len(processed_ids),
            "source_ledger_sha256": self._sha256(ledger),
        }
        self._write(checkpoint_path, next_checkpoint)

        return {
            "status": "PASS" if not malformed else "WARN",
            "source_trade_count": len(rows),
            "previously_processed_count": len(previous_ids),
            "new_trade_count": len(new_rows),
            "new_trade_ids": new_ids,
            "checkpoint_path": str(checkpoint_path),
            "incremental_ledger_path": str(new_ledger),
            "broker_write_performed": False,
        }

    def v63_daily_consistency_audit(self) -> dict[str, Any]:
        integrity = self.v61_integrity_check()
        analytics = self._load(
            self.root
            / "runtime/closed_trade_analytics_v46_v50/"
              "latest_closed_trade_analytics_report.json"
        )
        classification = self._load(
            self.root
            / "runtime/trade_classification_v56_v60/"
              "latest_trade_classification_report.json"
        )

        ledger_count = integrity["record_count"]
        analytics_count = (
            analytics.get("v47_core_performance_metrics", {})
            .get("trade_count")
        )
        classification_count = (
            classification.get("v56_closed_trade_classifier", {})
            .get("trade_count")
        )

        checks = {
            "ledger_integrity_not_warn": integrity["status"] == "PASS",
            "analytics_count_matches": (
                analytics_count is None or analytics_count == ledger_count
            ),
            "classification_count_matches": (
                classification_count is None
                or classification_count == ledger_count
            ),
        }

        mismatches = [
            name for name, passed in checks.items() if not passed
        ]

        return {
            "status": "PASS" if not mismatches else "WARN",
            "ledger_trade_count": ledger_count,
            "analytics_trade_count": analytics_count,
            "classification_trade_count": classification_count,
            "checks": checks,
            "mismatches": mismatches,
            "broker_write_performed": False,
        }

    def v64_recovery_checkpoint(self) -> dict[str, Any]:
        ledger = self._closed_trade_ledger()
        rows, malformed = self._load_jsonl(ledger)

        checkpoint = {
            "created_at_utc": self._now(),
            "source_ledger_path": str(ledger),
            "source_ledger_exists": ledger.exists(),
            "source_ledger_sha256": self._sha256(ledger),
            "record_count": len(rows),
            "malformed_line_numbers": malformed,
            "last_trade_id": (
                rows[-1].get("trade_id") if rows else None
            ),
            "recovery_mode": "READ_ONLY_CHECKPOINT",
            "broker_write_performed": False,
        }

        checkpoint_path = self.runtime / "recovery_checkpoint.json"
        self._write(checkpoint_path, checkpoint)

        previous = self._load(
            self.runtime / "previous_recovery_checkpoint.json"
        )

        drift = {
            "previous_record_count": previous.get("record_count"),
            "current_record_count": checkpoint["record_count"],
            "previous_sha256": previous.get("source_ledger_sha256"),
            "current_sha256": checkpoint["source_ledger_sha256"],
        }

        self._write(
            self.runtime / "previous_recovery_checkpoint.json",
            checkpoint,
        )

        return {
            "status": "PASS",
            "checkpoint_path": str(checkpoint_path),
            "checkpoint": checkpoint,
            "drift": drift,
            "automatic_restore_performed": False,
            "broker_write_performed": False,
        }

    def v65_data_health_summary(self) -> dict[str, Any]:
        integrity = self.v61_integrity_check()
        incremental = self.v62_incremental_processor()
        consistency = self.v63_daily_consistency_audit()
        recovery = self.v64_recovery_checkpoint()

        checks = {
            "ledger_integrity_pass": integrity["status"] == "PASS",
            "incremental_processor_not_blocked": (
                incremental["status"] in {"PASS", "WARN"}
            ),
            "daily_consistency_pass": consistency["status"] == "PASS",
            "recovery_checkpoint_created": (
                recovery["checkpoint"]["source_ledger_exists"]
                or recovery["checkpoint"]["record_count"] == 0
            ),
            "broker_write_off": True,
            "etrade_live_write_off": True,
        }

        passed = sum(1 for value in checks.values() if value)
        score = round(passed / len(checks) * 100.0, 2)

        if score == 100:
            status = "HEALTHY"
        elif score >= 80:
            status = "REVIEW_RECOMMENDED"
        else:
            status = "ATTENTION_REQUIRED"

        return {
            "status": status,
            "health_score": score,
            "passed_checks": passed,
            "total_checks": len(checks),
            "checks": checks,
            "integrity_issue_codes": integrity["issue_codes"],
            "new_trade_count": incremental["new_trade_count"],
            "consistency_mismatches": consistency["mismatches"],
            "automatic_repair_performed": False,
            "automatic_restore_performed": False,
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "DATA_INTEGRITY_RECOVERY_V61_TO_V65",
            "status": "PASS",
            "mode": "READ_ONLY_DATA_GOVERNANCE",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v61_integrity_check": self.v61_integrity_check(),
            "v62_incremental_processor": self.v62_incremental_processor(),
            "v63_daily_consistency_audit": (
                self.v63_daily_consistency_audit()
            ),
            "v64_recovery_checkpoint": self.v64_recovery_checkpoint(),
            "v65_data_health_summary": self.v65_data_health_summary(),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_data_integrity_report.json",
            result,
        )
        self._append(
            self.runtime / "data_integrity_ledger.jsonl",
            result,
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "record_count": result[
                "v61_integrity_check"
            ]["record_count"],
            "new_trade_count": result[
                "v62_incremental_processor"
            ]["new_trade_count"],
            "integrity_status": result[
                "v61_integrity_check"
            ]["status"],
            "consistency_status": result[
                "v63_daily_consistency_audit"
            ]["status"],
            "health_status": result[
                "v65_data_health_summary"
            ]["status"],
            "health_score": result[
                "v65_data_health_summary"
            ]["health_score"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }

        self._write(
            self.runtime / "daily_data_health_summary.json",
            summary,
        )

        return result
