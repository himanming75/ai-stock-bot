from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_real_market_multitimeframe_shadow as shadow


def _analysis_row(item: dict) -> dict:
    action = str(item.get("action", "HOLD")).upper()
    confidence = float(
        item.get("confidence_calibration", {}).get("calibrated_confidence", 0.0)
    )
    reward_risk = float(item.get("reward_risk", 0.0))
    guardrail_ok = item.get("execution_mode") == "ANALYSIS_ONLY"
    return {
        "symbol": str(item.get("symbol", "")).upper(),
        "action": action,
        "confidence": confidence,
        "reward_risk": reward_risk,
        "confidence_pass": confidence >= shadow.MIN_CONFIDENCE,
        "reward_risk_pass": reward_risk >= shadow.MIN_REWARD_RISK,
        "guardrail_pass": bool(guardrail_ok),
        "directional": action in {"BUY", "SELL"},
        "selector_eligible": (
            action in {"BUY", "SELL"}
            and confidence >= shadow.MIN_CONFIDENCE
            and reward_risk >= shadow.MIN_REWARD_RISK
            and guardrail_ok
        ),
    }


def classify_checkpoint(analyses: list[dict], rejected: dict, selected: dict | None) -> dict:
    rows = [_analysis_row(x) for x in analyses]
    actions = Counter(x["action"] for x in rows)
    blockers = Counter()

    for row in rows:
        if not row["directional"]:
            blockers["HOLD"] += 1
            continue
        if not row["confidence_pass"]:
            blockers["CONFIDENCE_BELOW_THRESHOLD"] += 1
        if not row["reward_risk_pass"]:
            blockers["REWARD_RISK_BELOW_THRESHOLD"] += 1
        if not row["guardrail_pass"]:
            blockers["GUARDRAIL_NOT_ANALYSIS_ONLY"] += 1

    if rejected:
        primary = "DATA_OR_FEATURE_COVERAGE"
    elif selected is not None:
        side = str(selected.get("side", "")).upper()
        primary = "SELL_SELECTED_NO_LONG_ENTRY" if side == "SELL" else "BUY_SELECTED"
    elif rows and actions.get("HOLD", 0) == len(rows):
        primary = "HOLD_ONLY"
    elif any(x["directional"] for x in rows):
        if any(x["directional"] and not x["confidence_pass"] for x in rows):
            primary = "CONFIDENCE_FILTER"
        elif any(
            x["directional"] and x["confidence_pass"] and not x["reward_risk_pass"]
            for x in rows
        ):
            primary = "REWARD_RISK_FILTER"
        elif any(
            x["directional"]
            and x["confidence_pass"]
            and x["reward_risk_pass"]
            and not x["guardrail_pass"]
            for x in rows
        ):
            primary = "GUARDRAIL_FILTER"
        else:
            primary = "SELECTOR_NONE_OTHER"
    else:
        primary = "NO_DIRECTIONAL_SIGNAL"

    return {
        "primary_cause": primary,
        "action_counts": dict(actions),
        "blocker_counts": dict(blockers),
        "analysis_rows": rows,
    }


def _date_in_scope(day: str, start: str, end: str) -> bool:
    return start <= day <= end


