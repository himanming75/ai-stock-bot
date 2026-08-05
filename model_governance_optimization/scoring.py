from __future__ import annotations
from statistics import mean, pstdev

def metric(candidate: dict, key: str, default=0.0) -> float:
    try:
        return float(candidate.get(key, default))
    except (TypeError, ValueError):
        return default

def governance_score(candidate: dict) -> dict:
    folds = [float(x) for x in candidate.get("fold_scores", [])]
    fold_mean = mean(folds) if folds else 0.0
    fold_std = pstdev(folds) if len(folds) > 1 else 0.0
    train = metric(candidate, "train_score")
    test = metric(candidate, "test_score")
    overfit_gap = max(train - test, 0.0)
    drawdown = abs(metric(candidate, "max_drawdown"))
    ece = abs(metric(candidate, "calibration_error"))
    turnover = max(metric(candidate, "turnover"), 0.0)
    sample_count = int(candidate.get("sample_count", 0))

    score = (
        test * 0.35
        + fold_mean * 0.20
        + metric(candidate, "sharpe_like") * 0.12
        + metric(candidate, "balanced_accuracy") * 0.15
        - drawdown * 0.08
        - ece * 0.05
        - fold_std * 0.03
        - overfit_gap * 0.05
        - turnover * 0.02
    )

    warnings = []
    if sample_count < 50:
        warnings.append("LOW_SAMPLE_COUNT")
    if overfit_gap > 0.12:
        warnings.append("OVERFIT_GAP_HIGH")
    if fold_std > 0.15:
        warnings.append("FOLD_INSTABILITY_HIGH")
    if drawdown > 0.20:
        warnings.append("DRAWDOWN_HIGH")
    if ece > 0.20:
        warnings.append("CALIBRATION_ERROR_HIGH")

    return {
        "governance_score": round(score, 8),
        "fold_mean": round(fold_mean, 8),
        "fold_std": round(fold_std, 8),
        "overfit_gap": round(overfit_gap, 8),
        "warnings": warnings,
        "stable": not warnings,
    }
