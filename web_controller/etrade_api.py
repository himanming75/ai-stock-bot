from __future__ import annotations
from pathlib import Path
from typing import Any
import importlib
import json
import os
import subprocess
from datetime import datetime, timezone

def _safe_json(path:Path)->dict[str,Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig",errors="replace"))
    except Exception:
        return {}

def _module_present(name:str)->bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False

def _v2_1_10_status()->dict[str,Any]:
    try:
        from broker_integration_v1.eligible_signal_to_sandbox_bridge_status_v2_1_10 import build_v2_1_10_status
        return build_v2_1_10_status()
    except Exception as exc:
        return {"status":"NOT_AVAILABLE","error_type":type(exc).__name__}

def _recent_artifacts(root:Path)->list[dict[str,Any]]:
    rows=[]
    candidates=[]
    for base in (root/"runtime",root/"release"):
        if not base.exists():
            continue
        for p in base.rglob("*.json"):
            low=str(p).lower()
            if "etrade" in low or "broker_integration" in low or "threshold_sensitivity" in low:
                try:
                    stat=p.stat()
                    candidates.append((stat.st_mtime,p,stat.st_size))
                except OSError:
                    pass
    for mtime,p,size in sorted(candidates,reverse=True)[:25]:
        try:
            rel=str(p.relative_to(root)).replace("\\","/")
        except Exception:
            rel=str(p)
        rows.append({
            "path":rel,
            "modified_utc":datetime.fromtimestamp(mtime,timezone.utc).isoformat(),
            "size_bytes":size,
        })
    return rows


def _production_result(root:Path)->dict[str,Any]:
    path=root/"release/v4001_4200_etrade_production_routing/actual/explicit_production_read_result.json"
    row=_safe_json(path)
    if not row:
        return {
            "available":False,
            "status":"NO_PRODUCTION_READ_SNAPSHOT",
            "account":{},
            "positions":[],
            "orders":[],
        }
    return {
        "available":True,
        "status":row.get("status"),
        "generated_at":row.get("generated_at"),
        "account":row.get("account") or {},
        "positions":row.get("positions") or [],
        "orders":row.get("orders") or [],
        "actual_external_network_used":bool(row.get("actual_external_network_used")),
        "actual_broker_read_performed":bool(row.get("actual_broker_read_performed")),
        "actual_broker_write_performed":bool(row.get("actual_broker_write_performed")),
        "actual_order_submission_performed":bool(row.get("actual_order_submission_performed")),
        "actual_live_orders_submitted":int(row.get("actual_live_orders_submitted") or 0),
    }

def _production_session_status()->dict[str,Any]:
    names=[
        "ETRADE_CONSUMER_KEY",
        "ETRADE_CONSUMER_SECRET",
        "ETRADE_ACCESS_TOKEN",
        "ETRADE_ACCESS_SECRET",
    ]
    return {
        "environment":os.environ.get("ETRADE_ENVIRONMENT","").upper(),
        "production_read_acknowledged":os.environ.get("ETRADE_ALLOW_PRODUCTION_READ","").upper()=="YES",
        "all_credentials_present":all(bool(os.environ.get(n)) for n in names),
        "access_token_present":bool(os.environ.get("ETRADE_ACCESS_TOKEN")),
        "access_secret_present":bool(os.environ.get("ETRADE_ACCESS_SECRET")),
        "credential_values_exposed":False,
    }

def _audit_files(root:Path)->dict[str,Any]:
    names=[
        "START_V2_1_31_4_CAPTURE_AND_AUDIT.ps1",
        "START_V2_1_31_4_CONTINUOUS_THRESHOLD_AUDIT.ps1",
        "STOP_V2_1_31_4_CONTINUOUS_THRESHOLD_AUDIT.ps1",
        "VERIFY_V2_1_31_4_THRESHOLD_SENSITIVITY_AUDIT.ps1",
    ]
    present={name:(root/name).exists() for name in names}
    return {
        "installed":all(present.values()),
        "files":present,
        "continuous_audit_default_started_by_web":False,
    }

def get_payload(root:Path)->dict[str,Any]:
    v210=_v2_1_10_status()
    audit=_audit_files(root)
    return {
        "stack":{
            "broker_package_present":(root/"broker_integration_v1").exists(),
            "v2_readonly_present":_module_present("broker_integration_v1.etrade_network_transport_v2"),
            "oauth_flow_v2_present":_module_present("broker_integration_v1.etrade_oauth_flow_v2"),
            "sandbox_order_transport_present":_module_present("broker_integration_v1.etrade_sandbox_order_transport_v2_1"),
            "v2_1_10_present":_module_present("broker_integration_v1.eligible_signal_to_sandbox_bridge_v2_1_10"),
            "v2_1_10_status":v210,
        },
        "credentials":{
            "consumer_key_present":bool(os.environ.get("ETRADE_CONSUMER_KEY")),
            "consumer_secret_present":bool(os.environ.get("ETRADE_CONSUMER_SECRET")),
            "credential_values_exposed":False,
            "token_persistence_requested_by_this_web_integration":False,
        },
        "audit":audit,
        "production_session":_production_session_status(),
        "production_readonly":_production_result(root),
        "recent_artifacts":_recent_artifacts(root),
        "safety":{
            "read_only_get_transport_available":_module_present("broker_integration_v1.etrade_network_transport_v2"),
            "sandbox_only_bridge":bool(v210.get("sandbox_only",True)),
            "production_order_post_allowed":False,
            "live_trading_enabled":False,
            "web_live_order_action_available":False,
            "web_production_oauth_action_available":False,
            "web_token_storage_added":False,
            "actual_live_orders_submitted":0,
        },
    }

def _run_ps1(root:Path,name:str,timeout:int=180)->dict[str,Any]:
    path=root/name
    if not path.exists():
        return {"ok":False,"error":"SCRIPT_NOT_FOUND","script":name}
    try:
        cp=subprocess.run(
            ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-File",str(path)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out=(cp.stdout or "")[-12000:]
        err=(cp.stderr or "")[-6000:]
        return {
            "ok":cp.returncode==0,
            "script":name,
            "returncode":cp.returncode,
            "stdout":out,
            "stderr":err,
            "production_order_post_allowed":False,
            "live_trading_enabled":False,
            "actual_live_orders_submitted":0,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok":False,"error":"TIMEOUT","script":name,
            "production_order_post_allowed":False,
            "live_trading_enabled":False,
            "actual_live_orders_submitted":0,
        }

def action_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    action=str(body.get("action",""))
    if action=="credential_preflight":
        return {
            "ok":True,
            "action":action,
            "consumer_key_present":bool(os.environ.get("ETRADE_CONSUMER_KEY")),
            "consumer_secret_present":bool(os.environ.get("ETRADE_CONSUMER_SECRET")),
            "credential_values_exposed":False,
            "network_call_performed":False,
            "order_call_performed":False,
        }
    if action=="run_v2_1_31_4_shadow_audit":
        return _run_ps1(root,"START_V2_1_31_4_CAPTURE_AND_AUDIT.ps1",180)
    if action=="verify_v2_1_31_4":
        return _run_ps1(root,"VERIFY_V2_1_31_4_THRESHOLD_SENSITIVITY_AUDIT.ps1",180)
    if action=="run_production_readonly_snapshot":
        session=_production_session_status()
        if session["environment"]!="PRODUCTION":
            return {
                "ok":False,
                "error":"ETRADE_ENVIRONMENT_NOT_PRODUCTION",
                "production_session":session,
                "actual_live_orders_submitted":0,
                "live_trading_enabled":False,
            }
        if not session["production_read_acknowledged"]:
            return {
                "ok":False,
                "error":"PRODUCTION_READ_NOT_ACKNOWLEDGED",
                "production_session":session,
                "actual_live_orders_submitted":0,
                "live_trading_enabled":False,
            }
        if not session["all_credentials_present"]:
            return {
                "ok":False,
                "error":"ETRADE_PRODUCTION_READ_SESSION_NOT_CONNECTED",
                "production_session":session,
                "actual_live_orders_submitted":0,
                "live_trading_enabled":False,
            }
        script=root/"tools/run_etrade_production_read_explicit.py"
        if not script.exists():
            return {
                "ok":False,
                "error":"PRODUCTION_READ_RUNNER_NOT_FOUND",
                "actual_live_orders_submitted":0,
                "live_trading_enabled":False,
            }
        try:
            cp=subprocess.run(
                [str(root/".venv/Scripts/python.exe"),str(script)],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
                env=os.environ.copy(),
            )
            return {
                "ok":cp.returncode==0,
                "action":action,
                "returncode":cp.returncode,
                "snapshot":_production_result(root),
                "stdout":(cp.stdout or "")[-10000:],
                "stderr":(cp.stderr or "")[-5000:],
                "actual_broker_write_performed":False,
                "actual_order_submission_performed":False,
                "actual_live_orders_submitted":0,
                "live_trading_enabled":False,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok":False,
                "error":"PRODUCTION_READ_TIMEOUT",
                "actual_broker_write_performed":False,
                "actual_order_submission_performed":False,
                "actual_live_orders_submitted":0,
                "live_trading_enabled":False,
            }
    return {
        "ok":False,
        "error":"ACTION_NOT_ALLOWED",
        "action":action,
        "production_order_post_allowed":False,
        "live_trading_enabled":False,
        "actual_live_orders_submitted":0,
    }
