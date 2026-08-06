from __future__ import annotations


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def build_signal_feedback(
    analyses: list[dict],
    realized_returns: dict[str, list[float]],
) -> dict:
    rows = []
    calibration_errors = []
    directional_hits = []

    for item in analyses:
        symbol = item["symbol"]
        expected = float(item.get("expected_return", 0.0))
        confidence = float(
            item.get("confidence_calibration", {}).get(
                "calibrated_confidence", 0.0
            )
        )
        actual_series = realized_returns.get(symbol, [])
        realized = _safe_mean(actual_series)
        error = abs(expected - realized)
        calibration_errors.append(error)

        expected_direction = 0 if expected == 0 else (1 if expected > 0 else -1)
        realized_direction = 0 if realized == 0 else (1 if realized > 0 else -1)
        hit = expected_direction == realized_direction
        directional_hits.append(1.0 if hit else 0.0)

        rows.append({
            "symbol": symbol,
            "expected_return": round(expected, 6),
            "realized_return": round(realized, 6),
            "absolute_error": round(error, 6),
            "directional_hit": hit,
            "original_confidence": round(confidence, 6),
            "feedback_adjustment": round(max(-0.20, 0.10 - error * 4.0), 6),
            "model_weight_update_enabled": False,
        })

    mae = _safe_mean(calibration_errors)
    directional_accuracy = _safe_mean(directional_hits)
    if directional_accuracy >= 0.70 and mae <= 0.02:
        health = "IMPROVING"
    elif directional_accuracy >= 0.45 and mae <= 0.05:
        health = "STABLE"
    else:
        health = "DEGRADING"

    return {
        "rows": rows,
        "mean_absolute_error": round(mae, 6),
        "directional_accuracy": round(directional_accuracy, 6),
        "feedback_health": health,
        "feedback_mode": "OFFLINE_OBSERVATION_ONLY",
        "automatic_model_update_enabled": False,
        "live_learning_enabled": False,
    }
