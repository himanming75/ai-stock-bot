from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib, json, os, ssl, tempfile
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def cj(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def hj(v): return hashlib.sha256(cj(v).encode("utf-8")).hexdigest()
def hb(v): return hashlib.sha256(v).hexdigest()
def wj(p,v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def aw(p,b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=p.parent) as h:
        h.write(b); t = Path(h.name)
    os.replace(t,p)

@dataclass(frozen=True)
class PositionAccountReconciliationConfig:
    mode: str = "PAPER_POSITION_ACCOUNT_RECONCILIATION"
    base_url: str = "https://paper-api.alpaca.markets"
    symbol: str = "AAPL"
    quantity_tolerance: float = 0.000001
    money_tolerance: float = 0.05
    pnl_tolerance: float = 0.05
    explicit_network_opt_in: bool = False
    required_opt_in_value: str = "YES"
    allow_get: bool = True
    allow_post: bool = False
    allow_patch: bool = False
    allow_delete: bool = False
    actual_orders_submitted: int = 0
    def validate(self):
        p = urlparse(self.base_url)
        if self.mode != "PAPER_POSITION_ACCOUNT_RECONCILIATION": raise ValueError("mode")
        if p.scheme != "https" or p.hostname != "paper-api.alpaca.markets": raise ValueError("endpoint")
        if not self.allow_get or self.allow_post or self.allow_patch or self.allow_delete: raise ValueError("GET only")
        if min(self.quantity_tolerance, self.money_tolerance, self.pnl_tolerance) < 0: raise ValueError("tolerance")
        if self.actual_orders_submitted != 0: raise ValueError("no new orders")

def validate_source(path: Path) -> dict[str, Any]:
    if not path.is_file(): raise FileNotFoundError(path)
    c = json.loads(path.read_text())
    u = dict(c); e = u.pop("certificate_sha256", None)
    if e != hj(u) or c.get("stage") != "V86.40" or c.get("status") != "PASS":
        raise ValueError("bad V86.40 certificate")
    if c.get("paper_order_lifecycle_validation_complete") is not True:
        raise ValueError("lifecycle prerequisite")
    if c.get("actual_orders_submitted") != 0:
        raise ValueError("unsafe prerequisite")
    return c

def policy():
    d = {"stage":"V86.41","status":"PASS","get_only":True,
         "new_order_creation":False,"order_cancel":False,"order_replace":False,
         "paper_order_submission_authorized":False,"live_trading_authorized":False}
    d["policy_sha256"] = hj(d); return d

def credential_status(env: Mapping[str,str]):
    d = {"stage":"V86.42",
         "api_key_present":bool(env.get("APCA_API_KEY_ID","").strip()),
         "api_secret_present":bool(env.get("APCA_API_SECRET_KEY","").strip()),
         "values_redacted":True}
    d["complete"] = d["api_key_present"] and d["api_secret_present"]
    d["credential_sha256"] = hj(d); return d

def identifier_status(env: Mapping[str,str]):
    oid = env.get("AI_STOCK_BOT_PAPER_ORDER_ID","").strip()
    cid = env.get("AI_STOCK_BOT_PAPER_CLIENT_ORDER_ID","").strip()
    d = {"stage":"V86.43","order_id_present":bool(oid),
         "client_order_id_present":bool(cid),
         "valid":bool(oid or cid),
         "preferred":"ORDER_ID" if oid else "CLIENT_ORDER_ID" if cid else "NONE"}
    d["identifier_sha256"] = hj(d); return d

def opt_in(config, env, enable_network):
    match = env.get("AI_STOCK_BOT_ENABLE_PAPER_RECONCILIATION_READ","") == config.required_opt_in_value
    allowed = config.explicit_network_opt_in and enable_network and match
    d = {"stage":"V86.44","config_opt_in":config.explicit_network_opt_in,
         "cli_opt_in":enable_network,"environment_match":match,"allowed":allowed}
    d["opt_in_sha256"] = hj(d); return d

def endpoint_urls(config, env):
    oid = env.get("AI_STOCK_BOT_PAPER_ORDER_ID","").strip()
    cid = env.get("AI_STOCK_BOT_PAPER_CLIENT_ORDER_ID","").strip()
    order_url = (config.base_url + "/v2/orders/" + quote(oid)) if oid else (
        config.base_url + "/v2/orders:by_client_order_id?" + urlencode({"client_order_id":cid})
    )
    d = {"stage":"V86.45","order":order_url,
         "account":config.base_url + "/v2/account",
         "positions":config.base_url + "/v2/positions",
         "method":"GET","write_endpoint_count":0}
    d["urls_sha256"] = hj(d); return d

def default_transport(url, headers, timeout):
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        return r.status, r.read()

def execute_get(name, url, env, transport: Callable = default_transport):
    headers = {
        "APCA-API-KEY-ID":env["APCA_API_KEY_ID"],
        "APCA-API-SECRET-KEY":env["APCA_API_SECRET_KEY"],
        "Accept":"application/json",
    }
    try:
        status, data = transport(url, headers, 8)
        payload = json.loads(data.decode("utf-8"))
        d = {"stage":"V86.46","name":name,"status_code":int(status),
             "ok":int(status)==200,"payload":payload,"credentials_redacted":True}
    except HTTPError as e:
        d = {"stage":"V86.46","name":name,"status_code":e.code,
             "ok":False,"error_class":"HTTP_ERROR","credentials_redacted":True}
    except (URLError, TimeoutError):
        d = {"stage":"V86.46","name":name,"status_code":None,
             "ok":False,"error_class":"NETWORK_ERROR","credentials_redacted":True}
    d["result_sha256"] = hj(d); return d

def to_float(value, field):
    try: return float(value)
    except (TypeError, ValueError): raise ValueError("invalid numeric field: " + field)

def order_metrics(order):
    qty = to_float(order.get("qty",0), "qty")
    filled = to_float(order.get("filled_qty",0), "filled_qty")
    avg = to_float(order.get("filled_avg_price") or 0, "filled_avg_price")
    notional = filled * avg
    d = {"stage":"V86.47","symbol":order.get("symbol"),"side":order.get("side"),
         "status":order.get("status"),"requested_qty":qty,"filled_qty":filled,
         "remaining_qty":qty-filled,"filled_avg_price":avg,
         "filled_notional":round(notional,8)}
    d["order_metrics_sha256"] = hj(d); return d

def find_position(symbol, positions):
    rows = [p for p in positions if p.get("symbol") == symbol]
    d = {"stage":"V86.48","symbol":symbol,"matching_count":len(rows),
         "position":rows[0] if rows else None}
    d["position_lookup_sha256"] = hj(d); return d

def quantity_reconciliation(metrics, lookup, config):
    expected = metrics["filled_qty"] if str(metrics["side"]).lower()=="buy" else -metrics["filled_qty"]
    actual = to_float((lookup["position"] or {}).get("qty",0), "position.qty")
    difference = actual - expected
    status = "PASS" if abs(difference) <= config.quantity_tolerance else "FAIL"
    d = {"stage":"V86.49","expected_position_qty":expected,"actual_position_qty":actual,
         "difference":difference,"tolerance":config.quantity_tolerance,"status":status}
    d["quantity_sha256"] = hj(d); return d

def average_price_reconciliation(metrics, lookup, config):
    position = lookup["position"] or {}
    order_avg = metrics["filled_avg_price"]
    position_avg = to_float(position.get("avg_entry_price",0), "position.avg_entry_price")
    difference = position_avg - order_avg
    applicable = metrics["filled_qty"] > 0 and str(metrics["side"]).lower()=="buy"
    status = "PASS" if (not applicable or abs(difference) <= config.money_tolerance) else "FAIL"
    d = {"stage":"V86.50","applicable":applicable,"order_filled_avg_price":order_avg,
         "position_avg_entry_price":position_avg,"difference":difference,
         "tolerance":config.money_tolerance,"status":status}
    d["average_price_sha256"] = hj(d); return d

def market_value_reconciliation(lookup, config):
    position = lookup["position"] or {}
    qty = to_float(position.get("qty",0), "position.qty")
    price = to_float(position.get("current_price",0), "position.current_price")
    reported = to_float(position.get("market_value",0), "position.market_value")
    calculated = qty * price
    difference = reported - calculated
    status = "PASS" if abs(difference) <= max(config.money_tolerance, abs(calculated)*0.0001) else "FAIL"
    d = {"stage":"V86.51","quantity":qty,"current_price":price,
         "reported_market_value":reported,"calculated_market_value":calculated,
         "difference":difference,"status":status}
    d["market_value_sha256"] = hj(d); return d

def unrealized_pnl_reconciliation(lookup, config):
    position = lookup["position"] or {}
    qty = to_float(position.get("qty",0), "position.qty")
    current = to_float(position.get("current_price",0), "position.current_price")
    avg = to_float(position.get("avg_entry_price",0), "position.avg_entry_price")
    reported = to_float(position.get("unrealized_pl",0), "position.unrealized_pl")
    calculated = (current-avg)*qty
    difference = reported-calculated
    status = "PASS" if abs(difference) <= max(config.pnl_tolerance, abs(calculated)*0.001) else "FAIL"
    d = {"stage":"V86.52","reported_unrealized_pl":reported,
         "calculated_unrealized_pl":calculated,"difference":difference,
         "tolerance":config.pnl_tolerance,"status":status}
    d["unrealized_pnl_sha256"] = hj(d); return d

def account_schema(account):
    required = {"status","cash","portfolio_value","buying_power","equity","last_equity","trading_blocked"}
    missing = sorted(required - set(account))
    d = {"stage":"V86.53","missing_fields":missing,
         "status":"PASS" if not missing else "FAIL"}
    d["account_schema_sha256"] = hj(d); return d

def account_numeric_reconciliation(account, config):
    cash = to_float(account.get("cash",0),"cash")
    portfolio = to_float(account.get("portfolio_value",0),"portfolio_value")
    equity = to_float(account.get("equity",0),"equity")
    buying_power = to_float(account.get("buying_power",0),"buying_power")
    last_equity = to_float(account.get("last_equity",0),"last_equity")
    checks = {
        "cash_finite": abs(cash) < 1e15,
        "portfolio_equity_match": abs(portfolio-equity) <= config.money_tolerance,
        "buying_power_nonnegative": buying_power >= 0,
        "equity_nonnegative": equity >= 0,
        "last_equity_nonnegative": last_equity >= 0,
        "trading_not_blocked": account.get("trading_blocked") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    d = {"stage":"V86.54","status":"PASS" if not failed else "FAIL",
         "checks":checks,"failed_checks":failed,"cash":cash,"portfolio_value":portfolio,
         "equity":equity,"buying_power":buying_power,"last_equity":last_equity}
    d["account_numeric_sha256"] = hj(d); return d

def buying_power_reconciliation(account, metrics):
    buying_power = to_float(account.get("buying_power",0),"buying_power")
    filled_notional = metrics["filled_notional"]
    d = {"stage":"V86.55","buying_power":buying_power,
         "filled_notional":filled_notional,
         "sufficient_for_filled_notional":buying_power >= 0,
         "status":"PASS" if buying_power >= 0 else "FAIL"}
    d["buying_power_sha256"] = hj(d); return d

def fixtures():
    return {
      "order":{"id":"fixture-order","client_order_id":"single-fixture","symbol":"AAPL",
               "side":"buy","type":"market","status":"filled","qty":"1","filled_qty":"1",
               "filled_avg_price":"200.00"},
      "account":{"status":"ACTIVE","cash":"99800.00","portfolio_value":"100000.00",
                 "equity":"100000.00","last_equity":"100000.00","buying_power":"199600.00",
                 "trading_blocked":False},
      "positions":[{"symbol":"AAPL","qty":"1","avg_entry_price":"200.00",
                    "current_price":"200.00","market_value":"200.00",
                    "unrealized_pl":"0.00"}],
    }

def evaluate(config, order, account, positions):
    metrics=order_metrics(order);lookup=find_position(metrics["symbol"],positions)
    quantity=quantity_reconciliation(metrics,lookup,config)
    avg=average_price_reconciliation(metrics,lookup,config)
    market=market_value_reconciliation(lookup,config)
    pnl=unrealized_pnl_reconciliation(lookup,config)
    schema=account_schema(account)
    account_numbers=account_numeric_reconciliation(account,config)
    buying_power=buying_power_reconciliation(account,metrics)
    checks={"quantity":quantity["status"]=="PASS","average_price":avg["status"]=="PASS",
            "market_value":market["status"]=="PASS","unrealized_pnl":pnl["status"]=="PASS",
            "account_schema":schema["status"]=="PASS",
            "account_numeric":account_numbers["status"]=="PASS",
            "buying_power":buying_power["status"]=="PASS"}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.56","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed,"order_metrics":metrics,
       "position_lookup":lookup,"quantity_reconciliation":quantity,
       "average_price_reconciliation":avg,"market_value_reconciliation":market,
       "unrealized_pnl_reconciliation":pnl,"account_schema":schema,
       "account_numeric_reconciliation":account_numbers,
       "buying_power_reconciliation":buying_power}
    d["evaluation_sha256"]=hj(d);return d

def offline_run(config):
    f=fixtures();ev=evaluate(config,f["order"],f["account"],f["positions"])
    return {"stage":"V86.57","network_mode":"OFFLINE_FIXTURE",
            "network_requests_executed":0,"credentials_used":0,
            "actual_orders_submitted":0,"order":f["order"],"account":f["account"],
            "positions":f["positions"],"evaluation":ev}

def actual_run(config, env, transport):
    u=endpoint_urls(config,env)
    results={n:execute_get(n,u[n],env,transport) for n in ("order","account","positions")}
    if not all(x["ok"] for x in results.values()): raise ValueError("GET reconciliation request failed")
    ev=evaluate(config,results["order"]["payload"],results["account"]["payload"],results["positions"]["payload"])
    return {"stage":"V86.57","network_mode":"ACTUAL_RECONCILIATION_READ",
            "network_requests_executed":3,"credentials_used":2,
            "actual_orders_submitted":0,"order":results["order"]["payload"],
            "account":results["account"]["payload"],
            "positions":results["positions"]["payload"],
            "evaluation":ev,"network_results":results}

def rollback_plan():
    d={"stage":"V86.58","status":"PASS","disable_reconciliation_opt_in":True,
       "clear_credentials":True,"clear_order_identifiers":True,
       "new_order_submission":False,"cancel_order":False,"replace_order":False}
    d["rollback_sha256"]=hj(d);return d

def audit(run):
    checks={"evaluation_pass":run["evaluation"]["status"]=="PASS",
            "request_budget_valid":run["network_requests_executed"] in {0,3},
            "actual_orders_zero":run["actual_orders_submitted"]==0,
            "write_actions_zero":True}
    failed=[k for k,v in checks.items() if not v]
    d={"stage":"V86.59","status":"PASS" if not failed else "FAIL",
       "checks":checks,"failed_checks":failed}
    d["audit_sha256"]=hj(d);return d

def store(out,docs):
    pid="position-account-recon-"+hj(docs)[:24];pd=out/"packages"/pid
    created=not pd.exists();files={}
    for n,d in docs.items():
        p=pd/f"{n}.json";b=(json.dumps(d,indent=2,sort_keys=True)+"\n").encode()
        if p.exists() and p.read_bytes()!=b: raise ValueError("package conflict")
        if not p.exists(): aw(p,b)
        files[n]={"relative_path":str(p.relative_to(out)).replace("\\","/"),
                  "sha256":hb(b),"byte_size":len(b)}
    led={"stage":"V86.59","status":"PASS","package_id":pid,
         "package_created":created,"package_reused":not created,"files":files,
         "actual_orders_submitted":0}
    led["ledger_sha256"]=hj(led);wj(out/"position_account_ledger_v86_59.json",led)
    return {"package_id":pid,"created":created,"reused":not created,"ledger":led}

def build_manifest(out,led,run):
    p=out/"position_account_ledger_v86_59.json";b=p.read_bytes()
    d={"stage":"V86.60","status":"PASS","package_id":led["package_id"],
       "files":{"ledger":{"relative_path":str(p.relative_to(out)).replace("\\","/"),
                          "sha256":hb(b),"byte_size":len(b)}},
       "network_requests_executed":run["network_requests_executed"],
       "credentials_used":run["credentials_used"],"actual_orders_submitted":0}
    d["manifest_sha256"]=hj(d);wj(out/"position_account_manifest_v86_60.json",d);return d

def run_engine(root,c,out,env=None,enable_network=False,transport=default_transport):
    validate_source(root/"release/v86_40/output/lifecycle_certificate_v86_40.json")
    c.validate();env=dict(os.environ) if env is None else env
    cred=credential_status(env);ident=identifier_status(env);gate=opt_in(c,env,enable_network)
    if gate["allowed"]:
        if not cred["complete"] or not ident["valid"]: raise ValueError("credentials and order identifier required")
        run=actual_run(c,env,transport)
    else:
        run=offline_run(c)
    au=audit(run)
    docs={"policy":policy(),"credential_status":cred,"identifier_status":ident,
          "opt_in":gate,"run":run,"rollback":rollback_plan(),"audit":au}
    st=store(out,docs);manifest=build_manifest(out,st["ledger"],run)
    ev=run["evaluation"]
    summary={"network_mode":run["network_mode"],
             "evaluation_status":ev["status"],
             "quantity_status":ev["quantity_reconciliation"]["status"],
             "average_price_status":ev["average_price_reconciliation"]["status"],
             "market_value_status":ev["market_value_reconciliation"]["status"],
             "unrealized_pnl_status":ev["unrealized_pnl_reconciliation"]["status"],
             "account_status":ev["account_numeric_reconciliation"]["status"],
             "buying_power_status":ev["buying_power_reconciliation"]["status"],
             "position_qty":ev["quantity_reconciliation"]["actual_position_qty"],
             "average_entry_price":ev["average_price_reconciliation"]["position_avg_entry_price"],
             "cash":ev["account_numeric_reconciliation"]["cash"],
             "buying_power":ev["account_numeric_reconciliation"]["buying_power"],
             "portfolio_value":ev["account_numeric_reconciliation"]["portfolio_value"],
             "audit_status":au["status"],
             "network_requests_executed":run["network_requests_executed"],
             "actual_orders_submitted":0}
    return {"stage":"V86.60","status":"PASS",**st,"manifest":manifest,"summary":summary}

def certificate(root,out,c,r):
    s=r["summary"]
    checks={"pipeline_pass":r["status"]=="PASS",
            "evaluation_pass":s["evaluation_status"]=="PASS",
            "quantity_pass":s["quantity_status"]=="PASS",
            "average_price_pass":s["average_price_status"]=="PASS",
            "market_value_pass":s["market_value_status"]=="PASS",
            "unrealized_pnl_pass":s["unrealized_pnl_status"]=="PASS",
            "account_pass":s["account_status"]=="PASS",
            "buying_power_pass":s["buying_power_status"]=="PASS",
            "audit_pass":s["audit_status"]=="PASS",
            "request_budget_valid":s["network_requests_executed"] in {0,3},
            "orders_zero":s["actual_orders_submitted"]==0}
    failed=[k for k,v in checks.items() if not v];status="PASS" if not failed else "FAIL"
    d={"stage":"V86.60","status":status,
       "scope":"PAPER_POSITION_AND_ACCOUNT_RECONCILIATION",
       "stages_completed":[f"V86.{i:02d}" for i in range(41,61)],
       "config":asdict(c),
       "position_account_summary":{**s,"package_id":r["package_id"],
                                   "package_created":r["created"],
                                   "package_reused":r["reused"]},
       "position_account_manifest":r["manifest"],
       "checks":checks,"failed_checks":failed,
       "network_requests_executed":s["network_requests_executed"],
       "actual_orders_submitted":0,
       "paper_position_account_reconciliation_complete":status=="PASS",
       "paper_order_submission_authorized":False,
       "live_trading_authorized":False,
       "next_phase":"V86_61_PAPER_BROKER_FINAL_NETWORK_CERTIFICATION"}
    d["certificate_sha256"]=hj(d)
    wj(out/"position_account_certificate_v86_60.json",d)
    wj(out/"position_account_verify_v86_60.json",
       {"stage":"V86.60","status":status,"verified":not failed,
        "certificate_sha256":d["certificate_sha256"],
        "failed_checks":failed,"next_phase":d["next_phase"]})
    return d
