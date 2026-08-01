from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from runtime_engine import JsonRecoveryStore, RecoverySnapshot
from portfolio_engine import PortfolioSnapshot
from risk_engine import RiskSnapshot


class PaperRuntimeRecoveryManager:
    def __init__(self, store: JsonRecoveryStore) -> None:
        self.store = store

    def save(
        self,
        *,
        state: str,
        captured_at: datetime,
        heartbeat_count: int,
        cycle_count: int,
        portfolio: PortfolioSnapshot,
        risk: RiskSnapshot,
    ) -> None:
        self.store.save(RecoverySnapshot(
            state=state,
            captured_at=captured_at,
            heartbeat_count=heartbeat_count,
            scheduler=[],
            metadata={
                "cycle_count": cycle_count,
                "cash": str(portfolio.cash),
                "equity": str(portfolio.equity),
                "market_value": str(portfolio.market_value),
                "realized_pnl": str(portfolio.realized_pnl),
                "unrealized_pnl": str(portfolio.unrealized_pnl),
                "kill_switch_engaged": risk.kill_switch_engaged,
                "emergency_stop_engaged": risk.emergency_stop_engaged,
                "new_buys_allowed": risk.new_buys_allowed,
                "drawdown": str(risk.drawdown),
            },
        ))

    def load_metadata(self) -> dict[str, object] | None:
        snapshot = self.store.load()
        if snapshot is None:
            return None
        return {
            "state": snapshot.state,
            "captured_at": snapshot.captured_at,
            "heartbeat_count": snapshot.heartbeat_count,
            **snapshot.metadata,
        }
