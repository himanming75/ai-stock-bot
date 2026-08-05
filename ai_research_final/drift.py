from __future__ import annotations
from decimal import Decimal
from typing import Any


class DriftDetector:
    def compare(
        self,
        *,
        baseline: dict[str, Decimal],
        current: dict[str, Decimal],
        warning_threshold: Decimal,
        critical_threshold: Decimal,
    ) -> dict[str, Any]:
        rows = []
        worst = Decimal("0")
        for feature in sorted(set(baseline) | set(current)):
            base = baseline.get(feature, Decimal("0"))
            now = current.get(feature, Decimal("0"))
            denominator = max(abs(base), Decimal("0.0001"))
            drift = abs(now - base) / denominator
            worst = max(worst, drift)
            if drift >= critical_threshold:
                severity = "CRITICAL"
            elif drift >= warning_threshold:
                severity = "WARNING"
            else:
                severity = "OK"
            rows.append({
                "feature": feature,
                "baseline": str(base),
                "current": str(now),
                "relative_drift": str(drift.quantize(Decimal("0.0001"))),
                "severity": severity,
            })
        return {
            "features": rows,
            "worst_relative_drift": str(worst.quantize(Decimal("0.0001"))),
            "status": (
                "CRITICAL" if worst >= critical_threshold
                else "WARNING" if worst >= warning_threshold
                else "OK"
            ),
            "automatic_model_disable_enabled": False,
        }
