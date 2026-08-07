from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, sys

CANONICAL_STACK = {
    "broker_abstraction_adapter": "broker_abstraction/adapters/etrade.py",
    "adapter_foundation": "multi_broker_etrade/adapter.py",
    "credentials": "multi_broker_etrade/credentials.py",
    "oauth": "multi_broker_etrade/oauth.py",
    "oauth_session": "multi_broker_etrade_oauth/session.py",
    "oauth_workflow": "multi_broker_etrade_oauth/workflow.py",
    "sandbox_service": "multi_broker_etrade_sandbox_cert/service.py",
    "production_routing": "multi_broker_etrade_routing/service.py",
    "unified_portfolio": "multi_broker_etrade_unified/service.py",
    "reconciliation": "multi_broker_etrade_reconciliation/service.py",
    "health_monitoring": "multi_broker_etrade_health/service.py",
    "recovery": "multi_broker_etrade_recovery/service.py",
    "readonly_engine": "live_broker_readonly/engine.py",
    "readonly_credentials": "live_broker_readonly/credentials.py",
    "live_audit": "etrade_live_audit/canonicalizer.py",
    "kill_switch": "autonomous_risk_governor/kill_switch.py",
    "kill_switch_guard": "autonomous_risk_governor/kill_switch_guard.py",
}

EXISTING_VALIDATION_COMMANDS = [
    ("adapter_foundation_test", "RUN_V3401_TO_V3600_ETRADE_ADAPTER_FOUNDATION_TEST.ps1"),
    ("oauth_session_test", "RUN_V3601_TO_V3800_ETRADE_OAUTH_SESSION_TEST.ps1"),
    ("sandbox_certification_test", "RUN_V3801_TO_V4000_ETRADE_SANDBOX_CERTIFICATION_TEST.ps1"),
    ("production_routing_test", "RUN_V4001_TO_V4200_ETRADE_PRODUCTION_ROUTING_TEST.ps1"),
    ("unified_portfolio_test", "RUN_V4201_TO_V4400_ETRADE_UNIFIED_PORTFOLIO_TEST.ps1"),
    ("reconciliation_test", "RUN_V4401_TO_V4600_ETRADE_RECONCILIATION_TEST.ps1"),
    ("health_monitoring_test", "RUN_V4601_TO_V4800_ETRADE_HEALTH_MONITORING_TEST.ps1"),
    ("operational_readiness_test", "RUN_V4801_TO_V5000_ETRADE_OPERATIONAL_READINESS_TEST.ps1"),
    ("sandbox_certification_v8001_test", "RUN_V8001_TO_V8200_ETRADE_TEST.ps1"),
    ("phase3_live_canonicalization_verify", "VERIFY_PHASE3_ETRADE_LIVE_CANONICALIZATION.ps1"),
    ("phase4_single_account_binding_verify", "VERIFY_PHASE4_SINGLE_ACCOUNT_BINDING.ps1"),
]

def read_json(p: Path):
    try:
        x=json.loads(p.read_text(encoding="utf-8-sig"))
        return x if isinstance(x,dict) else {}
    except Exception:
        return {}

def credential_presence():
    groups={
        "etrade_consumer_key":["ETRADE_CONSUMER_KEY","E_TRADE_CONSUMER_KEY"],
        "etrade_consumer_secret":["ETRADE_CONSUMER_SECRET","E_TRADE_CONSUMER_SECRET"],
        "etrade_access_token":["ETRADE_ACCESS_TOKEN","E_TRADE_ACCESS_TOKEN"],
        "etrade_access_token_secret":["ETRADE_ACCESS_TOKEN_SECRET","E_TRADE_ACCESS_TOKEN_SECRET"],
    }
    return {name:any(bool(os.getenv(k)) for k in keys) for name,keys in groups.items()}

def file_contract(root: Path):
    rows=[]
    for role,rel in CANONICAL_STACK.items():
        p=root/rel
        rows.append({
            "role":role,
            "path":rel,
            "exists":p.is_file(),
            "size":p.stat().st_size if p.is_file() else None,
        })
    return rows

