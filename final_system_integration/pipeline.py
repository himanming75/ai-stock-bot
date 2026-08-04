from __future__ import annotations
from typing import Any

ORDER = [
    "MARKET_REGIME","META_STRATEGY","BACKTEST_BATCH","PORTFOLIO_MANAGER",
    "AI_RISK_MANAGER","RISK_BUDGET","ADAPTIVE_REBALANCE",
    "AUTONOMOUS_DECISION","AUTONOMOUS_CYCLE","MULTI_DAY_SCHEDULER",
    "CONTINUOUS_ENGINE","CONTINUOUS_RUNTIME","PAPER_EXECUTION",
    "POSITION_LIFECYCLE","ACCOUNT_RECONCILIATION","BROKER_RECONCILIATION",
    "MASTER_ORCHESTRATOR",
]

def build_pipeline(modules: list[dict[str, Any]]) -> dict[str, Any]:
    lookup={row["module_id"]:row for row in modules}
    steps=[]
    blocked=False
    for index,module_id in enumerate(ORDER,start=1):
        row=lookup.get(module_id,{})
        ready=bool(row.get("ready"))
        if blocked:
            state="BLOCKED_BY_PREVIOUS"
        elif ready:
            state="READY"
        else:
            state="SOURCE_NOT_READY"
            blocked=True
        steps.append({
            "step":index,
            "module_id":module_id,
            "state":state,
            "source_state":row.get("state"),
        })
    return {
        "steps":steps,
        "total_steps":len(steps),
        "ready_steps":sum(1 for row in steps if row["state"]=="READY"),
        "blocked_steps":sum(1 for row in steps if row["state"]!="READY"),
        "passed":all(row["state"]=="READY" for row in steps),
    }
