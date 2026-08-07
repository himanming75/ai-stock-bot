from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .readers import read_json, tail_jsonl


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    return []


class OperationConsoleReaders:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ai_candidates(self) -> list[dict[str, Any]]:
        candidates = [
            self.root / (
                "release/v11001_12000_multi_timeframe_ai/actual/"
                "multi_timeframe_ai_report_bilingual.json"
            ),
            self.root / (
                "release/v13001_14000_portfolio_optimizer_stress_guardrails/"
                "actual/portfolio_optimizer_report_bilingual.json"
            ),
        ]
        for path in candidates:
            data = read_json(path)
            analyses = _as_list(data.get("analyses"))
            if analyses:
                result = []
                for item in analyses:
                    confidence = item.get("confidence_calibration", {})
                    result.append({
                        "symbol": item.get("symbol", ""),
                        "action": item.get("action", "HOLD"),
                        "confidence": confidence.get(
                            "calibrated_confidence",
                            item.get("confidence", 0),
                        ),
                        "consensus_score": item.get("consensus_score", 0),
                        "market_regime": item.get("market_regime_2", ""),
                        "structure": item.get("dominant_structure", ""),
                        "expected_return": item.get("expected_return", 0),
                        "expected_risk": item.get("expected_risk", 0),
                        "reward_risk": item.get("reward_risk", 0),
                    })
                return result
        return []

    def watchlist(self) -> list[str]:
        profile = read_json(
            self.root
            / "release/v14001_15000_paper_autonomous_execution/config/"
            "paper_execution_profile.json"
        )
        symbols = profile.get("allowed_symbols", [])
        if isinstance(symbols, list):
            return [str(symbol) for symbol in symbols]
        return []

    def order_history(self) -> list[dict[str, Any]]:
        paths = [
            self.root / (
                "release/v14001_15000_paper_autonomous_execution/actual/"
                "paper_execution_cycle_ledger.jsonl"
            ),
            self.root / (
                "runtime/paper_automation_controller/"
                "controller_events.jsonl"
            ),
        ]
        for path in paths:
            rows = tail_jsonl(path, limit=100)
            orders = []
            for row in rows:
                order = row.get("order")
                if isinstance(order, dict):
                    orders.append({
                        "cycle_id": row.get("cycle_id", ""),
                        "symbol": order.get("symbol", ""),
                        "side": order.get("side", ""),
                        "status": order.get("status", ""),
                        "client_order_id": order.get(
                            "client_order_id", ""
                        ),
                        "paper": order.get("paper", True),
                    })
                elif row.get("paper_order_submitted") is not None:
                    orders.append({
                        "cycle_id": row.get("cycle_id", ""),
                        "symbol": (
                            row.get("selected_candidate") or {}
                        ).get("symbol", ""),
                        "side": (
                            row.get("selected_candidate") or {}
                        ).get("side", ""),
                        "status": row.get("status", ""),
                        "client_order_id": "",
                        "paper": True,
                    })
            if orders:
                return orders[-25:]
        return []

    def fills(self) -> list[dict[str, Any]]:
        candidates = [
            self.root / (
                "release/order_lifecycle_actual_validation/actual/"
                "fill_reconciliation_ledger.jsonl"
            ),
            self.root / (
                "runtime/broker_integration/"
                "fill_reconciliation_ledger.jsonl"
            ),
        ]
        for path in candidates:
            rows = tail_jsonl(path, limit=50)
            if rows:
                return rows[-25:]
        return []

    def account_summary(self) -> dict[str, Any]:
        candidates = [
            self.root / (
                "release/realtime_portfolio_monitoring/actual/"
                "latest_portfolio_snapshot.json"
            ),
            self.root / (
                "runtime/realtime_portfolio_monitoring/"
                "latest_portfolio_snapshot.json"
            ),
            self.root / (
                "release/v14001_15000_paper_autonomous_execution/"
                "paper_preflight.json"
            ),
        ]
        for path in candidates:
            data = read_json(path)
            if data:
                return data
        return {}

    def session_stage(self, operator: dict[str, Any]) -> dict[str, Any]:
        runtime = operator.get("runtime_status", "STOPPED")
        emergency = operator.get("emergency_stop", False)

        if emergency:
            stage = "EMERGENCY_STOP"
            message = "Emergency stop active / 비상 정지 활성"
        elif runtime == "RUNNING":
            stage = "MONITORING"
            message = "Monitoring Paper session / 모의투자 세션 감시"
        elif runtime == "PAUSED":
            stage = "PAUSED"
            message = "Session paused / 세션 일시 정지"
        else:
            stage = "IDLE"
            message = "Waiting to start / 시작 대기"

        return {
            "stage": stage,
            "message": message,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
