from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Optional

VERSION = "66.0"
SCHEMA_VERSION = "v66.0.extended_paper_promotion.1"


class PromotionError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromotionError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromotionError(f"invalid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise PromotionError("top-level JSON must be an object")
    return data


def valid_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise PromotionError(f"{field} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise PromotionError(f"{field} must be hexadecimal") from exc
    return value.lower()


def decimal_value(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PromotionError(f"{field} must be numeric") from exc


def validate_inputs(v65: Dict[str, Any], v64: Dict[str, Any]) -> None:
    if v65.get("status") != "PASS":
        raise PromotionError("V65 status must be PASS")
    if v65.get("network_used") is not False:
        raise PromotionError("V65 network_used must be false")
    if v65.get("schema_version") != "v65.0.strategy_quality_gate.1":
        raise PromotionError("unsupported V65 schema")
    if v65.get("approved_for_live") is not False:
        raise PromotionError("V65 approved_for_live must remain false")
    valid_sha(v65.get("quality_gate_sha256"), "V65 quality_gate_sha256")

    gate = v65.get("quality_gate")
    if gate not in {"APPROVE", "WATCH", "REJECT", "INSUFFICIENT_DATA"}:
        raise PromotionError("unsupported V65 quality_gate")
    approved = v65.get("approved_for_extended_paper")
    if not isinstance(approved, bool):
        raise PromotionError("V65 approved_for_extended_paper must be boolean")
    if gate == "APPROVE" and not approved:
        raise PromotionError("V65 APPROVE must approve extended paper")
    if gate != "APPROVE" and approved:
        raise PromotionError("only V65 APPROVE may approve extended paper")

    if v64.get("status") != "PASS":
        raise PromotionError("V64 status must be PASS")
    if v64.get("network_used") is not False:
        raise PromotionError("V64 network_used must be false")
    if v64.get("schema_version") != "v64.0.strategy_analytics.1":
        raise PromotionError("unsupported V64 schema")
    valid_sha(v64.get("strategy_report_sha256"), "V64 strategy_report_sha256")
    if v65.get("source_v64_strategy_report_sha256") != v64.get("strategy_report_sha256"):
        raise PromotionError("V65 source hash does not match V64 report")

    for field in ("closed_trade_count", "open_trade_count"):
        value = v64.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PromotionError(f"V64 {field} must be a nonnegative integer")
    if not isinstance(v64.get("overall"), dict):
        raise PromotionError("V64 overall must be an object")


def promotion_state(gate: str) -> tuple[str, bool, bool, str]:
    if gate == "APPROVE":
        return ("EXTENDED_PAPER_APPROVED", True, True,
                "V65 quality gate approved extended paper evaluation")
    if gate == "WATCH":
        return ("WATCHLIST", False, False,
                "Continue paper observation before promotion")
    if gate == "REJECT":
        return ("BLOCKED", False, False,
                "V65 quality gate rejected the strategy")
    return ("HOLD_INSUFFICIENT_DATA", False, False,
            "Insufficient closed-trade data for promotion")


def build_report(v65: Dict[str, Any], v64: Dict[str, Any]) -> Dict[str, Any]:
    validate_inputs(v65, v64)
    state, eligible, start, reason = promotion_state(v65["quality_gate"])
    overall = v64["overall"]
    report = {
        "status": "PASS",
        "decision": "extended_paper_promotion_evaluated",
        "promotion_state": state,
        "eligible_for_extended_paper": eligible,
        "start_extended_paper": start,
        "approved_for_live": False,
        "network_used": False,
        "reason": reason,
        "observed": {
            "quality_gate": v65["quality_gate"],
            "closed_trade_count": v64["closed_trade_count"],
            "open_trade_count": v64["open_trade_count"],
            "win_rate": f"{decimal_value(overall.get('win_rate'), 'win_rate'):.6f}",
            "profit_factor": f"{decimal_value(overall.get('profit_factor'), 'profit_factor'):.6f}",
            "expectancy": f"{decimal_value(overall.get('expectancy'), 'expectancy'):.6f}",
            "net_pnl": f"{decimal_value(overall.get('net_pnl'), 'net_pnl'):.4f}",
        },
        "safety": {
            "live_trading_enabled": False,
            "broker_connection_enabled": False,
            "external_order_submission_enabled": False,
            "requires_future_live_safety_gate": True,
        },
        "source_v64_strategy_report_sha256": v64["strategy_report_sha256"],
        "source_v65_quality_gate_sha256": v65["quality_gate_sha256"],
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    report["promotion_report_sha256"] = sha256_of(report)
    return report


def run(v65_path: Path, v64_path: Path, output: Path) -> Dict[str, Any]:
    report = build_report(read_json(v65_path), read_json(v64_path))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="V66 Extended Paper Promotion Controller")
    parser.add_argument("--quality-gate", required=True, type=Path)
    parser.add_argument("--strategy-analytics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = run(args.quality_gate, args.strategy_analytics, args.output)
    except PromotionError as exc:
        print(json.dumps({"status": "FAIL", "decision": "promotion_rejected", "error": str(exc), "network_used": False, "version": VERSION}, indent=2, sort_keys=True))
        return 1
    summary = {key: report[key] for key in (
        "status", "decision", "promotion_state", "eligible_for_extended_paper",
        "start_extended_paper", "approved_for_live", "network_used",
        "promotion_report_sha256")}
    summary["closed_trade_count"] = report["observed"]["closed_trade_count"]
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
