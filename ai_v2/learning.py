from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any


class PerformanceLearningLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(
        self,
        *,
        strategy_id: str,
        symbol: str,
        pnl: Decimal,
        return_pct: Decimal,
        holding_minutes: int,
        exit_reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "record_type": "STRATEGY_OUTCOME",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "strategy_id": strategy_id,
            "symbol": symbol,
            "pnl": str(pnl),
            "return_pct": str(return_pct),
            "holding_minutes": holding_minutes,
            "exit_reason": exit_reason,
            "metadata": metadata or {},
            "model_training_performed": False,
            "broker_action_performed": False,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def summarize(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "trade_count": 0,
                "win_rate": "0",
                "profit_factor": "0",
                "average_return_pct": "0",
                "maximum_drawdown": "0",
            }

        records = [
            json.loads(line)
            for line in self.path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
            if line.strip()
        ]
        pnl_values = [Decimal(item["pnl"]) for item in records]
        returns = [Decimal(item["return_pct"]) for item in records]
        wins = sum(1 for value in pnl_values if value > 0)
        gross_profit = sum(
            (value for value in pnl_values if value > 0),
            Decimal("0"),
        )
        gross_loss = abs(sum(
            (value for value in pnl_values if value < 0),
            Decimal("0"),
        ))
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else (Decimal("999") if gross_profit > 0 else Decimal("0"))
        )

        equity = Decimal("0")
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        for pnl in pnl_values:
            equity += pnl
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)

        count = len(records)
        return {
            "trade_count": count,
            "win_rate": str(
                (Decimal(wins) / Decimal(count)).quantize(
                    Decimal("0.0001")
                )
                if count else Decimal("0")
            ),
            "profit_factor": str(
                profit_factor.quantize(Decimal("0.0001"))
            ),
            "average_return_pct": str(
                (sum(returns, Decimal("0")) / Decimal(count)).quantize(
                    Decimal("0.0001")
                )
                if count else Decimal("0")
            ),
            "maximum_drawdown": str(
                max_drawdown.quantize(Decimal("0.0001"))
            ),
            "actual_model_training_performed": False,
        }
