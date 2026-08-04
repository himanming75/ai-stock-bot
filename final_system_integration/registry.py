from __future__ import annotations
from pathlib import Path
from typing import Any
from final_system_integration.io import load_json

SOURCES = [
    ("MARKET_REGIME","release/v93_33_to_v93_64/actual/multi_timeframe_regime_result.json",{"MULTI_TIMEFRAME_REGIME_READY"}),
    ("META_STRATEGY","release/v94_01_to_v94_32/actual/meta_strategy_result.json",{"META_STRATEGY_ENGINE_READY"}),
    ("PAPER_EXECUTION","release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json",{"PAPER_EXECUTION_SIMULATION_COMPLETED","PAPER_EXECUTION_SIMULATION_DUPLICATE_CYCLE_BLOCKED"}),
    ("POSITION_LIFECYCLE","release/v95_33_to_v95_64/actual/paper_position_lifecycle_result.json",{"PAPER_POSITION_LIFECYCLE_HOLD","PAPER_POSITION_LIFECYCLE_COMPLETED"}),
    ("ACCOUNT_RECONCILIATION","release/v96_01_to_v96_32/actual/paper_account_reconciliation_result.json",{"PAPER_ACCOUNT_RECONCILIATION_PASS"}),
    ("BROKER_RECONCILIATION","release/v97_33_to_v97_64/actual/paper_broker_snapshot_reconciliation_result.json",{"PAPER_BROKER_SNAPSHOT_RECONCILIATION_PASS"}),
    ("BACKTEST_BATCH","release/v98_33_to_v98_64/actual/backtest_batch_result.json",{"BACKTEST_BATCH_REGRESSION_READY"}),
    ("PORTFOLIO_MANAGER","release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json",{"AI_PORTFOLIO_MANAGER_READY"}),
    ("AI_RISK_MANAGER","release/v100_01_to_v100_32/actual/ai_risk_manager_result.json",{"AI_RISK_MANAGER_READY"}),
    ("RISK_BUDGET","release/v100_33_to_v100_64/actual/risk_budget_allocation_result.json",{"RISK_BUDGET_ALLOCATION_READY"}),
    ("ADAPTIVE_REBALANCE","release/v101_33_to_v101_64/actual/adaptive_rebalance_optimization_result.json",{"ADAPTIVE_REBALANCE_OPTIMIZATION_READY","ADAPTIVE_REBALANCE_OPTIMIZATION_NO_ACTION"}),
    ("MASTER_ORCHESTRATOR","release/v102_01_to_v102_32/actual/master_ai_orchestrator_result.json",{"MASTER_AI_ORCHESTRATOR_READY"}),
    ("AUTONOMOUS_DECISION","release/v102_33_to_v102_64/actual/autonomous_decision_result.json",{"AUTONOMOUS_DECISION_READY_FOR_MANUAL_APPROVAL","AUTONOMOUS_DECISION_HOLD","AUTONOMOUS_DECISION_REVIEW_REQUIRED","AUTONOMOUS_DECISION_BLOCKED"}),
    ("AUTONOMOUS_CYCLE","release/v103_01_to_v103_32/actual/autonomous_cycle_result.json",{"AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL","AUTONOMOUS_CYCLE_HOLD","AUTONOMOUS_CYCLE_REVIEW_REQUIRED","AUTONOMOUS_CYCLE_BLOCKED","AUTONOMOUS_CYCLE_DUPLICATE_BLOCKED"}),
    ("MULTI_DAY_SCHEDULER","release/v103_33_to_v103_64/actual/multi_day_scheduler_result.json",{"MULTI_DAY_SCHEDULER_READY"}),
    ("CONTINUOUS_ENGINE","release/v104_01_to_v104_32/actual/continuous_autonomous_engine_result.json",{"CONTINUOUS_AUTONOMOUS_ENGINE_WAITING_FOR_MANUAL_APPROVAL","CONTINUOUS_AUTONOMOUS_ENGINE_HOLD","CONTINUOUS_AUTONOMOUS_ENGINE_READY"}),
    ("CONTINUOUS_RUNTIME","release/v104_33_to_v104_64/actual/continuous_service_runtime_result.json",{"CONTINUOUS_SERVICE_RUNTIME_READY"}),
]

def collect(root: Path) -> list[dict[str, Any]]:
    rows=[]
    for module_id,path,allowed in SOURCES:
        value=load_json(root/path)
        state=value.get("state")
        status=value.get("status")
        present=bool(value)
        ready=present and status=="PASS" and state in allowed
        rows.append({
            "module_id":module_id,
            "source_path":path,
            "present":present,
            "state":state,
            "status":status,
            "ready":ready,
            "actual_orders_submitted":value.get("actual_orders_submitted",0),
            "execution_authorized":value.get("execution_authorized",False),
            "paper_only":value.get("paper_only",True),
        })
    return rows
