from __future__ import annotations
import math
from statistics import mean, pstdev


def safe_mean(values):
    values = list(values)
    return mean(values) if values else 0.0


def directional_label(value: float, threshold: float = 0.0) -> int:
    return 1 if value > threshold else 0


def classification_metrics(rows: list[dict], threshold: float) -> dict:
    tp = fp = tn = fn = 0
    for row in rows:
        predicted = directional_label(float(row["final_score"]), threshold)
        actual = directional_label(float(row["forward_return"]), 0.0)
        if predicted == 1 and actual == 1:
            tp += 1
        elif predicted == 1 and actual == 0:
            fp += 1
        elif predicted == 0 and actual == 0:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )
    balanced_accuracy = (recall + specificity) / 2.0

    return {
        "threshold": threshold,
        "count": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": round(accuracy, 8),
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "specificity": round(specificity, 8),
        "f1": round(f1, 8),
        "balanced_accuracy": round(balanced_accuracy, 8),
    }


def calibration_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {
            "brier_score": 0.0,
            "expected_calibration_error": 0.0,
            "buckets": [],
        }

    buckets = []
    brier_terms = []
    ece = 0.0

    for row in rows:
        probability = max(
            0.0,
            min(1.0, float(row.get("confidence", 0.0)) / 100.0),
        )
        actual = 1.0 if float(row["forward_return"]) > 0 else 0.0
        brier_terms.append((probability - actual) ** 2)

    for lower in range(0, 100, 10):
        upper = lower + 10
        bucket_rows = [
            row for row in rows
            if lower <= float(row.get("confidence", 0.0)) < upper
            or (
                upper == 100
                and float(row.get("confidence", 0.0)) == 100
            )
        ]
        if not bucket_rows:
            continue

        average_confidence = safe_mean(
            float(row.get("confidence", 0.0)) / 100.0
            for row in bucket_rows
        )
        observed_rate = safe_mean(
            1.0 if float(row["forward_return"]) > 0 else 0.0
            for row in bucket_rows
        )
        weight = len(bucket_rows) / len(rows)
        gap = abs(average_confidence - observed_rate)
        ece += weight * gap

        buckets.append({
            "lower": lower,
            "upper": upper,
            "count": len(bucket_rows),
            "average_confidence": round(average_confidence, 8),
            "observed_positive_rate": round(observed_rate, 8),
            "calibration_gap": round(gap, 8),
        })

    return {
        "brier_score": round(safe_mean(brier_terms), 8),
        "expected_calibration_error": round(ece, 8),
        "buckets": buckets,
    }


def strategy_returns(rows: list[dict], threshold: float) -> list[float]:
    returns = []
    for row in rows:
        score = float(row["final_score"])
        forward = float(row["forward_return"])
        if score > threshold:
            returns.append(forward)
        elif score < -threshold:
            returns.append(-forward)
        else:
            returns.append(0.0)
    return returns


def performance_metrics(returns: list[float]) -> dict:
    if not returns:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "average_return": 0.0,
            "cumulative_return": 0.0,
            "volatility": 0.0,
            "sharpe_like": 0.0,
            "maximum_drawdown": 0.0,
            "profit_factor": 0.0,
        }

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    gains = []
    losses = []

    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = (equity - peak) / peak if peak else 0.0
        max_drawdown = min(max_drawdown, drawdown)
        if value > 0:
            gains.append(value)
        elif value < 0:
            losses.append(abs(value))

    average = safe_mean(returns)
    volatility = pstdev(returns) if len(returns) > 1 else 0.0
    sharpe_like = average / volatility if volatility else 0.0
    profit_factor = (
        sum(gains) / sum(losses)
        if losses and sum(losses) > 0
        else (float("inf") if gains else 0.0)
    )

    return {
        "trade_count": sum(1 for value in returns if value != 0),
        "win_rate": round(
            sum(1 for value in returns if value > 0)
            / max(sum(1 for value in returns if value != 0), 1),
            8,
        ),
        "average_return": round(average, 8),
        "cumulative_return": round(equity - 1.0, 8),
        "volatility": round(volatility, 8),
        "sharpe_like": round(sharpe_like, 8),
        "maximum_drawdown": round(max_drawdown, 8),
        "profit_factor": (
            "INF" if math.isinf(profit_factor)
            else round(profit_factor, 8)
        ),
    }
