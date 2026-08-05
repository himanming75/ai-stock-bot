from __future__ import annotations
from .metrics import classification_metrics, performance_metrics, strategy_returns


def walk_forward(
    rows: list[dict],
    *,
    train_size: int,
    test_size: int,
    threshold: float,
) -> list[dict]:
    results = []
    start = 0
    fold = 1

    while start + train_size + test_size <= len(rows):
        train = rows[start:start + train_size]
        test = rows[start + train_size:start + train_size + test_size]

        results.append({
            "fold": fold,
            "train_start": train[0]["timestamp"],
            "train_end": train[-1]["timestamp"],
            "test_start": test[0]["timestamp"],
            "test_end": test[-1]["timestamp"],
            "train_count": len(train),
            "test_count": len(test),
            "classification": classification_metrics(test, threshold),
            "performance": performance_metrics(
                strategy_returns(test, threshold)
            ),
        })

        start += test_size
        fold += 1

    return results
