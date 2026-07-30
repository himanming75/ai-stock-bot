#!/usr/bin/env python3
"""
V63.0 Risk Analytics Foundation

Consumes V62 dashboard data and produces offline risk analytics:
- daily return statistics
- annualized volatility
- downside deviation
- Sharpe ratio
- Sortino ratio
- Calmar ratio
- recovery factor
- historical VaR / CVaR
- rolling drawdown series
- normalized risk score
- SHA-256 integrity hashes

No broker API, no network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "63.0"
SCHEMA_VERSION = "v63.0.risk_analytics.1"
ERROR_SCHEMA_VERSION = "v63.0.risk_analytics_error.1"
ANNUALIZATION_DAYS = Decimal("252")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dec(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


def q4(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def q6(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def mean(values: List[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def population_std(values: List[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    avg = mean(values)
    variance = sum((v - avg) ** 2 for v in values) / Decimal(len(values))
    return Decimal(str(math.sqrt(float(variance))))


def historical_quantile(values: List[Decimal], confidence: Decimal) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    alpha = Decimal("1") - confidence
    index = max(0, min(len(ordered) - 1, math.ceil(float(alpha * Decimal(len(ordered)))) - 1))
    return ordered[index]


def validate_v62(v62: Dict[str, Any]) -> None:
    if not isinstance(v62, dict):
        raise ValueError("v62 must be an object")
    if v62.get("status") != "PASS":
        raise ValueError("v62 status must be PASS")
    if v62.get("network_used") is not False:
        raise ValueError("v62 network_used must be false")
    chart = v62.get("chart")
    if not isinstance(chart, list) or not chart:
        raise ValueError("v62 chart must be a non-empty list")
    dashboard_sha = str(v62.get("dashboard_sha256", ""))
    if len(dashboard_sha) != 64:
        raise ValueError("v62 dashboard_sha256 must be 64 characters")


class RiskAnalyticsEngine:
    def build(
        self,
        v62: Dict[str, Any],
        risk_free_rate: Decimal = Decimal("0"),
        var_confidence: Decimal = Decimal("0.95"),
    ) -> Dict[str, Any]:
        validate_v62(v62)

        if not Decimal("0") <= risk_free_rate <= Decimal("1"):
            raise ValueError("risk_free_rate must be between 0 and 1")
        if not Decimal("0.50") <= var_confidence < Decimal("1"):
            raise ValueError("var_confidence must be between 0.50 and 1")

        chart = deepcopy(v62["chart"])
        returns: List[Decimal] = []
        rolling_drawdown: List[Dict[str, Any]] = []

        for index, point in enumerate(chart):
            if not isinstance(point, dict):
                raise ValueError(f"chart[{index}] must be an object")
            daily_return = dec(point.get("daily_return", "0"), f"chart[{index}].daily_return")
            drawdown = dec(point.get("drawdown", "0"), f"chart[{index}].drawdown")
            returns.append(daily_return)

            item_core = {
                "sequence": int(point.get("sequence", index + 1)),
                "journal_date": str(point.get("journal_date")),
                "equity": q4(dec(point.get("equity"), f"chart[{index}].equity")),
                "running_peak": q4(dec(point.get("running_peak"), f"chart[{index}].running_peak")),
                "drawdown_amount": q4(dec(point.get("drawdown_amount", "0"), f"chart[{index}].drawdown_amount")),
                "drawdown": q6(drawdown),
            }
            item = dict(item_core)
            item["rolling_point_sha256"] = sha256_hex(item_core)
            rolling_drawdown.append(item)

        avg_daily_return = mean(returns)
        daily_volatility = population_std(returns)
        annualized_volatility = daily_volatility * Decimal(str(math.sqrt(252)))

        negative_returns = [r for r in returns if r < 0]
        downside_deviation_daily = Decimal(str(math.sqrt(float(
            sum((min(r, Decimal("0"))) ** 2 for r in returns) / Decimal(len(returns))
        )))) if returns else Decimal("0")
        downside_deviation_annualized = downside_deviation_daily * Decimal(str(math.sqrt(252)))

        daily_risk_free = risk_free_rate / ANNUALIZATION_DAYS
        excess_daily_return = avg_daily_return - daily_risk_free

        sharpe = (
            excess_daily_return / daily_volatility * Decimal(str(math.sqrt(252)))
            if daily_volatility != 0 else Decimal("0")
        )
        sortino = (
            excess_daily_return / downside_deviation_daily * Decimal(str(math.sqrt(252)))
            if downside_deviation_daily != 0 else Decimal("0")
        )

        metrics = v62.get("metrics", {})
        total_return = dec(metrics.get("total_return", "0"), "metrics.total_return")
        max_drawdown = dec(metrics.get("max_drawdown", "0"), "metrics.max_drawdown")
        total_pnl = dec(metrics.get("total_pnl", "0"), "metrics.total_pnl")
        starting_equity = dec(metrics.get("starting_equity", "0"), "metrics.starting_equity")

        calmar = total_return / abs(max_drawdown) if max_drawdown != 0 else Decimal("0")
        recovery_factor = total_pnl / abs(starting_equity * max_drawdown) if max_drawdown != 0 else Decimal("0")

        var_return = historical_quantile(returns, var_confidence)
        tail = [r for r in returns if r <= var_return]
        cvar_return = mean(tail) if tail else var_return

        # Positive loss values are easier to display on a risk dashboard.
        var_loss = max(Decimal("0"), -var_return)
        cvar_loss = max(Decimal("0"), -cvar_return)

        # Deterministic 0-100 risk score.
        # Volatility 20%, drawdown 40%, VaR 25%, downside deviation 15%.
        volatility_component = min(Decimal("100"), annualized_volatility * Decimal("500"))
        drawdown_component = min(Decimal("100"), abs(max_drawdown) * Decimal("500"))
        var_component = min(Decimal("100"), var_loss * Decimal("1000"))
        downside_component = min(Decimal("100"), downside_deviation_annualized * Decimal("500"))
        risk_score = (
            volatility_component * Decimal("0.20")
            + drawdown_component * Decimal("0.40")
            + var_component * Decimal("0.25")
            + downside_component * Decimal("0.15")
        )

        if risk_score < Decimal("20"):
            risk_level = "LOW"
        elif risk_score < Decimal("40"):
            risk_level = "MODERATE"
        elif risk_score < Decimal("70"):
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        analytics_core = {
            "observation_count": len(returns),
            "average_daily_return": q6(avg_daily_return),
            "daily_volatility": q6(daily_volatility),
            "annualized_volatility": q6(annualized_volatility),
            "downside_deviation_daily": q6(downside_deviation_daily),
            "downside_deviation_annualized": q6(downside_deviation_annualized),
            "sharpe_ratio": q6(sharpe),
            "sortino_ratio": q6(sortino),
            "calmar_ratio": q6(calmar),
            "recovery_factor": q6(recovery_factor),
            "max_drawdown": q6(max_drawdown),
            "var_confidence": q6(var_confidence),
            "historical_var_return": q6(var_return),
            "historical_var_loss": q6(var_loss),
            "historical_cvar_return": q6(cvar_return),
            "historical_cvar_loss": q6(cvar_loss),
            "negative_return_count": len(negative_returns),
            "risk_free_rate": q6(risk_free_rate),
            "risk_score": q6(risk_score),
            "risk_level": risk_level,
        }
        analytics = dict(analytics_core)
        analytics["analytics_sha256"] = sha256_hex(analytics_core)

        result = {
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "decision": "risk_analytics_built",
            "network_used": False,
            "source_v62_dashboard_sha256": v62["dashboard_sha256"],
            "analytics": analytics,
            "rolling_drawdown": rolling_drawdown,
            "rolling_point_count": len(rolling_drawdown),
        }
        result["risk_report_sha256"] = sha256_hex({
            "schema_version": SCHEMA_VERSION,
            "source_v62_dashboard_sha256": result["source_v62_dashboard_sha256"],
            "analytics": analytics,
            "rolling_drawdown": rolling_drawdown,
        })
        return result


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V63.0 Risk Analytics Foundation")
    parser.add_argument("--dashboard-input", required=True)
    parser.add_argument("--risk-free-rate", default="0")
    parser.add_argument("--var-confidence", default="0.95")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    output = Path(args.output)
    try:
        result = RiskAnalyticsEngine().build(
            read_json(Path(args.dashboard_input)),
            risk_free_rate=dec(args.risk_free_rate, "risk_free_rate"),
            var_confidence=dec(args.var_confidence, "var_confidence"),
        )
        write_json(output, result)
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "observation_count": result["analytics"]["observation_count"],
            "annualized_volatility": result["analytics"]["annualized_volatility"],
            "sharpe_ratio": result["analytics"]["sharpe_ratio"],
            "sortino_ratio": result["analytics"]["sortino_ratio"],
            "max_drawdown": result["analytics"]["max_drawdown"],
            "historical_var_loss": result["analytics"]["historical_var_loss"],
            "risk_score": result["analytics"]["risk_score"],
            "risk_level": result["analytics"]["risk_level"],
            "risk_report_sha256": result["risk_report_sha256"],
            "network_used": result["network_used"],
        }, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error = {
            "version": VERSION,
            "schema_version": ERROR_SCHEMA_VERSION,
            "status": "FAIL",
            "network_used": False,
            "error": str(exc),
        }
        write_json(output, error)
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
