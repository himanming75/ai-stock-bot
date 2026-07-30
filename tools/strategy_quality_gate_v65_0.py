#!/usr/bin/env python3
"""
V65.0 Strategy Quality Gate Foundation

Consumes V64 strategy analytics and V63 risk analytics, then evaluates
whether a strategy is ready for continued paper validation.

Possible gate results:
- APPROVE
- WATCH
- REJECT
- INSUFFICIENT_DATA

Offline only. No broker API. No network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "65.0"
SCHEMA_VERSION = "v65.0.strategy_quality_gate.1"
ERROR_SCHEMA_VERSION = "v65.0.strategy_quality_gate_error.1"


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


def q6(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def validate_sources(v64: Dict[str, Any], v63: Dict[str, Any]) -> None:
    if not isinstance(v64, dict):
        raise ValueError("v64 must be an object")
    if v64.get("status") != "PASS":
        raise ValueError("v64 status must be PASS")
    if v64.get("network_used") is not False:
        raise ValueError("v64 network_used must be false")
    if len(str(v64.get("strategy_report_sha256", ""))) != 64:
        raise ValueError("v64 strategy_report_sha256 must be 64 characters")

    if not isinstance(v63, dict):
        raise ValueError("v63 must be an object")
    if v63.get("status") != "PASS":
        raise ValueError("v63 status must be PASS")
    if v63.get("network_used") is not False:
        raise ValueError("v63 network_used must be false")
    if len(str(v63.get("risk_report_sha256", ""))) != 64:
        raise ValueError("v63 risk_report_sha256 must be 64 characters")


class StrategyQualityGate:
    def evaluate(
        self,
        v64: Dict[str, Any],
        v63: Dict[str, Any],
        *,
        minimum_trades: int = 20,
        approve_win_rate: Decimal = Decimal("0.55"),
        approve_profit_factor: Decimal = Decimal("1.50"),
        approve_expectancy: Decimal = Decimal("0"),
        approve_max_risk_score: Decimal = Decimal("40"),
        watch_win_rate: Decimal = Decimal("0.45"),
        watch_profit_factor: Decimal = Decimal("1.00"),
        watch_expectancy: Decimal = Decimal("-5"),
        reject_risk_score: Decimal = Decimal("70"),
    ) -> Dict[str, Any]:
        validate_sources(v64, v63)

        if minimum_trades <= 0:
            raise ValueError("minimum_trades must be greater than zero")

        overall = v64.get("overall")
        if not isinstance(overall, dict):
            raise ValueError("v64 overall must be an object")

        closed_trade_count = int(v64.get("closed_trade_count", overall.get("trade_count", 0)))
        win_rate = dec(overall.get("win_rate", "0"), "overall.win_rate")
        profit_factor = dec(overall.get("profit_factor", "0"), "overall.profit_factor")
        expectancy = dec(overall.get("expectancy", "0"), "overall.expectancy")

        analytics = v63.get("analytics")
        if not isinstance(analytics, dict):
            raise ValueError("v63 analytics must be an object")

        risk_score = dec(analytics.get("risk_score", "0"), "analytics.risk_score")
        risk_level = str(analytics.get("risk_level", "UNKNOWN"))

        approve_checks = {
            "minimum_trades": closed_trade_count >= minimum_trades,
            "win_rate": win_rate >= approve_win_rate,
            "profit_factor": profit_factor >= approve_profit_factor,
            "expectancy": expectancy > approve_expectancy,
            "risk_score": risk_score <= approve_max_risk_score,
        }

        watch_checks = {
            "minimum_trades": closed_trade_count >= minimum_trades,
            "win_rate": win_rate >= watch_win_rate,
            "profit_factor": profit_factor >= watch_profit_factor,
            "expectancy": expectancy >= watch_expectancy,
            "risk_score": risk_score < reject_risk_score,
        }

        reasons: List[str] = []

        if closed_trade_count < minimum_trades:
            gate = "INSUFFICIENT_DATA"
            reasons.append(
                f"closed_trade_count {closed_trade_count} is below minimum_trades {minimum_trades}"
            )
        elif risk_score >= reject_risk_score:
            gate = "REJECT"
            reasons.append(
                f"risk_score {q6(risk_score)} is at or above reject threshold {q6(reject_risk_score)}"
            )
        elif all(approve_checks.values()):
            gate = "APPROVE"
            reasons.append("all approval thresholds passed")
        elif all(watch_checks.values()):
            gate = "WATCH"
            failed = [name for name, passed in approve_checks.items() if not passed]
            reasons.append("watch thresholds passed")
            if failed:
                reasons.append("approval checks not passed: " + ", ".join(failed))
        else:
            gate = "REJECT"
            failed = [name for name, passed in watch_checks.items() if not passed]
            reasons.append("watch thresholds not passed: " + ", ".join(failed))

        approved_for_live = False
        approved_for_extended_paper = gate in {"APPROVE", "WATCH"}

        thresholds = {
            "minimum_trades": minimum_trades,
            "approve_win_rate": q6(approve_win_rate),
            "approve_profit_factor": q6(approve_profit_factor),
            "approve_expectancy": q6(approve_expectancy),
            "approve_max_risk_score": q6(approve_max_risk_score),
            "watch_win_rate": q6(watch_win_rate),
            "watch_profit_factor": q6(watch_profit_factor),
            "watch_expectancy": q6(watch_expectancy),
            "reject_risk_score": q6(reject_risk_score),
        }

        observed = {
            "closed_trade_count": closed_trade_count,
            "win_rate": q6(win_rate),
            "profit_factor": q6(profit_factor),
            "expectancy": q6(expectancy),
            "risk_score": q6(risk_score),
            "risk_level": risk_level,
        }

        result_core = {
            "quality_gate": gate,
            "approved_for_extended_paper": approved_for_extended_paper,
            "approved_for_live": approved_for_live,
            "reasons": reasons,
            "observed": observed,
            "thresholds": thresholds,
            "approve_checks": approve_checks,
            "watch_checks": watch_checks,
        }

        result = {
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "decision": "strategy_quality_evaluated",
            "network_used": False,
            "source_v64_strategy_report_sha256": v64["strategy_report_sha256"],
            "source_v63_risk_report_sha256": v63["risk_report_sha256"],
            **result_core,
        }
        result["quality_gate_sha256"] = sha256_hex({
            "schema_version": SCHEMA_VERSION,
            "source_v64_strategy_report_sha256": result["source_v64_strategy_report_sha256"],
            "source_v63_risk_report_sha256": result["source_v63_risk_report_sha256"],
            **result_core,
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
    parser = argparse.ArgumentParser(description="V65.0 Strategy Quality Gate Foundation")
    parser.add_argument("--strategy-analytics", required=True)
    parser.add_argument("--risk-analytics", required=True)
    parser.add_argument("--minimum-trades", type=int, default=20)
    parser.add_argument("--approve-win-rate", default="0.55")
    parser.add_argument("--approve-profit-factor", default="1.50")
    parser.add_argument("--approve-expectancy", default="0")
    parser.add_argument("--approve-max-risk-score", default="40")
    parser.add_argument("--watch-win-rate", default="0.45")
    parser.add_argument("--watch-profit-factor", default="1.00")
    parser.add_argument("--watch-expectancy", default="-5")
    parser.add_argument("--reject-risk-score", default="70")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    output = Path(args.output)

    try:
        result = StrategyQualityGate().evaluate(
            read_json(Path(args.strategy_analytics)),
            read_json(Path(args.risk_analytics)),
            minimum_trades=args.minimum_trades,
            approve_win_rate=dec(args.approve_win_rate, "approve_win_rate"),
            approve_profit_factor=dec(args.approve_profit_factor, "approve_profit_factor"),
            approve_expectancy=dec(args.approve_expectancy, "approve_expectancy"),
            approve_max_risk_score=dec(args.approve_max_risk_score, "approve_max_risk_score"),
            watch_win_rate=dec(args.watch_win_rate, "watch_win_rate"),
            watch_profit_factor=dec(args.watch_profit_factor, "watch_profit_factor"),
            watch_expectancy=dec(args.watch_expectancy, "watch_expectancy"),
            reject_risk_score=dec(args.reject_risk_score, "reject_risk_score"),
        )
        write_json(output, result)
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "quality_gate": result["quality_gate"],
            "approved_for_extended_paper": result["approved_for_extended_paper"],
            "approved_for_live": result["approved_for_live"],
            "closed_trade_count": result["observed"]["closed_trade_count"],
            "win_rate": result["observed"]["win_rate"],
            "profit_factor": result["observed"]["profit_factor"],
            "expectancy": result["observed"]["expectancy"],
            "risk_score": result["observed"]["risk_score"],
            "quality_gate_sha256": result["quality_gate_sha256"],
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
