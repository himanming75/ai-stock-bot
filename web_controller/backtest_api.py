from __future__ import annotations
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import copy
import json
import os
import uuid

from automated_backtest.dashboard import build_dashboard_payload
from automated_backtest.engine import evaluate as run_existing_backtest
from tools.discover_existing_backtest_and_build_feed import build as build_canonical_feed
from tools.build_backtest_provenance_quality_gate import build as build_quality_gate

POLICY_REL=Path("release/v98_01_to_v98_32/input/automated_backtest_policy.json")
RESULT_REL=Path("release/v98_01_to_v98_32/actual/automated_backtest_result.json")
SELECTED_DIR=Path("runtime/web_backtest_runs")
LATEST_SELECTED=SELECTED_DIR/"latest_selected_backtest.json"

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def _write_json(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True,default=str),encoding="utf-8")
    os.replace(tmp,path)

def _options(root:Path)->dict[str,Any]:
    policy=_load_json(root/POLICY_REL)
    return {
        "strategies":list(policy.get("strategies") or []),
        "datasets":list(policy.get("datasets") or []),
        "windows":list(policy.get("windows") or []),
        "policy_version":policy.get("policy_version"),
        "starting_equity":policy.get("starting_equity"),
        "commission_bps":policy.get("commission_bps"),
        "slippage_bps":policy.get("slippage_bps"),
    }


def _current_strategy(root:Path)->dict[str,Any]:
    cfg=_load_json(root/"release/v146_01_to_v150_64/config/strategy_config.json")
    if not cfg:
        # fallback: strategy manager may use a different release path locally
        for p in [
            root/"release/v151_01_to_v155_64/config/strategy_config.json",
            root/"release/v141_01_to_v145_64/config/strategy_config.json",
        ]:
            cfg=_load_json(p)
            if cfg:
                break
    enabled=[]
    for name,row in (cfg.get("strategies") or {}).items():
        if isinstance(row,dict) and row.get("enabled"):
            enabled.append({"name":name,"weight_pct":row.get("weight_pct")})
    return {
        "enabled_strategies":enabled,
        "symbols":cfg.get("symbols",[]),
        "risk":cfg.get("risk",{}),
        "paper_only":cfg.get("paper_only",True),
        "live_submission_enabled":cfg.get("live_submission_enabled",False),
    }

def _ai_state(root:Path)->dict[str,Any]:
    health=_load_json(root/"runtime/ai_ml_model_health_v2_2_16/latest_ml_model_health.json")
    rec=_load_json(root/"runtime/ai_ml_research_recommendation_v2_2_22/latest_ml_research_recommendation.json")
    cand=_load_json(root/"runtime/ai_ml_candidate_evaluation_v2_2_18/latest_ml_candidate_evaluation_snapshot.json")
    return {
        "model_health":health.get("model_health","NOT_AVAILABLE"),
        "research_action":rec.get("recommended_research_action",health.get("research_action","WAIT")),
        "research_comparison_allowed":bool(rec.get("research_comparison_allowed",False)),
        "candidate_research_ready":bool(cand.get("candidate_research_ready",False)),
        "best_shadow_research_horizon":cand.get("best_shadow_research_horizon"),
    }

def _candidate_from_selected(selected:dict[str,Any])->dict[str,Any]:
    result=selected.get("result") or {}
    aggregation=result.get("aggregation") or {}
    top=aggregation.get("top_result") or {}
    selection=selected.get("selection") or {}
    available=bool(selected and (top or selection))
    return {
        "available":available,
        "selection":selection,
        "state":result.get("state"),
        "status":result.get("status"),
        "top_result":top,
        "automation_score":top.get("automation_score"),
        "total_return_pct":top.get("total_return_pct"),
        "maximum_drawdown_pct":top.get("maximum_drawdown_pct"),
        "win_rate_pct":top.get("win_rate_pct"),
        "trade_count":top.get("trade_count"),
    }

def _comparison(root:Path,selected:dict[str,Any])->dict[str,Any]:
    current=_current_strategy(root)
    ai=_ai_state(root)
    candidate=_candidate_from_selected(selected)

    reasons=[]
    decision="KEEP_CURRENT_WAIT"
    if not candidate["available"]:
        reasons.append("NO_SELECTED_BACKTEST_CANDIDATE")
    if not ai["research_comparison_allowed"]:
        reasons.append("AI_RESEARCH_COMPARISON_NOT_READY")
    if ai["model_health"]!="GREEN":
        reasons.append("AI_MODEL_HEALTH_NOT_GREEN")

    if candidate["available"] and ai["research_comparison_allowed"] and ai["model_health"]=="GREEN":
        decision="CANDIDATE_READY_FOR_MANUAL_RESEARCH_REVIEW"

    return {
        "current_strategy":current,
        "candidate":candidate,
        "ai":ai,
        "recommendation":{
            "decision":decision,
            "reasons":reasons,
            "automatic_strategy_change":False,
            "automatic_threshold_change":False,
            "automatic_risk_change":False,
            "automatic_paper_execution_change":False,
            "automatic_live_execution_change":False,
        },
    }