def audit(root: Path, start: str, end: str) -> dict:
    root = Path(root).resolve()
    by = shadow.load_real_rows(root)

    checkpoints = [
        cp for cp in shadow.make_checkpoints(by)
        if _date_in_scope(cp.date().isoformat(), start, end)
    ]
    scope_dates = sorted({cp.date().isoformat() for cp in checkpoints})
    if not checkpoints:
        raise RuntimeError(f"No market checkpoints in requested range: {start}..{end}")

    # Canonical lifecycle is reused once as the authoritative BUY-entry engine.
    lifecycle = shadow.rolling_lifecycle(root)
    accepted_signal_times = {
        str(t.get("entry_signal_time_et"))
        for t in lifecycle.get("closed_trades", [])
        if t.get("entry_signal_time_et")
    }
    accepted_by_day = Counter(
        str(t.get("entry_signal_time_et", ""))[:10]
        for t in lifecycle.get("closed_trades", [])
        if _date_in_scope(str(t.get("entry_signal_time_et", ""))[:10], start, end)
    )

    records = []
    per_day = defaultdict(lambda: {
        "market_checkpoints": 0,
        "feature_complete_checkpoints": 0,
        "selected_buy": 0,
        "selected_sell": 0,
        "selected_none": 0,
        "accepted_buy_entries": 0,
        "buy_selected_but_not_accepted": 0,
        "causes": Counter(),
        "missing_feature_symbols": Counter(),
    })

    for cp in checkpoints:
        day = cp.date().isoformat()
        truncated = shadow.truncate_by_checkpoint(by, cp)
        analyses, feature_audit, rejected, selected = shadow.analyze_at_rows(truncated)
        cls = classify_checkpoint(analyses, rejected, selected)

        cp_iso = cp.isoformat()
        selected_side = None if selected is None else str(selected.get("side", "")).upper()
        buy_accepted = bool(selected_side == "BUY" and cp_iso in accepted_signal_times)

        if selected_side == "BUY" and not buy_accepted:
            cls["lifecycle_handoff"] = "BUY_SELECTED_NOT_ACCEPTED_BY_CANONICAL_LIFECYCLE"
        elif selected_side == "BUY":
            cls["lifecycle_handoff"] = "BUY_SELECTED_AND_ACCEPTED"
        elif selected_side == "SELL":
            cls["lifecycle_handoff"] = "SELL_DELEGATED_TO_POSITION_LIFECYCLE"
        else:
            cls["lifecycle_handoff"] = "NO_SELECTED_CANDIDATE"

        rec = {
            "checkpoint_et": cp_iso,
            "date": day,
            "analysis_count": len(analyses),
            "expected_analysis_count": len(shadow.ALLOWED),
            "feature_complete": len(analyses) == len(shadow.ALLOWED) and not rejected,
            "feature_audit": feature_audit,
            "rejected_symbols": rejected,
            "selected_candidate": selected,
            "buy_accepted_by_canonical_lifecycle": buy_accepted,
            **cls,
        }
        records.append(rec)

        d = per_day[day]
        d["market_checkpoints"] += 1
        if rec["feature_complete"]:
            d["feature_complete_checkpoints"] += 1
        d["causes"][rec["primary_cause"]] += 1
        for sym in rejected:
            d["missing_feature_symbols"][sym] += 1

        if selected_side == "BUY":
            d["selected_buy"] += 1
            if buy_accepted:
                d["accepted_buy_entries"] += 1
            else:
                d["buy_selected_but_not_accepted"] += 1
        elif selected_side == "SELL":
            d["selected_sell"] += 1
        else:
            d["selected_none"] += 1

    daily_rows = []
    zero_trade_dates = []
    root_cause_days = Counter()

    for day in scope_dates:
        d = per_day[day]
        d["accepted_buy_entries"] = max(
            d["accepted_buy_entries"], accepted_by_day.get(day, 0)
        )
        is_zero = d["accepted_buy_entries"] == 0
        if is_zero:
            zero_trade_dates.append(day)

        causes = d["causes"]
        if d["feature_complete_checkpoints"] < d["market_checkpoints"]:
            day_primary = "DATA_OR_FEATURE_COVERAGE"
        elif d["selected_buy"] > 0 and d["accepted_buy_entries"] == 0:
            day_primary = "BUY_SIGNAL_LIFECYCLE_ENTRY_GAP"
        elif d["selected_buy"] == 0 and d["selected_sell"] > 0:
            day_primary = "SELL_ONLY_OR_SELL_DOMINANT"
        elif causes.get("HOLD_ONLY", 0) > 0 and d["selected_buy"] == 0:
            day_primary = "HOLD_DOMINANT"
        elif causes.get("CONFIDENCE_FILTER", 0) > 0 and d["selected_buy"] == 0:
            day_primary = "CONFIDENCE_FILTER"
        elif causes.get("REWARD_RISK_FILTER", 0) > 0 and d["selected_buy"] == 0:
            day_primary = "REWARD_RISK_FILTER"
        elif is_zero:
            day_primary = "NO_ACCEPTED_BUY_OTHER"
        else:
            day_primary = "TRADED"

        if is_zero:
            root_cause_days[day_primary] += 1

        daily_rows.append({
            "date": day,
            "zero_trade": is_zero,
            "primary_root_cause": day_primary,
            "market_checkpoints": d["market_checkpoints"],
            "feature_complete_checkpoints": d["feature_complete_checkpoints"],
            "feature_coverage_rate": (
                d["feature_complete_checkpoints"] / d["market_checkpoints"]
                if d["market_checkpoints"] else 0.0
            ),
            "selected_buy": d["selected_buy"],
            "selected_sell": d["selected_sell"],
            "selected_none": d["selected_none"],
            "accepted_buy_entries": d["accepted_buy_entries"],
            "buy_selected_but_not_accepted": d["buy_selected_but_not_accepted"],
            "checkpoint_cause_counts": dict(causes),
            "missing_feature_symbols": dict(d["missing_feature_symbols"]),
        })

    checkpoint_causes = Counter(r["primary_cause"] for r in records)
    selected_sides = Counter(
        "NONE" if r["selected_candidate"] is None
        else str(r["selected_candidate"].get("side", "")).upper()
        for r in records
    )

    report = {
        "stage": "V1.7_HOLDOUT_ZERO_TRADE_ROOT_CAUSE_DATA_SIGNAL_COVERAGE_AUDIT",
        "status": "PASS",
        "mode": "READ_ONLY_HISTORICAL_DIAGNOSTIC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_range": {"start": start, "end": end},
        "source_dataset": "runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "canonical_reuse": {
            "historical_ingestor": "tools.build_real_market_multitimeframe_shadow.load_real_rows",
            "feature_analyzer": "tools.build_real_market_multitimeframe_shadow.analyze_at_rows",
            "selector": "paper_autonomous_execution.signals.select_candidate via analyze_at_rows",
            "lifecycle": "tools.build_real_market_multitimeframe_shadow.rolling_lifecycle",
            "duplicate_engine_created": False,
        },
        "thresholds_observed_not_modified": {
            "min_confidence": shadow.MIN_CONFIDENCE,
            "min_reward_risk": shadow.MIN_REWARD_RISK,
        },
        "scope_summary": {
            "trading_dates": len(scope_dates),
            "market_checkpoints": len(checkpoints),
            "zero_trade_dates": len(zero_trade_dates),
            "zero_trade_date_list": zero_trade_dates,
            "checkpoint_primary_cause_counts": dict(checkpoint_causes),
            "selected_side_counts": dict(selected_sides),
            "zero_trade_day_root_cause_counts": dict(root_cause_days),
        },
        "canonical_lifecycle_crosscheck": {
            "entry_summary": lifecycle.get("entry_summary", {}),
            "checkpoint_summary": lifecycle.get("checkpoint_summary", {}),
            "note": "Historical analysis only. No broker write/order submission path is used.",
        },
        "daily_audit": daily_rows,
        "checkpoint_audit": records,
        "interpretation": {
            "data_feature_problem_detected": any(
                x["feature_complete_checkpoints"] < x["market_checkpoints"]
                for x in daily_rows
            ),
            "hold_filter_detected": checkpoint_causes.get("HOLD_ONLY", 0) > 0,
            "confidence_filter_detected": checkpoint_causes.get("CONFIDENCE_FILTER", 0) > 0,
            "reward_risk_filter_detected": checkpoint_causes.get("REWARD_RISK_FILTER", 0) > 0,
            "sell_selected_detected": selected_sides.get("SELL", 0) > 0,
            "buy_selected_lifecycle_gap_detected": any(
                x["buy_selected_but_not_accepted"] > 0 for x in daily_rows
            ),
        },
        "contracts": {
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "strategy_parameter_modified": False,
            "risk_parameter_modified": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "automatic_promotion": False,
            "live_auto_enable": False,
        },
    }

    out = root / "runtime/real_market_multitimeframe_shadow"
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest_holdout_zero_trade_audit_v1_7.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    with (out / "holdout_zero_trade_audit_v1_7_ledger.jsonl").open("a", encoding="utf-8") as h:
        h.write(json.dumps(
            {k: v for k, v in report.items() if k != "checkpoint_audit"},
            default=str
        ) + "\n")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    p.add_argument("--start", default="2026-06-09")
    p.add_argument("--end", default="2026-07-07")
    a = p.parse_args()
    result = audit(Path(a.root), a.start, a.end)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
