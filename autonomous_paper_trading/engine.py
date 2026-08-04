from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from autonomous_paper_trading.alpaca_paper import AlpacaPaperClient
from autonomous_paper_trading.auth import confirmation, credentials
from autonomous_paper_trading.config import load, validate
from autonomous_paper_trading.idempotency import make_key, register
from autonomous_paper_trading.io import load_json, write_json, append_jsonl
from autonomous_paper_trading.report import build as build_report

def evaluate(root: Path, allow_network: bool = False) -> dict:
    policy = load(root)
    validation = validate(policy)
    auth = credentials()
    confirm = confirmation(root, policy)
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    optimizer = load_json(
        root / "release/v251_01_to_v255_64/actual/execution_optimizer_result.json"
    )
    ensemble = load_json(
        root / "release/v246_01_to_v250_64/actual/ai_strategy_ensemble_v3_result.json"
    )
    risk = load_json(
        root / "release/v206_01_to_v210_64/actual/risk_engine_v2_result.json"
    )
    plan = optimizer.get("execution_plan", {})
    candidate = ensemble.get("final_trade_candidate", {})
    risk_passed = risk.get("risk_gate", {}).get("passed") is True

    blocking = []
    if not validation["valid"]:
        blocking.append("POLICY_INVALID")
    if not policy.get("autonomous_cycle_enabled"):
        blocking.append("AUTONOMOUS_CYCLE_DISABLED")
    if not policy.get("real_paper_submission_enabled"):
        blocking.append("PAPER_SUBMISSION_DISABLED")
    if policy.get("require_confirmation_token") and not confirm["valid"]:
        blocking.append("CONFIRMATION_TOKEN_INVALID")
    if not auth["ready"]:
        blocking.append("PAPER_CREDENTIALS_MISSING")
    if not plan.get("plan_allowed"):
        blocking.append("EXECUTION_PLAN_BLOCKED")
    if not candidate:
        blocking.append("TRADE_CANDIDATE_MISSING")
    if not risk_passed:
        blocking.append("RISK_GATE_BLOCKED")
    if not allow_network:
        blocking.append("NETWORK_CALL_NOT_AUTHORIZED_FOR_THIS_RUN")

    account = {}
    clock = {"is_open": False}
    positions = []
    open_orders = []
    paper_orders = 0
    receipt = {}

    client = None
    can_read = allow_network and auth["ready"] and policy.get("real_paper_read_enabled")
    if can_read:
        client = AlpacaPaperClient(auth["key"], auth["secret"], policy["paper_base_url"])
        account = client.account()
        clock = client.clock()
        positions = client.positions()
        open_orders = client.open_orders()

    market_open = clock.get("is_open") is True
    if policy.get("require_market_open") and not market_open:
        blocking.append("MARKET_CLOSED")

    idempotency_key = make_key(session_id, plan)
    plan_with_id = {
        **plan,
        "client_order_id": f"AISB-PAPER-{idempotency_key}",
    }
    duplicate = register(root, idempotency_key, plan_with_id)

    submission_allowed = (
        allow_network
        and not blocking
        and not duplicate["duplicate"]
        and client is not None
    )
    if submission_allowed:
        receipt = client.submit_order(plan_with_id)
        paper_orders = 1

    state = (
        "AUTONOMOUS_PAPER_TRADING_ACTIVE"
        if submission_allowed
        else "AUTONOMOUS_PAPER_TRADING_READY_BLOCKED"
    )
    result = {
        "stage": "V260.64",
        "state": state,
        "status": "PASS",
        "session_id": session_id,
        "cycle_count": 1,
        "market_open": market_open,
        "blocking_reasons": sorted(set(blocking)),
        "account_snapshot": account,
        "position_count": len(positions),
        "open_order_count": len(open_orders),
        "execution_plan": plan_with_id,
        "candidate": candidate,
        "risk_gate_passed": risk_passed,
        "duplicate": duplicate,
        "paper_order_receipt": receipt,
        "autonomous_cycle_enabled": policy.get("autonomous_cycle_enabled") is True,
        "real_paper_read_enabled": policy.get("real_paper_read_enabled") is True,
        "real_paper_submission_enabled": policy.get("real_paper_submission_enabled") is True,
        "live_submission_enabled": False,
        "live_network_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": paper_orders,
        "actual_live_orders_submitted": 0,
        "next_phase": "V261_01_TO_V270_64_LONG_TERM_PAPER_QUALIFICATION",
    }
    actual = root / "release/v256_01_to_v260_64/actual"
    write_json(actual / "autonomous_paper_trading_result.json", result)
    append_jsonl(actual / "autonomous_paper_trading_ledger.jsonl", {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "state": state,
        "blocking_reasons": result["blocking_reasons"],
        "actual_paper_orders_submitted": paper_orders,
        "actual_live_orders_submitted": 0,
    })
    result["daily_report"] = build_report(root, result)
    return result
