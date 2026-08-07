from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def tail_jsonl(path: Path, limit: int = 30) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(
            encoding="utf-8-sig", errors="replace"
        ).splitlines()
    except OSError:
        return []

    result = []
    for line in lines[-limit:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            result.append(value)
    return result


class DashboardReaders:
    def __init__(self, root: Path) -> None:
        self.root = root

    def phase_status(self) -> dict[str, Any]:
        paths = {
            "phase1": self.root / (
                "release/paper_trading_1_0_canonicalizer/"
                "canonicalizer_result.json"
            ),
            "phase2": self.root / (
                "release/phase2_ai_engine_canonicalization/"
                "phase2_ai_engine_result.json"
            ),
            "phase3": self.root / (
                "release/phase3_etrade_live_canonicalization/"
                "phase3_etrade_live_result.json"
            ),
            "phase4": self.root / (
                "release/phase4_single_account_binding/"
                "phase4_single_account_result.json"
            ),
        }
        return {
            name: read_json(path)
            for name, path in paths.items()
        }

    def ai_status(self) -> dict[str, Any]:
        paths = [
            self.root / (
                "release/v11001_12000_multi_timeframe_ai/actual/"
                "multi_timeframe_ai_report_bilingual.json"
            ),
            self.root / (
                "release/phase2_ai_engine_canonicalization/"
                "phase2_ai_engine_result.json"
            ),
        ]
        for path in paths:
            data = read_json(path)
            if data:
                return data
        return {}

    def paper_status(self) -> dict[str, Any]:
        paths = [
            self.root / (
                "release/v14001_15000_paper_autonomous_execution/"
                "paper_preflight.json"
            ),
            self.root / (
                "release/v14001_15000_paper_autonomous_execution/actual/"
                "latest_paper_execution_cycle.json"
            ),
        ]
        merged = {}
        for path in paths:
            merged[path.name] = read_json(path)
        return merged

    def positions(self) -> dict[str, Any]:
        candidates = [
            self.root / (
                "release/realtime_portfolio_monitoring/actual/"
                "latest_portfolio_snapshot.json"
            ),
            self.root / (
                "runtime/realtime_portfolio_monitoring/"
                "latest_portfolio_snapshot.json"
            ),
        ]
        for path in candidates:
            data = read_json(path)
            if data:
                return data
        return {}

    def risk(self) -> dict[str, Any]:
        candidates = [
            self.root / (
                "release/phase3_etrade_live_canonicalization/"
                "phase3_etrade_live_result.json"
            ),
            self.root / (
                "release/v13001_14000_portfolio_optimizer_stress_guardrails/"
                "portfolio_optimizer_certification.json"
            ),
        ]
        for path in candidates:
            data = read_json(path)
            if data:
                return data
        return {}

    def logs(self) -> list[dict[str, Any]]:
        candidates = [
            self.root / (
                "release/v14001_15000_paper_autonomous_execution/actual/"
                "paper_execution_cycle_ledger.jsonl"
            ),
            self.root / (
                "runtime/paper_automation_controller/"
                "controller_events.jsonl"
            ),
        ]
        for path in candidates:
            data = tail_jsonl(path)
            if data:
                return data
        return []
