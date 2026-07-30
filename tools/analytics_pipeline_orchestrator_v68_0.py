from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "68.0"
SCHEMA_VERSION = "v68.0.analytics_pipeline_orchestrator.1"


class PipelineError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PipelineError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PipelineError("top-level JSON must be an object")
    return value


def dec(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PipelineError(f"{field} must be numeric") from exc


def validate_v67(report: Dict[str, Any]) -> None:
    if report.get("status") != "PASS":
        raise PipelineError("V67 status must be PASS")
    if report.get("network_used") is not False:
        raise PipelineError("V67 network_used must be false")
    if report.get("approved_for_live") is not False:
        raise PipelineError("V67 approved_for_live must be false")
    if report.get("schema_version") != "v67.0.paper_trade_scenarios.1":
        raise PipelineError("unsupported V67 schema_version")
    trades = report.get("trades")
    if not isinstance(trades, list):
        raise PipelineError("V67 trades must be a list")
    if report.get("trade_count") != len(trades):
        raise PipelineError("V67 trade_count does not match trades length")
    if report.get("closed_trade_count") != len(trades):
        raise PipelineError("V67 closed_trade_count does not match trades length")
    if report.get("open_trade_count") != 0:
        raise PipelineError("V67 open_trade_count must be zero")
    for index, trade in enumerate(trades):
        if not isinstance(trade, dict):
            raise PipelineError(f"trade {index} must be an object")
        if trade.get("status") != "CLOSED":
            raise PipelineError(f"trade {index} must be CLOSED")
        if trade.get("network_used") is not False:
            raise PipelineError(f"trade {index} network_used must be false")
        for key in ("trade_id", "strategy", "symbol", "side", "realized_pnl",
                    "opened_at", "closed_at", "holding_minutes"):
            if key not in trade:
                raise PipelineError(f"trade {index} missing {key}")


def group_metrics(name: str, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    pnls = [dec(t["realized_pnl"], "realized_pnl") for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    flats = [x for x in pnls if x == 0]
    gross_profit = sum(wins, Decimal("0"))
    gross_loss_abs = abs(sum(losses, Decimal("0")))
    net_pnl = sum(pnls, Decimal("0"))
    count = len(pnls)
    win_rate = Decimal(len(wins)) / Decimal(count) if count else Decimal("0")
    avg_win = gross_profit / Decimal(len(wins)) if wins else Decimal("0")
    avg_loss = gross_loss_abs / Decimal(len(losses)) if losses else Decimal("0")
    expectancy = net_pnl / Decimal(count) if count else Decimal("0")
    profit_factor = (
        gross_profit / gross_loss_abs
        if gross_loss_abs > 0
        else (Decimal("999999") if gross_profit > 0 else Decimal("0"))
    )
    avg_holding = (
        sum(Decimal(str(t["holding_minutes"])) for t in trades) / Decimal(count)
        if count else Decimal("0")
    )

    metrics = {
        "group": name,
        "trade_count": count,
        "win_count": len(wins),
        "loss_count": len(losses),
        "flat_count": len(flats),
        "gross_profit": f"{gross_profit:.4f}",
        "gross_loss": f"{gross_loss_abs:.4f}",
        "net_pnl": f"{net_pnl:.4f}",
        "win_rate": f"{win_rate:.6f}",
        "profit_factor": f"{profit_factor:.6f}",
        "average_win": f"{avg_win:.4f}",
        "average_loss": f"{avg_loss:.4f}",
        "expectancy": f"{expectancy:.4f}",
        "average_holding_minutes": f"{avg_holding:.4f}",
    }
    metrics["group_sha256"] = sha256_of(metrics)
    return metrics


def grouped(trades: List[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    values: Dict[str, List[Dict[str, Any]]] = {}
    for trade in trades:
        key = str(trade[field])
        values.setdefault(key, []).append(trade)
    return [group_metrics(key, values[key]) for key in sorted(values)]


def build_analytics(v67: Dict[str, Any]) -> Dict[str, Any]:
    trades = v67["trades"]
    overall = group_metrics("ALL", trades)
    by_strategy = grouped(trades, "strategy")
    by_symbol = grouped(trades, "symbol")
    by_side = grouped(trades, "side")

    ranking = sorted(
        by_strategy,
        key=lambda x: (
            dec(x["expectancy"], "expectancy"),
            dec(x["profit_factor"], "profit_factor"),
            dec(x["win_rate"], "win_rate"),
        ),
        reverse=True,
    )
    ranking_out = [
        {
            "rank": i + 1,
            "strategy": row["group"],
            "trade_count": row["trade_count"],
            "net_pnl": row["net_pnl"],
            "win_rate": row["win_rate"],
            "profit_factor": row["profit_factor"],
            "expectancy": row["expectancy"],
        }
        for i, row in enumerate(ranking)
    ]

    report = {
        "status": "PASS",
        "decision": "v67_strategy_analytics_built",
        "network_used": False,
        "approved_for_live": False,
        "closed_trade_count": len(trades),
        "open_trade_count": 0,
        "overall": overall,
        "by_strategy": by_strategy,
        "by_symbol": by_symbol,
        "by_side": by_side,
        "strategy_ranking": ranking_out,
        "source_v67_scenario_report_sha256": v67["scenario_report_sha256"],
        "schema_version": "v68.0.embedded_strategy_analytics.1",
        "version": VERSION,
    }
    report["analytics_report_sha256"] = sha256_of(report)
    return report


def quality_gate(
    analytics: Dict[str, Any],
    minimum_trades: int,
    approve_win_rate: Decimal,
    approve_profit_factor: Decimal,
    approve_expectancy: Decimal,
    watch_win_rate: Decimal,
    watch_profit_factor: Decimal,
    watch_expectancy: Decimal,
) -> Dict[str, Any]:
    overall = analytics["overall"]
    count = analytics["closed_trade_count"]
    win_rate = dec(overall["win_rate"], "win_rate")
    profit_factor = dec(overall["profit_factor"], "profit_factor")
    expectancy = dec(overall["expectancy"], "expectancy")

    if count < minimum_trades:
        gate = "INSUFFICIENT_DATA"
        reason = f"closed_trade_count {count} is below minimum_trades {minimum_trades}"
    elif (
        win_rate >= approve_win_rate
        and profit_factor >= approve_profit_factor
        and expectancy > approve_expectancy
    ):
        gate = "APPROVE"
        reason = "all approval thresholds were satisfied"
    elif (
        win_rate >= watch_win_rate
        and profit_factor >= watch_profit_factor
        and expectancy >= watch_expectancy
    ):
        gate = "WATCH"
        reason = "watch thresholds were satisfied but approval thresholds were not"
    else:
        gate = "REJECT"
        reason = "performance did not satisfy watch thresholds"

    report = {
        "status": "PASS",
        "decision": "embedded_strategy_quality_evaluated",
        "quality_gate": gate,
        "approved_for_extended_paper": gate == "APPROVE",
        "approved_for_live": False,
        "network_used": False,
        "reason": reason,
        "observed": {
            "closed_trade_count": count,
            "win_rate": f"{win_rate:.6f}",
            "profit_factor": f"{profit_factor:.6f}",
            "expectancy": f"{expectancy:.6f}",
        },
        "thresholds": {
            "minimum_trades": minimum_trades,
            "approve_win_rate": f"{approve_win_rate:.6f}",
            "approve_profit_factor": f"{approve_profit_factor:.6f}",
            "approve_expectancy": f"{approve_expectancy:.6f}",
            "watch_win_rate": f"{watch_win_rate:.6f}",
            "watch_profit_factor": f"{watch_profit_factor:.6f}",
            "watch_expectancy": f"{watch_expectancy:.6f}",
        },
        "source_analytics_report_sha256": analytics["analytics_report_sha256"],
        "schema_version": "v68.0.embedded_quality_gate.1",
        "version": VERSION,
    }
    report["quality_gate_sha256"] = sha256_of(report)
    return report


def promotion(quality: Dict[str, Any]) -> Dict[str, Any]:
    gate = quality["quality_gate"]
    state = {
        "APPROVE": "EXTENDED_PAPER_APPROVED",
        "WATCH": "WATCHLIST",
        "REJECT": "BLOCKED",
        "INSUFFICIENT_DATA": "HOLD_INSUFFICIENT_DATA",
    }[gate]
    report = {
        "status": "PASS",
        "decision": "embedded_extended_paper_promotion_evaluated",
        "promotion_state": state,
        "eligible_for_extended_paper": gate == "APPROVE",
        "start_extended_paper": gate == "APPROVE",
        "approved_for_live": False,
        "network_used": False,
        "source_quality_gate_sha256": quality["quality_gate_sha256"],
        "schema_version": "v68.0.embedded_promotion.1",
        "version": VERSION,
    }
    report["promotion_report_sha256"] = sha256_of(report)
    return report


def build_pipeline(
    v67: Dict[str, Any],
    minimum_trades: int = 20,
    approve_win_rate: Decimal = Decimal("0.55"),
    approve_profit_factor: Decimal = Decimal("1.50"),
    approve_expectancy: Decimal = Decimal("0"),
    watch_win_rate: Decimal = Decimal("0.45"),
    watch_profit_factor: Decimal = Decimal("1.00"),
    watch_expectancy: Decimal = Decimal("-5"),
) -> Dict[str, Any]:
    validate_v67(v67)
    analytics = build_analytics(v67)
    quality = quality_gate(
        analytics, minimum_trades, approve_win_rate, approve_profit_factor,
        approve_expectancy, watch_win_rate, watch_profit_factor, watch_expectancy
    )
    promo = promotion(quality)

    report = {
        "status": "PASS",
        "pipeline_status": "PASS",
        "decision": "analytics_pipeline_completed",
        "failed_stage": None,
        "network_used": False,
        "approved_for_live": False,
        "trade_count": v67["trade_count"],
        "closed_trade_count": analytics["closed_trade_count"],
        "open_trade_count": analytics["open_trade_count"],
        "analytics": analytics,
        "quality_gate": quality,
        "promotion": promo,
        "source_v67_scenario_report_sha256": v67["scenario_report_sha256"],
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    report["pipeline_report_sha256"] = sha256_of(report)
    return report


def run(input_path: Path, output_path: Path, **kwargs: Any) -> Dict[str, Any]:
    v67 = read_json(input_path)
    report = build_pipeline(v67, **kwargs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V68 Analytics Pipeline Orchestrator")
    parser.add_argument("--paper-trades", required=True, type=Path)
    parser.add_argument("--minimum-trades", type=int, default=20)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        if args.minimum_trades < 1:
            raise PipelineError("minimum_trades must be at least 1")
        report = run(
            args.paper_trades,
            args.output,
            minimum_trades=args.minimum_trades,
        )
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL",
            "pipeline_status": "FAIL",
            "decision": "analytics_pipeline_failed",
            "failed_stage": "INPUT_OR_PIPELINE",
            "error": str(exc),
            "network_used": False,
            "approved_for_live": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps({
        "status": report["status"],
        "pipeline_status": report["pipeline_status"],
        "decision": report["decision"],
        "trade_count": report["trade_count"],
        "closed_trade_count": report["closed_trade_count"],
        "win_rate": report["analytics"]["overall"]["win_rate"],
        "profit_factor": report["analytics"]["overall"]["profit_factor"],
        "expectancy": report["analytics"]["overall"]["expectancy"],
        "net_pnl": report["analytics"]["overall"]["net_pnl"],
        "quality_gate": report["quality_gate"]["quality_gate"],
        "promotion_state": report["promotion"]["promotion_state"],
        "approved_for_live": report["approved_for_live"],
        "network_used": report["network_used"],
        "pipeline_report_sha256": report["pipeline_report_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
