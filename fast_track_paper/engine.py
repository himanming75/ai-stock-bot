from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from fast_track_paper.io import (
    load_json,write_json,append_jsonl,read_jsonl,digest
)
from fast_track_paper.orders import build_orders
from fast_track_paper.fills import simulate_fills
from fast_track_paper.positions import open_positions,merge_positions
from fast_track_paper.lifecycle import process_tick
from fast_track_paper.close import daily_close
from fast_track_paper.analytics import calculate_analytics
from fast_track_paper.checkpoint import save_checkpoint
from fast_track_paper.source import resolve_daily_source

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v106_33_to_v108_64/input/"
        "fast_track_paper_policy.json"
    )
    source=resolve_daily_source(root)
    prices=load_json(
        root/"release/v106_33_to_v108_64/input/"
        "paper_price_scenario.json"
    )
    actual_dir=root/"release/v106_33_to_v108_64/actual"
    cycle_ledger=actual_dir/"fast_track_cycle_ledger.jsonl"
    daily_ledger=actual_dir/"daily_performance_ledger.jsonl"

    source_ready=(
        source.get("state")=="DAILY_PAPER_TRADING_RUN_COMPLETED"
        and source.get("paper_simulation_authorized") is True
    )
    session=(source.get("selected_session",{}).get("session") or {})
    cycle_id=digest({
        "run_id":source.get("run_id"),
        "session_id":session.get("session_id"),
        "policy_version":policy.get("policy_version"),
    })[:24]

    prior_cycles=read_jsonl(cycle_ledger)
    duplicate=any(row.get("cycle_id")==cycle_id for row in prior_cycles)
    if duplicate:
        body={
            "stage":"V108.64",
            "stage_range":"V106.33-V108.64",
            "state":"FAST_TRACK_PAPER_CYCLE_DUPLICATE_BLOCKED",
            "status":"PASS",
            "cycle_id":cycle_id,
            "source_recovery":source.get("source_recovery",{}),
            "actual_orders_submitted":0,
            "paper_only":True,
            "live_trading_enabled":False,
            "next_phase":"V109_01_TO_V110_64_AUTONOMOUS_PAPER_OPERATIONS",
        }
        body["certificate_sha256"]=digest(body)
        write_json(actual_dir/"fast_track_paper_result.json",body)
        return body

    if not source_ready:
        body={
            "stage":"V108.64",
            "stage_range":"V106.33-V108.64",
            "state":"FAST_TRACK_PAPER_SOURCE_REQUIRED",
            "status":"PASS",
            "cycle_id":cycle_id,
            "source_recovery":source.get("source_recovery",{}),
            "actual_orders_submitted":0,
            "paper_only":True,
            "live_trading_enabled":False,
            "next_phase":"V109_01_TO_V110_64_AUTONOMOUS_PAPER_OPERATIONS",
        }
        body["certificate_sha256"]=digest(body)
        write_json(actual_dir/"fast_track_paper_result.json",body)
        return body

    account_equity=float(policy.get("starting_equity",100000.0))
    starting_cash=float(policy.get("starting_cash",100000.0))
    orders=build_orders(
        source.get("daily_plan",{}),
        account_equity,
        prices.get("reference_prices",{}),
        policy.get("strategy_symbol_map",{}),
    )
    fills=simulate_fills(orders,policy)
    positions=open_positions(fills)
    existing=load_json(
        actual_dir/"paper_position_state.json"
    ).get("positions",[])
    positions=merge_positions(existing,positions)

    all_exits=[]
    tick_results=[]
    for tick in prices.get("intraday_ticks",[]):
        processed=process_tick(
            positions,
            tick.get("prices",{}),
            policy,
        )
        positions=processed["positions"]
        all_exits.extend(processed["exits"])
        tick_results.append({
            "tick":tick.get("tick"),
            "prices":tick.get("prices",{}),
            "exit_count":len(processed["exits"]),
        })

    close_result=daily_close(
        starting_cash,
        positions,
        fills,
        all_exits,
        prices.get("closing_prices",{}),
    )
    prior_daily=read_jsonl(daily_ledger)
    analytics=calculate_analytics(
        prior_daily,
        close_result,
        account_equity,
    )
    state="FAST_TRACK_PAPER_EXECUTION_AND_ANALYTICS_COMPLETE"
    checkpoint=save_checkpoint(
        actual_dir/"fast_track_checkpoint.json",
        cycle_id,
        state,
        close_result.get("open_positions",[]),
        close_result,
    )
    write_json(
        actual_dir/"paper_position_state.json",
        {"positions":close_result.get("open_positions",[])},
    )
    observed_at=datetime.now(timezone.utc).isoformat()
    summary={
        "stage":"V108.64",
        "stage_range":"V106.33-V108.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed_at,
        "cycle_id":cycle_id,
        "source_run_id":source.get("run_id"),
        "source_recovery":source.get("source_recovery",{}),
        "session_id":session.get("session_id"),
        "session_date":session.get("session_date"),
        "paper_order_count":len(orders),
        "filled_count":sum(1 for row in fills if row["state"]=="FILLED"),
        "partial_fill_count":sum(
            1 for row in fills if row["state"]=="PARTIAL_FILL"
        ),
        "not_filled_count":sum(
            1 for row in fills if row["state"]=="NOT_FILLED"
        ),
        "exit_count":len(all_exits),
        "orders":orders,
        "fills":fills,
        "tick_results":tick_results,
        "exits":all_exits,
        "daily_close":close_result,
        "analytics":analytics,
        "checkpoint":checkpoint,
        "paper_orders_simulated":len(orders),
        "paper_fills_processed":sum(
            1 for row in fills if row["filled_quantity"]>0
        ),
        "actual_broker_orders_submitted":0,
        "actual_orders_submitted":0,
        "paper_only":True,
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "next_phase":"V109_01_TO_V110_64_AUTONOMOUS_PAPER_OPERATIONS",
    }
    summary["certificate_sha256"]=digest(summary)
    write_json(actual_dir/"fast_track_paper_result.json",summary)
    write_json(actual_dir/"daily_close_report.json",close_result)
    write_json(actual_dir/"performance_analytics.json",analytics)
    for row in orders:
        append_jsonl(actual_dir/"paper_order_ledger.jsonl",row)
    for row in fills:
        append_jsonl(actual_dir/"paper_fill_ledger.jsonl",row)
    for row in all_exits:
        append_jsonl(actual_dir/"paper_exit_ledger.jsonl",row)
    append_jsonl(cycle_ledger,{
        "observed_at":observed_at,
        "cycle_id":cycle_id,
        "state":state,
        "session_date":session.get("session_date"),
        "paper_order_count":len(orders),
        "paper_fills_processed":summary["paper_fills_processed"],
        "exit_count":len(all_exits),
        "ending_equity":close_result.get("ending_equity"),
        "actual_orders_submitted":0,
    })
    append_jsonl(daily_ledger,{
        "observed_at":observed_at,
        "session_date":session.get("session_date"),
        "ending_equity":close_result.get("ending_equity"),
        "daily_return_pct":analytics.get("daily_return_pct"),
        "total_pnl":close_result.get("total_pnl"),
    })
    return summary
