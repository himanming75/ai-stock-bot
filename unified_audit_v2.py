from pathlib import Path
from datetime import datetime, timezone
import json
from validation_analytics_v3 import main_report

def read_json(p):
    try:
        x=json.loads(p.read_text(encoding="utf-8-sig"))
        return x if isinstance(x,dict) else {}
    except Exception: return {}

def read_jsonl(p):
    if not p.exists(): return []
    out=[]
    for line in p.read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if not line.strip(): continue
        try:
            x=json.loads(line)
            if isinstance(x,dict): out.append(x)
        except Exception: pass
    return out

def build(root):
    root=Path(root); rt=root/"runtime"
    closed=read_jsonl(rt/"paper_full_auto_lifecycle/closed_round_trips.jsonl")
    exits=read_jsonl(rt/"paper_full_auto_lifecycle/exit_ledger.jsonl")
    validation=read_json(rt/"paper_validation_ops/latest_validation_operations_report.json")
    reliability=read_json(rt/"paper_operational_reliability_v2/latest_operational_reliability_report.json")
    watchdog=read_json(rt/"paper_operational_reliability_v2/watchdog_latest.json")
    analytics=main_report(root)
    etrade_live=read_json(rt/"etrade_live_readiness_stage1/latest_etrade_live_readiness.json")
    baseline=analytics.get("validation_baseline",{}); base=max(0,int(baseline.get("baseline_closed_trade_count",0) or 0))
    validation_closed=closed[base:]
    events=[]
    for x in validation_closed:
        events.append({"event_type":"CLOSED_TRADE","time":x.get("exit_time") or x.get("exit_time_utc") or x.get("generated_at_utc") or "",
                       "symbol":x.get("symbol",""),"side":x.get("side","LONG"),"quantity":x.get("quantity"),
                       "realized_pl":x.get("realized_pl") if x.get("realized_pl") is not None else x.get("realized_pnl"),
                       "reason":x.get("exit_reason") or x.get("reason","")})
    for x in exits:
        events.append({"event_type":"EXIT_SUBMITTED","time":x.get("submitted_at_utc") or "","symbol":x.get("symbol",""),
                       "side":"SELL","quantity":x.get("qty"),"realized_pl":None,"reason":x.get("reason","")})
    events.sort(key=lambda x:x.get("time",""),reverse=True)
    broker=reliability.get("broker",{})
    progress=dict(validation.get("progress",{})); progress["closed_trades"]=len(validation_closed); progress["closed_trade_target"]=300
    progress["closed_trade_target_progress_pct"]=round(min(100.0,len(validation_closed)/300*100),2)
    ai_link=analytics.get("ai_outcome_linkage",{})
    report={"stage":"PAPER_UNIFIED_TRADE_AUDIT_DASHBOARD_V2","status":"PASS","mode":"READ_ONLY",
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),"broker_write_performed":False,
            "trading_configuration_changed":False,"validation_progress":progress,
            "validation_metrics":analytics.get("paper_trade_metrics",{}),
            "symbol_breakdown":analytics.get("symbol_breakdown",[]),
            "exit_reason_breakdown":analytics.get("exit_reason_breakdown",[]),
            "time_bucket_breakdown":analytics.get("time_bucket_breakdown",[]),
            "confidence_breakdown":analytics.get("confidence_breakdown",[]),
            "paper_vs_backtest":analytics.get("paper_vs_backtest",{}),
            "ai_research_samples":analytics.get("ai_research_samples",{}),
            "ai_outcome_metrics":ai_link.get("metrics",{}),
            "ai_linked_trades":ai_link.get("rows",[]),
            "live_readiness":analytics.get("live_readiness",{}),
            "etrade_live_readiness":etrade_live,
            "reliability_health":reliability.get("health",{}),"watchdog":watchdog,
            "broker_snapshot":{"market_open":broker.get("market_open"),"position_count":broker.get("position_count",0),
                               "position_symbols":broker.get("position_symbols",[]),"open_order_count":broker.get("open_order_count",0),
                               "open_order_symbols":broker.get("open_order_symbols",[])},
            "recent_timeline":events[:100]}
    out=rt/"paper_unified_audit_v2"; out.mkdir(parents=True,exist_ok=True)
    (out/"latest_unified_trade_audit.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    return report

