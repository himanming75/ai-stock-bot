from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from live_shadow_slippage.config import load, validate
from live_shadow_slippage.io import load_json, write_json, append_jsonl
from live_shadow_slippage.quote import normalize
from live_shadow_slippage.slippage import estimate
from live_shadow_slippage.qualification import evaluate as evaluate_qualification
from live_shadow_slippage.report import build as build_report

def evaluate(root: Path) -> dict[str, Any]:
    policy = load(root)
    validation = validate(policy)
    signal = load_json(root / "release/v226_01_to_v230_64/input/paper_shadow_signal.json").get("signal", {})
    quote = normalize(load_json(root / "release/v226_01_to_v230_64/input/live_quote_snapshot.json"))
    account = load_json(root / "release/v226_01_to_v230_64/input/live_account_readonly_snapshot.json").get("account", {})
    slippage = estimate(signal, quote)
    qualification = evaluate_qualification(policy, signal, account, quote, slippage)
    observed = datetime.now(timezone.utc).isoformat()
    state = "LIVE_SHADOW_QUALIFIED" if qualification["passed"] else "LIVE_SHADOW_REVIEW_REQUIRED"
    result = {
        "stage": "V230.64",
        "state": state,
        "status": "PASS",
        "observed_at": observed,
        "signal": signal,
        "quote": quote,
        "slippage": slippage,
        "qualification": qualification,
        "real_live_read_enabled": policy.get("real_live_read_enabled") is True,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_live_orders_submitted": 0,
        "next_phase": "V231_01_TO_V235_64_ORDER_LIFECYCLE_V2",
    }
    result["daily_report"] = build_report(root, result)
    actual = root / "release/v226_01_to_v230_64/actual"
    write_json(actual / "live_shadow_slippage_result.json", result)
    append_jsonl(actual / "live_shadow_slippage_audit_ledger.jsonl", {
        "observed_at": observed,
        "state": state,
        "symbol": signal.get("symbol"),
        "slippage_pct": slippage["slippage_pct"],
        "spread_pct": quote["spread_pct"],
        "qualified": qualification["passed"],
        "actual_live_orders_submitted": 0,
    })
    return result