def run_existing_validation(root: Path):
    rows=[]
    for name,script in EXISTING_VALIDATION_COMMANDS:
        p=root/script
        if not p.exists():
            rows.append({"name":name,"script":script,"status":"NOT_PRESENT","exit_code":None,"tail":""})
            continue
        proc=subprocess.run(
            ["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(p)],
            cwd=str(root),capture_output=True,text=True,encoding="utf-8",errors="replace"
        )
        combined=(proc.stdout or "")+"\n"+(proc.stderr or "")
        rows.append({
            "name":name,
            "script":script,
            "status":"PASS" if proc.returncode==0 else "FAIL",
            "exit_code":proc.returncode,
            "tail":"\n".join(combined.splitlines()[-30:]),
        })
    return rows

def current_validation(root: Path):
    v=read_json(root/"runtime/paper_backtest_validation_analytics_v3/latest_validation_analytics.json")
    lr=v.get("live_readiness",{}) if isinstance(v,dict) else {}
    return {
        "closed_trades":int(lr.get("observed_closed_trades",0) or 0),
        "trading_days":int(lr.get("observed_trading_days",0) or 0),
        "financial_gate_eligible":bool(lr.get("eligible",False)),
        "status":lr.get("status","NOT_READY"),
    }

def build(root: Path, run_existing_tests: bool=False):
    root=Path(root)
    files=file_contract(root)
    creds=credential_presence()
    validation=current_validation(root)
    tests=run_existing_validation(root) if run_existing_tests else []

    canonical_present=all(x["exists"] for x in files)
    required_test_rows=[x for x in tests if x["status"]!="NOT_PRESENT"]
    existing_tests_pass=(all(x["status"]=="PASS" for x in required_test_rows)
                         if run_existing_tests and required_test_rows else None)

    hard_checks={
        "canonical_stack_present":canonical_present,
        "existing_validation_tests_pass":existing_tests_pass is True if run_existing_tests else None,
        "paper_validation_300_complete":validation["closed_trades"]>=300,
        "paper_validation_10_days_complete":validation["trading_days"]>=10,
        "paper_financial_gate_eligible":validation["financial_gate_eligible"],
        "etrade_credentials_present":all(creds.values()),
        "manual_arm_required":True,
        "live_auto_enable_off":True,
        "actual_live_submission_disabled":True,
    }

    readiness_without_credentials = (
        canonical_present
        and (existing_tests_pass is not False)
        and validation["closed_trades"]>=300
        and validation["trading_days"]>=10
        and validation["financial_gate_eligible"]
    )
    full_ready = readiness_without_credentials and all(creds.values())

    report={
        "stage":"ETRADE_CANONICAL_READONLY_INTEGRATION",
        "status":"READY_FOR_MANUAL_LIVE_STAGE1_REVIEW" if full_ready else "BLOCKED",
        "mode":"CANONICAL_STACK_READ_ONLY_VALIDATION",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "canonical_stack":files,
        "canonical_stack_present":canonical_present,
        "existing_validation_results":tests,
        "existing_validation_pass":existing_tests_pass,
        "credential_presence":creds,
        "credential_values_exposed":False,
        "paper_validation":validation,
        "hard_checks":hard_checks,
        "stage1_policy":{
            "max_live_order_notional":25.0,
            "max_live_orders_per_day":1,
            "max_concurrent_positions":1,
            "manual_arm_required":True,
            "kill_switch_required":True,
            "production_read_before_write_required":True,
            "account_binding_verification_required":True,
            "oauth_session_verification_required":True,
            "paper_closed_trade_requirement":300,
            "paper_trading_day_requirement":10,
            "automatic_live_enable":False,
        },
        "contracts":{
            "broker_write_performed":False,
            "live_order_submitted":False,
            "paper_order_submitted":False,
            "existing_etrade_adapter_modified":False,
            "existing_etrade_oauth_modified":False,
            "existing_routing_modified":False,
            "trading_configuration_changed":False,
            "live_auto_enable":False,
        },
        "next_action":(
            "WAIT_FOR_300_TRADE_VALIDATION"
            if validation["closed_trades"]<300 or validation["trading_days"]<10
            else "CONFIGURE_OR_VERIFY_ETRADE_CREDENTIALS"
            if not all(creds.values())
            else "MANUAL_LIVE_STAGE1_REVIEW"
        ),
    }

    out=root/"runtime/etrade_canonical_readonly_integration"
    out.mkdir(parents=True,exist_ok=True)
    (out/"latest_etrade_canonical_readonly_report.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )
    return report

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\stock-bot")
    ap.add_argument("--run-existing-tests",action="store_true")
    args=ap.parse_args()
    print(json.dumps(build(Path(args.root),run_existing_tests=args.run_existing_tests),indent=2,default=str))
