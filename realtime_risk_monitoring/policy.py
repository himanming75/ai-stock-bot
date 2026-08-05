from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .models import D


@dataclass(frozen=True)
class RiskPolicy:
    max_daily_loss_percent: Decimal
    max_drawdown_percent: Decimal
    max_single_position_percent: Decimal
    max_gross_exposure_percent: Decimal
    max_net_exposure_percent: Decimal
    min_cash_reserve_percent: Decimal
    max_buying_power_utilization_percent: Decimal
    warning_score: Decimal
    critical_score: Decimal

    @classmethod
    def load(cls, path: Path) -> "RiskPolicy":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return cls(
            max_daily_loss_percent=D(data["max_daily_loss_percent"]),
            max_drawdown_percent=D(data["max_drawdown_percent"]),
            max_single_position_percent=D(data["max_single_position_percent"]),
            max_gross_exposure_percent=D(data["max_gross_exposure_percent"]),
            max_net_exposure_percent=D(data["max_net_exposure_percent"]),
            min_cash_reserve_percent=D(data["min_cash_reserve_percent"]),
            max_buying_power_utilization_percent=D(
                data["max_buying_power_utilization_percent"]
            ),
            warning_score=D(data["warning_score"]),
            critical_score=D(data["critical_score"]),
        )
