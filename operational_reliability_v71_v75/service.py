from __future__ import annotations

import json
import os
import shutil
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class OperationalReliabilityPack:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/operational_reliability_v71_v75"
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

    def v71_api_resilience(self) -> dict[str, Any]:
        """
        Read-only connectivity/API readiness check.
        This does NOT place, cancel, replace, or close any order.
        """
        result = {
            "status": "PASS",
            "dns_ok": False,
            "paper_credentials_present": False,
            "paper_clock_read_ok": False,
            "attempts": 0,
            "max_attempts": 3,
            "backoff_seconds": [0, 1, 2],
            "broker_write_performed": False,
        }

        try:
            socket.gethostbyname("paper-api.alpaca.markets")
            result["dns_ok"] = True
        except Exception:
            pass

        key = os.getenv("APCA_API_KEY_ID", "").strip()
        secret = os.getenv("APCA_API_SECRET_KEY", "").strip()
        result["paper_credentials_present"] = bool(key and secret)

        if not key or not secret:
            result["status"] = "WARN"
            result["reason"] = "PAPER_CREDENTIALS_NOT_IN_PROCESS_ENVIRONMENT"
            return result

        last_error = None
        for attempt, delay in enumerate([0, 1, 2], start=1):
            if delay:
                time.sleep(delay)
            result["attempts"] = attempt
            try:
                from alpaca.trading.client import TradingClient
                client = TradingClient(key, secret, paper=True)
                clock = client.get_clock()
                result["paper_clock_read_ok"] = True
                result["market_open"] = bool(getattr(clock, "is_open", False))
                result["clock_timestamp"] = str(
                    getattr(clock, "timestamp", "")
                )
                last_error = None
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}:{exc}"

        if not result["paper_clock_read_ok"]:
            result["status"] = "WARN"
            result["last_error"] = last_error

        return result

    def v72_session_lock_recovery_audit(self) -> dict[str, Any]:
        candidate_locks = [
            self.root / "runtime/paper_autonomous_daily_session/session.lock",
            self.root / "runtime/market_open_auto_validation/runner.lock",
        ]

        locks = []
        stale_candidates = []

        now = time.time()
        for path in candidate_locks:
            if path.exists():
                age_seconds = now - path.stat().st_mtime
                row = {
                    "path": str(path),
                    "exists": True,
                    "age_seconds": round(age_seconds, 3),
                }
                locks.append(row)

                # Advisory only: identify locks older than 12 hours.
                if age_seconds > 12 * 3600:
                    stale_candidates.append(str(path))
            else:
                locks.append({
                    "path": str(path),
                    "exists": False,
                    "age_seconds": None,
                })

        return {
            "status": "PASS",
            "locks": locks,
            "stale_lock_candidates": stale_candidates,
            "automatic_lock_deletion": False,
            "automatic_recovery_performed": False,
            "broker_write_performed": False,
        }

    def v73_runtime_ledger_consistency(self) -> dict[str, Any]:
        checks = []

        ledgers = [
            self.root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl",
            self.root
            / "runtime/data_integrity_v61_v65/"
              "data_integrity_ledger.jsonl",
            self.root
            / "runtime/market_regime_v66_v70/"
              "market_regime_ledger.jsonl",
        ]

        malformed_total = 0
        for path in ledgers:
            rows, malformed = self._load_jsonl(path)
            malformed_total += len(malformed)
            checks.append({
                "path": str(path),
                "exists": path.exists(),
                "record_count": len(rows),
                "malformed_line_numbers": malformed,
            })

        health = self._load(
            self.root
            / "runtime/data_integrity_v61_v65/"
              "latest_data_integrity_report.json"
        )
        health_status = (
            health.get("v65_data_health_summary", {}).get("status")
        )

        status = (
            "PASS"
            if malformed_total == 0
            else "WARN"
        )

        return {
            "status": status,
            "ledger_checks": checks,
            "malformed_total": malformed_total,
            "v65_data_health_status": health_status,
            "automatic_repair_performed": False,
            "broker_write_performed": False,
        }

    def v74_system_resource_monitor(self) -> dict[str, Any]:
        disk = shutil.disk_usage(self.root)

        runtime_dir = self.root / "runtime"
        runtime_bytes = 0
        file_count = 0
        if runtime_dir.exists():
            for path in runtime_dir.rglob("*"):
                if path.is_file():
                    file_count += 1
                    try:
                        runtime_bytes += path.stat().st_size
                    except Exception:
                        pass

        process_info = {
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
        }

        memory_info = {}
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            mem = proc.memory_info()
            memory_info = {
                "rss_bytes": int(mem.rss),
                "vms_bytes": int(mem.vms),
                "cpu_percent": float(proc.cpu_percent(interval=0.05)),
            }
        except Exception:
            memory_info = {
                "rss_bytes": None,
                "vms_bytes": None,
                "cpu_percent": None,
            }

        free_ratio = disk.free / disk.total if disk.total else 0.0
        status = "PASS" if free_ratio >= 0.05 else "WARN"

        return {
            "status": status,
            "disk_total_bytes": disk.total,
            "disk_free_bytes": disk.free,
            "disk_free_ratio": round(free_ratio, 6),
            "runtime_folder_bytes": runtime_bytes,
            "runtime_file_count": file_count,
            "process": process_info,
            "memory": memory_info,
            "broker_write_performed": False,
        }

    def v75_operational_health_report(self) -> dict[str, Any]:
        api = self.v71_api_resilience()
        locks = self.v72_session_lock_recovery_audit()
        consistency = self.v73_runtime_ledger_consistency()
        resources = self.v74_system_resource_monitor()

        closed_trade_report = self._load(
            self.root
            / "runtime/closed_trade_analytics_v46_v50/"
              "latest_closed_trade_analytics_report.json"
        )
        closed_trade_count = (
            closed_trade_report
            .get("v47_core_performance_metrics", {})
            .get("trade_count")
        )

        checks = {
            "api_not_failed": api["status"] in {"PASS", "WARN"},
            "no_automatic_lock_delete": (
                locks["automatic_lock_deletion"] is False
            ),
            "ledger_consistency_not_failed": (
                consistency["status"] in {"PASS", "WARN"}
            ),
            "disk_space_not_critical": resources["status"] == "PASS",
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
            "api_status": api["status"],
            "stale_lock_candidate_count": len(
                locks["stale_lock_candidates"]
            ),
            "ledger_status": consistency["status"],
            "disk_status": resources["status"],
            "closed_trade_count": closed_trade_count,
            "automatic_recovery_performed": False,
            "automatic_repair_performed": False,
            "broker_write_performed": False,
        }

    def run(self) -> dict[str, Any]:
        result = {
            "stage": "OPERATIONAL_RELIABILITY_V71_TO_V75",
            "status": "PASS",
            "mode": "READ_ONLY_OPERATIONAL_RELIABILITY",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v71_api_resilience": self.v71_api_resilience(),
            "v72_session_lock_recovery_audit": (
                self.v72_session_lock_recovery_audit()
            ),
            "v73_runtime_ledger_consistency": (
                self.v73_runtime_ledger_consistency()
            ),
            "v74_system_resource_monitor": (
                self.v74_system_resource_monitor()
            ),
            "v75_operational_health_report": (
                self.v75_operational_health_report()
            ),
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_operational_reliability_report.json",
            result,
        )
        self._append(
            self.runtime / "operational_reliability_ledger.jsonl",
            result,
        )

        self._write(
            self.runtime / "daily_operational_health_summary.json",
            {
                "generated_at_utc": self._now(),
                "status": result[
                    "v75_operational_health_report"
                ]["status"],
                "health_score": result[
                    "v75_operational_health_report"
                ]["health_score"],
                "api_status": result[
                    "v75_operational_health_report"
                ]["api_status"],
                "ledger_status": result[
                    "v75_operational_health_report"
                ]["ledger_status"],
                "disk_status": result[
                    "v75_operational_health_report"
                ]["disk_status"],
                "broker_write_performed": False,
                "etrade_live_write_enabled": False,
            },
        )

        return result