def get_payload(root: Path) -> dict[str, Any]:
    automated = build_dashboard_payload(root)
    canonical = _load_json(
        root/"runtime/canonical_backtest_feed/backtest_discovery_report.json"
    )
    quality = _load_json(
        root/"runtime/backtest_provenance_quality_gate/latest_provenance_quality_report.json"
    )
    latest_selected=_load_json(root/LATEST_SELECTED)
    return {
        "automated": automated,
        "canonical": canonical,
        "quality": quality,
        "options":_options(root),
        "latest_selected":latest_selected,
        "comparison":_comparison(root,latest_selected),
        "safety": {
            "existing_backtest_engine_reused": True,
            "original_v98_policy_persistently_modified": False,
            "selected_policy_temporary_only": True,
            "new_backtest_engine_created": False,
            "new_strategy_created": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "actual_orders_submitted": 0,
        },
    }

def _one_by_id(rows:list[dict[str,Any]],key:str,value:str)->dict[str,Any]|None:
    for row in rows:
        if str(row.get(key))==value:
            return copy.deepcopy(row)
    return None

def _run_selected(root:Path,body:dict[str,Any])->dict[str,Any]:
    policy_path=root/POLICY_REL
    result_path=root/RESULT_REL
    original_text=policy_path.read_text(encoding="utf-8-sig")
    original_policy=json.loads(original_text)
    original_result=result_path.read_bytes() if result_path.exists() else None

    strategy_id=str(body.get("strategy_id",""))
    dataset_id=str(body.get("dataset_id",""))
    window_id=str(body.get("window_id",""))
    strategy=_one_by_id(list(original_policy.get("strategies") or []),"strategy_id",strategy_id)
    dataset=_one_by_id(list(original_policy.get("datasets") or []),"dataset_id",dataset_id)
    window=_one_by_id(list(original_policy.get("windows") or []),"window_id",window_id)
    if not strategy or not dataset or not window:
        return {
            "ok":False,
            "error":"INVALID_SELECTION",
            "strategy_id":strategy_id,
            "dataset_id":dataset_id,
            "window_id":window_id,
            "actual_orders_submitted":0,
            "live_trading_enabled":False,
        }

    selected=copy.deepcopy(original_policy)
    strategy["enabled"]=True
    selected["strategies"]=[strategy]
    selected["datasets"]=[dataset]
    selected["windows"]=[window]
    selected["policy_version"]=str(original_policy.get("policy_version","V98.01"))+"-WEB-SELECTED"

    run_id=f"WEBBT-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    try:
        _write_json(policy_path,selected)
        result=run_existing_backtest(root,force=bool(body.get("force",False)))
        record={
            "web_run_id":run_id,
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "selection":{
                "strategy_id":strategy_id,
                "dataset_id":dataset_id,
                "window_id":window_id,
                "force":bool(body.get("force",False)),
            },
            "temporary_policy":selected,
            "result":result,
            "safety":{
                "original_policy_restored":False,
                "broker_write_enabled":False,
                "order_submission_enabled":False,
                "live_trading_enabled":False,
                "actual_orders_submitted":0,
            },
        }
    finally:
        policy_path.write_text(original_text,encoding="utf-8")
        if original_result is None:
            if result_path.exists():
                result_path.unlink()
        else:
            result_path.parent.mkdir(parents=True,exist_ok=True)
            result_path.write_bytes(original_result)

    record["safety"]["original_policy_restored"]=True
    dest=root/SELECTED_DIR/f"{run_id}.json"
    _write_json(dest,record)
    _write_json(root/LATEST_SELECTED,record)
    return {
        "ok":record["result"].get("status")=="PASS",
        "action":"run_selected",
        "web_run_id":run_id,
        "selection":record["selection"],
        "result":record["result"],
        "original_policy_restored":True,
        "actual_orders_submitted":0,
        "live_trading_enabled":False,
    }

def action_payload(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action", ""))
    if action == "refresh_feed":
        canonical = build_canonical_feed(root)
        quality = build_quality_gate(root)
        return {
            "ok": True,
            "action": action,
            "canonical": canonical,
            "quality": quality,
            "actual_orders_submitted": 0,
            "live_trading_enabled": False,
        }
    if action in {"run_existing", "run_existing_force"}:
        result = run_existing_backtest(
            root, force=(action == "run_existing_force")
        )
        return {
            "ok": result.get("status") == "PASS",
            "action": action,
            "result": result,
            "actual_orders_submitted": 0,
            "live_trading_enabled": False,
        }
    if action=="run_selected":
        return _run_selected(root,body)
    return {
        "ok": False,
        "error": "ACTION_NOT_ALLOWED",
        "action": action,
        "actual_orders_submitted": 0,
        "live_trading_enabled": False,
    }
