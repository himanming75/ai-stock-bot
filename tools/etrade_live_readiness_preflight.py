from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, os, re

KEYWORDS=("etrade","e_trade","live_broker","live_order","account_binding","kill_switch","live_preflight")

def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def inventory(root: Path):
    rows=[]
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        s=str(p)
        if any(x in s.lower() for x in ("\\.git\\","\\.venv\\","\\archive\\","\\runtime\\")):
            continue
        rel=p.relative_to(root).as_posix()
        low=rel.lower()
        if any(k in low for k in KEYWORDS):
            rows.append({
                "path":rel,
                "suffix":p.suffix.lower(),
                "size":p.stat().st_size,
            })
    return rows

def credential_presence():
    # Presence only: never return values.
    groups={
        "etrade_consumer_key":["ETRADE_CONSUMER_KEY","E_TRADE_CONSUMER_KEY"],
        "etrade_consumer_secret":["ETRADE_CONSUMER_SECRET","E_TRADE_CONSUMER_SECRET"],
        "etrade_access_token":["ETRADE_ACCESS_TOKEN","E_TRADE_ACCESS_TOKEN"],
        "etrade_access_token_secret":["ETRADE_ACCESS_TOKEN_SECRET","E_TRADE_ACCESS_TOKEN_SECRET"],
    }
    return {name:any(bool(os.getenv(k)) for k in keys) for name,keys in groups.items()}

def local_live_flags(root: Path):
    hits=[]
    patterns=[
        re.compile(r"etrade_live_write_enabled",re.I),
        re.compile(r"live_submission_enabled",re.I),
        re.compile(r"live_write",re.I),
        re.compile(r"submit_live",re.I),
    ]
    for p in root.rglob("*.json"):
        s=str(p).lower()
        if any(x in s for x in ("\\.git\\","\\.venv\\","\\archive\\","\\runtime\\")):
            continue
        try:
            txt=p.read_text(encoding="utf-8-sig",errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(txt):
                hits.append(p.relative_to(root).as_posix())
                break
    return sorted(set(hits))

def build(root: Path):
    root=Path(root)
    validation=read_json(root/"runtime/paper_backtest_validation_analytics_v3/latest_validation_analytics.json")
    live_readiness=validation.get("live_readiness",{}) if isinstance(validation,dict) else {}
    closed=int(live_readiness.get("observed_closed_trades",0) or 0)
    days=int(live_readiness.get("observed_trading_days",0) or 0)
    creds=credential_presence()
    files=inventory(root)
    flags=local_live_flags(root)

    hard_checks={
        "paper_validation_300_complete":closed>=300,
        "paper_validation_10_days_complete":days>=10,
        "validation_financial_gate_eligible":bool(live_readiness.get("eligible",False)),
        "etrade_credentials_present":all(creds.values()),
        "live_auto_enable_off":True,
        "actual_live_order_submission_disabled":True,
        "manual_live_arm_required":True,
    }

    report={
        "stage":"ETRADE_LIVE_READINESS_STAGE1",
        "status":"READY_FOR_MANUAL_STAGE1_REVIEW" if all(hard_checks.values()) else "BLOCKED",
        "mode":"READ_ONLY_PREFLIGHT",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "etrade_local_inventory":files,
        "etrade_candidate_count":len(files),
        "credential_presence":creds,
        "credential_values_exposed":False,
        "local_live_flag_files":flags,
        "validation_snapshot":{
            "closed_trades":closed,
            "trading_days":days,
            "live_readiness_status":live_readiness.get("status","NOT_READY"),
        },
        "hard_checks":hard_checks,
        "stage1_policy":{
            "max_live_order_notional":25.0,
            "max_live_orders_per_day":1,
            "max_concurrent_positions":1,
            "automatic_live_enable":False,
            "manual_arm_required":True,
            "kill_switch_required":True,
            "paper_validation_required":True,
            "paper_closed_trade_requirement":300,
            "paper_trading_day_requirement":10,
        },
        "contracts":{
            "broker_write_performed":False,
            "live_order_submitted":False,
            "paper_order_submitted":False,
            "trading_configuration_changed":False,
            "existing_etrade_adapter_modified":False,
            "live_auto_enable":False,
        },
        "next_action":"WAIT_FOR_300_TRADE_VALIDATION" if closed<300 else "MANUAL_REVIEW_REQUIRED",
    }

    out=root/"runtime/etrade_live_readiness_stage1"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_etrade_live_readiness.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2))
