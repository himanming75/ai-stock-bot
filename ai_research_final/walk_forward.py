from __future__ import annotations
from decimal import Decimal
from typing import Any


class WalkForwardValidator:
    def validate(
        self,
        *,
        returns: list[Decimal],
        train_size: int,
        test_size: int,
    ) -> dict[str, Any]:
        if train_size <= 0 or test_size <= 0:
            raise ValueError("WINDOW_SIZES_MUST_BE_POSITIVE")
        if len(returns) < train_size + test_size:
            raise ValueError("INSUFFICIENT_RETURNS")

        windows = []
        start = 0
        while start + train_size + test_size <= len(returns):
            train = returns[start:start + train_size]
            test = returns[start + train_size:start + train_size + test_size]
            train_mean = sum(train, Decimal("0")) / Decimal(len(train))
            test_mean = sum(test, Decimal("0")) / Decimal(len(test))
            windows.append({
                "window": len(windows) + 1,
                "train_start": start,
                "train_end": start + train_size - 1,
                "test_start": start + train_size,
                "test_end": start + train_size + test_size - 1,
                "train_mean_return": str(train_mean.quantize(Decimal("0.000001"))),
                "test_mean_return": str(test_mean.quantize(Decimal("0.000001"))),
                "test_positive": test_mean > 0,
            })
            start += test_size

        positive = sum(1 for row in windows if row["test_positive"])
        return {
            "window_count": len(windows),
            "positive_test_windows": positive,
            "positive_window_ratio": str(
                (Decimal(positive) / Decimal(len(windows))).quantize(
                    Decimal("0.0001")
                )
                if windows else Decimal("0")
            ),
            "windows": windows,
            "actual_strategy_promotion_performed": False,
        }
