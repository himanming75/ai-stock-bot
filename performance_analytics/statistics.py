from __future__ import annotations

from decimal import Decimal
from math import sqrt

from .models import D, ONE, ZERO, HUNDRED, ratio, text


def decimal_mean(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return sum(values, ZERO) / Decimal(len(values))


def decimal_std(values: list[Decimal]) -> Decimal:
    if len(values) < 2:
        return ZERO
    mean = decimal_mean(values)
    variance = sum(
        ((value - mean) ** 2 for value in values),
        ZERO,
    ) / Decimal(len(values) - 1)
    return Decimal(str(sqrt(float(variance))))


def period_returns(points: list[dict]) -> list[dict]:
    records = []
    for previous, current in zip(points, points[1:]):
        previous_equity = previous["equity"]
        current_equity = current["equity"]
        value = ratio(
            current_equity - previous_equity,
            previous_equity,
        )
        records.append(
            {
                "start": previous["generated_at"],
                "end": current["generated_at"],
                "return_decimal": value,
                "return_percent": value * HUNDRED,
            }
        )
    return records


def equity_curve(points: list[dict]) -> list[dict]:
    if not points:
        return []
    first = points[0]["equity"]
    peak = first
    curve = []
    for point in points:
        equity = point["equity"]
        peak = max(peak, equity)
        cumulative_return = ratio(equity - first, first) * HUNDRED
        drawdown = ratio(peak - equity, peak) * HUNDRED
        curve.append(
            {
                "generated_at": point["generated_at"],
                "equity": text(equity),
                "cumulative_return_percent": text(cumulative_return),
                "drawdown_percent": text(drawdown),
            }
        )
    return curve


def streaks(values: list[Decimal]) -> dict:
    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0
    for value in values:
        if value > ZERO:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif value < ZERO:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
        else:
            current_wins = 0
            current_losses = 0
    return {
        "max_consecutive_positive_periods": max_wins,
        "max_consecutive_negative_periods": max_losses,
    }


def aggregate_by_period(points: list[dict], mode: str) -> list[dict]:
    groups = {}
    for point in points:
        timestamp = point["timestamp"]
        if mode == "day":
            key = timestamp.date().isoformat()
        elif mode == "week":
            year, week, _ = timestamp.isocalendar()
            key = f"{year}-W{week:02d}"
        elif mode == "month":
            key = f"{timestamp.year:04d}-{timestamp.month:02d}"
        else:
            raise ValueError(mode)
        groups.setdefault(key, []).append(point)

    rows = []
    for key in sorted(groups):
        group = groups[key]
        start = group[0]["equity"]
        end = group[-1]["equity"]
        rows.append(
            {
                "period": key,
                "start_equity": text(start),
                "end_equity": text(end),
                "pnl": text(end - start),
                "return_percent": text(
                    ratio(end - start, start) * HUNDRED
                ),
                "observation_count": len(group),
            }
        )
    return rows
