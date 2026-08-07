from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ClosedTradeEODPipeline:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.runtime = self.root / "runtime/closed_trade_eod_v51_v55"
        self.runtime.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _write(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _python(self) -> Path:
        p = self.root / ".venv/Scripts/python.exe"
        if not p.exists():
            raise RuntimeError(f"VENV_PYTHON_MISSING:{p}")
        return p

    def v51_market_close_detector(self) -> dict[str, Any]:
        key = os.getenv("APCA_API_KEY_ID", "").strip()
        secret = os.getenv("APCA_API_SECRET_KEY", "").strip()

        if not key or not secret:
            return {
                "status": "BLOCKED",
                "reason": "PAPER_CREDENTIALS_MISSING",
                "market_open": None,
                "read_only": True,
            }

        try:
            from alpaca.trading.client import TradingClient
            client = TradingClient(key, secret, paper=True)
            clock = client.get_clock()
        except Exception as exc:
            return {
                "status": "BLOCKED",
                "reason": f"CLOCK_READ_FAILED:{type(exc).__name__}:{exc}",
                "market_open": None,
                "read_only": True,
            }

        return {
            "status": "PASS",
            "market_open": bool(getattr(clock, "is_open", False)),
            "timestamp": str(getattr(clock, "timestamp", "")),
            "next_open": str(getattr(clock, "next_open", "")),
            "next_close": str(getattr(clock, "next_close", "")),
            "read_only": True,
        }

    def _run_script(self, script: str) -> dict[str, Any]:
        path = self.root / script
        if not path.exists():
            return {
                "status": "BLOCKED",
                "reason": f"SCRIPT_MISSING:{script}",
                "exit_code": None,
            }

        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(path),
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

        return {
            "status": "PASS" if cp.returncode == 0 else "BLOCKED",
            "exit_code": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-12000:],
            "script": str(path),
        }

    def v52_refresh_collector(self) -> dict[str, Any]:
        result = self._run_script(
            "RUN_CLOSED_TRADE_OUTCOME_V41_TO_V45.ps1"
        )
        result["broker_write_performed"] = False
        return result

    def v53_refresh_analytics(self) -> dict[str, Any]:
        result = self._run_script(
            "RUN_CLOSED_TRADE_ANALYTICS_V46_TO_V50.ps1"
        )
        result["broker_write_performed"] = False
        return result

    def v54_archive_daily_snapshot(self) -> dict[str, Any]:
        date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        archive_dir = self.runtime / "archive" / date_key
        archive_dir.mkdir(parents=True, exist_ok=True)

        sources = {
            "closed_trade_outcome": (
                self.root
                / "runtime/closed_trade_outcome_v41_v45/"
                  "latest_closed_trade_outcome_report.json"
            ),
            "closed_trade_analytics": (
                self.root
                / "runtime/closed_trade_analytics_v46_v50/"
                  "latest_closed_trade_analytics_report.json"
            ),
        }

        copied = {}
        for name, src in sources.items():
            if src.exists():
                dst = archive_dir / src.name
                dst.write_bytes(src.read_bytes())
                copied[name] = str(dst)

        manifest = {
            "generated_at_utc": self._now(),
            "date_key": date_key,
            "copied": copied,
            "broker_write_performed": False,
        }
        self._write(archive_dir / "archive_manifest.json", manifest)

        return {
            "status": "PASS",
            "archive_dir": str(archive_dir),
            "copied_count": len(copied),
            "copied": copied,
            "broker_write_performed": False,
        }

    def v55_readiness_summary(self) -> dict[str, Any]:
        analytics = self._load(
            self.root
            / "runtime/closed_trade_analytics_v46_v50/"
              "latest_closed_trade_analytics_report.json"
        )
        gate = analytics.get("v50_readiness_gate", {})

        return {
            "status": "PASS" if analytics else "COLLECTING_DATA",
            "readiness_status": gate.get("status", "UNKNOWN"),
            "passed_checks": gate.get("passed_checks"),
            "total_checks": gate.get("total_checks"),
            "blockers": gate.get("blockers", []),
            "live_submission_enabled": False,
            "deployment_effect": "ADVISORY_ONLY",
            "broker_write_performed": False,
        }

    def run(self, allow_during_market: bool = False) -> dict[str, Any]:
        clock = self.v51_market_close_detector()

        if (
            clock.get("status") == "PASS"
            and clock.get("market_open") is True
            and not allow_during_market
        ):
            result = {
                "stage": "CLOSED_TRADE_EOD_PIPELINE_V51_TO_V55",
                "status": "WAITING_FOR_MARKET_CLOSE",
                "mode": "READ_ONLY_EOD",
                "paper_only": True,
                "etrade_live_write_enabled": False,
                "broker_write_performed": False,
                "v51_market_close_detector": clock,
                "generated_at_utc": self._now(),
            }
            self._write(self.runtime / "latest_eod_pipeline_report.json", result)
            return result

        collector = self.v52_refresh_collector()
        analytics = (
            self.v53_refresh_analytics()
            if collector.get("status") == "PASS"
            else {
                "status": "BLOCKED",
                "reason": "COLLECTOR_NOT_PASS",
                "broker_write_performed": False,
            }
        )
        archive = self.v54_archive_daily_snapshot()
        readiness = self.v55_readiness_summary()

        overall = (
            "PASS"
            if collector.get("status") == "PASS"
            and analytics.get("status") == "PASS"
            else "BLOCKED"
        )

        result = {
            "stage": "CLOSED_TRADE_EOD_PIPELINE_V51_TO_V55",
            "status": overall,
            "mode": "READ_ONLY_EOD",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v51_market_close_detector": clock,
            "v52_collector_refresh": collector,
            "v53_analytics_refresh": analytics,
            "v54_daily_archive": archive,
            "v55_readiness_summary": readiness,
            "generated_at_utc": self._now(),
        }

        self._write(
            self.runtime / "latest_eod_pipeline_report.json",
            result,
        )
        return result
