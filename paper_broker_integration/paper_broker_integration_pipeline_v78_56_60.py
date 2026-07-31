from __future__ import annotations
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Any
import hashlib, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
        "live_deployment_approved":False,
        "real_credentials_allowed":False,
    }

@dataclass(frozen=True)
class PaperBrokerOrder:
    broker_order_id: str
    order_intent_id: str
    symbol: str
    side: str
    quantity: int
    remaining_quantity: int
    order_type: str
    time_in_force: str
    limit_price: float | None
    reference_price: float
    status: str
    order_sha256: str

@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    broker_order_id: str
    order_intent_id: str
    symbol: str
    side: str
    fill_quantity: int
    fill_price: float
    gross_notional: float
    commission: float
    slippage_cost: float
    remaining_quantity: int
    fill_status: str
    fill_sha256: str

class OfflinePaperBroker:
    def __init__(self, commission_per_order: float, slippage_bps: float, max_fill_quantity: int):
        if commission_per_order < 0 or slippage_bps < 0 or max_fill_quantity <= 0:
            raise ValueError("invalid paper broker configuration")
        self.commission_per_order=float(commission_per_order)
        self.slippage_bps=float(slippage_bps)
        self.max_fill_quantity=int(max_fill_quantity)
        self.orders:dict[str,PaperBrokerOrder]={}
        self.intent_ids:set[str]=set()
        self.fills:list[PaperFill]=[]
        self.network_allowed=False
        self.broker_connected=False
        self.actual_orders_submitted=0

    def submit(self, intent:dict)->PaperBrokerOrder:
        intent_id=str(intent.get("order_intent_id",""))
        if not intent_id:
            raise ValueError("order_intent_id required")
        if intent_id in self.intent_ids:
            raise ValueError("duplicate order intent submission")
        quantity=int(intent.get("quantity",0))
        if quantity<=0:
            raise ValueError("quantity must be positive")
        side=str(intent.get("side","")).lower()
        if side not in ("buy","sell"):
            raise ValueError("unsupported side")
        order_type=str(intent.get("order_type","market")).lower()
        if order_type not in ("market","limit"):
            raise ValueError("unsupported order type")
        reference_price=float(intent.get("reference_price",0))
        if reference_price<=0:
            raise ValueError("reference price must be positive")
        limit_price=intent.get("limit_price")
        if order_type=="limit" and (limit_price is None or float(limit_price)<=0):
            raise ValueError("limit price required")
        base={
            "order_intent_id":intent_id,
            "symbol":str(intent.get("symbol","")).upper(),
            "side":side,
            "quantity":quantity,
            "remaining_quantity":quantity,
            "order_type":order_type,
            "time_in_force":str(intent.get("time_in_force","day")).lower(),
            "limit_price":None if limit_price is None else float(limit_price),
            "reference_price":reference_price,
            "status":"ACCEPTED",
        }
        sha=digest_json(base)
        order=PaperBrokerOrder(
            broker_order_id=f"PBO-{intent_id}-{sha[:12]}",
            order_intent_id=intent_id,
            symbol=base["symbol"],
            side=side,
            quantity=quantity,
            remaining_quantity=quantity,
            order_type=order_type,
            time_in_force=base["time_in_force"],
            limit_price=base["limit_price"],
            reference_price=reference_price,
            status="ACCEPTED",
            order_sha256=sha,
        )
        self.orders[order.broker_order_id]=order
        self.intent_ids.add(intent_id)
        return order

    def _fill_price(self, order:PaperBrokerOrder)->float:
        ref=order.reference_price
        slip=ref*(self.slippage_bps/10000.0)
        price=ref+slip if order.side=="buy" else ref-slip
        if order.order_type=="limit":
            if order.side=="buy":
                price=min(price,float(order.limit_price))
            else:
                price=max(price,float(order.limit_price))
        return round(price,8)

    def fill_next(self, broker_order_id:str)->PaperFill:
        if broker_order_id not in self.orders:
            raise ValueError("unknown broker order")
        order=self.orders[broker_order_id]
        if order.remaining_quantity<=0 or order.status=="FILLED":
            raise ValueError("order already filled")
        fill_qty=min(order.remaining_quantity,self.max_fill_quantity)
        fill_price=self._fill_price(order)
        gross=round(fill_qty*fill_price,8)
        commission=round(self.commission_per_order,8)
        slippage_cost=round(abs(fill_price-order.reference_price)*fill_qty,8)
        remaining=order.remaining_quantity-fill_qty
        status="FILLED" if remaining==0 else "PARTIALLY_FILLED"
        base={
            "broker_order_id":order.broker_order_id,
            "order_intent_id":order.order_intent_id,
            "symbol":order.symbol,
            "side":order.side,
            "fill_quantity":fill_qty,
            "fill_price":fill_price,
            "gross_notional":gross,
            "commission":commission,
            "slippage_cost":slippage_cost,
            "remaining_quantity":remaining,
            "fill_status":status,
        }
        sha=digest_json(base)
        fill=PaperFill(
            fill_id=f"PF-{order.broker_order_id}-{len(self.fills)+1}-{sha[:10]}",
            broker_order_id=order.broker_order_id,
            order_intent_id=order.order_intent_id,
            symbol=order.symbol,
            side=order.side,
            fill_quantity=fill_qty,
            fill_price=fill_price,
            gross_notional=gross,
            commission=commission,
            slippage_cost=slippage_cost,
            remaining_quantity=remaining,
            fill_status=status,
            fill_sha256=sha,
        )
        self.fills.append(fill)
        self.orders[broker_order_id]=replace(order,remaining_quantity=remaining,status=status)
        return fill

    def cancel(self, broker_order_id:str)->PaperBrokerOrder:
        if broker_order_id not in self.orders:
            raise ValueError("unknown broker order")
        order=self.orders[broker_order_id]
        if order.status=="FILLED":
            raise ValueError("filled order cannot be cancelled")
        if order.status=="CANCELLED":
            raise ValueError("order already cancelled")
        cancelled=replace(order,status="CANCELLED")
        self.orders[broker_order_id]=cancelled
        return cancelled

    def health(self)->dict:
        return {
            "status":"HEALTHY",
            "mode":"offline_paper_broker",
            "order_count":len(self.orders),
            "fill_count":len(self.fills),
            "network_allowed":False,
            "broker_connected":False,
            "actual_orders_submitted":0,
        }

def build_paper_broker_integration_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.55" or cert.get("status")!="PASS":
        errors.append("execution_coordinator_certificate")
    if cert.get("certification_scope")!="OFFLINE_PAPER_BROKER_INTEGRATION_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    broker=config.get("paper_broker_integration",{})
    for key in ("commission_per_order","slippage_bps","max_fill_quantity","allow_real_broker"):
        if key not in broker:
            errors.append(f"config_{key}")
    if broker.get("allow_real_broker") is not False:
        errors.append("real_broker_allowed")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.56.paper_broker_foundation.1",
        "stage":"V78.56","status":status,
        "scope":"OFFLINE_PAPER_BROKER_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "paper_broker_integration":broker,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_57_PAPER_ORDER_SUBMISSION_PIPELINE",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"paper_broker_integration_foundation_v78_56.json",doc)
    ver={"stage":"V78.56","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_broker_integration_foundation_verification_v78_56.json",ver)
    return doc

def run_paper_order_submission_pipeline(foundation_path:Path,intent_path:Path,output_dir:Path)->dict:
    foundation,intent_doc=map(load_json,(foundation_path,intent_path))
    errors=[]
    if foundation.get("stage")!="V78.56" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if intent_doc.get("stage")!="V78.52" or intent_doc.get("status")!="PASS":
        errors.append("intent_input")
    cfg=foundation.get("paper_broker_integration",{})
    broker=OfflinePaperBroker(
        float(cfg.get("commission_per_order",0)),
        float(cfg.get("slippage_bps",0)),
        int(cfg.get("max_fill_quantity",1)),
    )
    orders=[]
    try:
        for intent in intent_doc.get("paper_order_intents",[]):
            orders.append(broker.submit(intent))
    except Exception as exc:
        errors.append(f"submission_exception:{type(exc).__name__}")
    checks={
        "order_count_matches_intents":len(orders)==len(intent_doc.get("paper_order_intents",[])),
        "order_ids_unique":len({x.broker_order_id for x in orders})==len(orders),
        "intent_ids_unique":len({x.order_intent_id for x in orders})==len(orders),
        "all_orders_accepted":all(x.status=="ACCEPTED" for x in orders),
        "real_broker_disabled":foundation.get("paper_broker_integration",{}).get("allow_real_broker") is False,
        "actual_orders_zero":broker.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("submission_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.57.paper_order_submission.1",
        "stage":"V78.57","status":status,
        "paper_broker_orders":[asdict(x) for x in orders],
        "checks":checks,"failed_checks":failed,
        "paper_order_submission_count":len(orders),
        "real_order_submission_count":0,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_58_PAPER_FILL_SIMULATION_ENGINE",
    }
    doc["submission_sha256"]=digest_json({k:v for k,v in doc.items() if k!="submission_sha256"})
    write_json(output_dir/"paper_order_submission_pipeline_v78_57.json",doc)
    ver={"stage":"V78.57","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "submission_sha256":doc["submission_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_order_submission_pipeline_verification_v78_57.json",ver)
    return doc

def run_paper_fill_simulation(foundation_path:Path,submission_path:Path,output_dir:Path)->dict:
    foundation,submission=map(load_json,(foundation_path,submission_path))
    errors=[]
    if foundation.get("stage")!="V78.56" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if submission.get("stage")!="V78.57" or submission.get("status")!="PASS":
        errors.append("submission_input")
    cfg=foundation.get("paper_broker_integration",{})
    broker=OfflinePaperBroker(
        float(cfg.get("commission_per_order",0)),
        float(cfg.get("slippage_bps",0)),
        int(cfg.get("max_fill_quantity",1)),
    )
    fills=[]
    try:
        for raw in submission.get("paper_broker_orders",[]):
            intent={
                "order_intent_id":raw["order_intent_id"],
                "symbol":raw["symbol"],
                "side":raw["side"],
                "quantity":raw["quantity"],
                "order_type":raw["order_type"],
                "time_in_force":raw["time_in_force"],
                "limit_price":raw["limit_price"],
                "reference_price":raw["reference_price"],
            }
            order=broker.submit(intent)
            while broker.orders[order.broker_order_id].remaining_quantity>0:
                fills.append(broker.fill_next(order.broker_order_id))
    except Exception as exc:
        errors.append(f"fill_exception:{type(exc).__name__}")

    order_qty=sum(x["quantity"] for x in submission.get("paper_broker_orders",[]))
    fill_qty=sum(x.fill_quantity for x in fills)
    checks={
        "filled_quantity_matches_orders":fill_qty==order_qty,
        "all_orders_filled":all(x.status=="FILLED" for x in broker.orders.values()),
        "partial_fill_present":any(x.fill_status=="PARTIALLY_FILLED" for x in fills),
        "final_fill_present":any(x.fill_status=="FILLED" for x in fills),
        "fill_ids_unique":len({x.fill_id for x in fills})==len(fills),
        "fill_hashes_unique":len({x.fill_sha256 for x in fills})==len(fills),
        "commission_non_negative":all(x.commission>=0 for x in fills),
        "slippage_non_negative":all(x.slippage_cost>=0 for x in fills),
        "actual_orders_zero":broker.actual_orders_submitted==0,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("fill_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.58.paper_fill_simulation.1",
        "stage":"V78.58","status":status,
        "paper_fills":[asdict(x) for x in fills],
        "final_orders":[asdict(x) for x in broker.orders.values()],
        "checks":checks,"failed_checks":failed,
        "paper_fill_count":len(fills),
        "paper_filled_quantity":fill_qty,
        "real_fill_count":0,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_59_PAPER_BROKER_INTEGRATION_SAFETY_GATE",
    }
    doc["fill_batch_sha256"]=digest_json({k:v for k,v in doc.items() if k!="fill_batch_sha256"})
    write_json(output_dir/"paper_fill_simulation_engine_v78_58.json",doc)
    ver={"stage":"V78.58","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "fill_batch_sha256":doc["fill_batch_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_fill_simulation_engine_verification_v78_58.json",ver)
    return doc

def run_paper_broker_integration_safety_gate(foundation_path:Path,submission_path:Path,
                                             fill_path:Path,output_dir:Path)->dict:
    foundation,submission,fill=map(load_json,(foundation_path,submission_path,fill_path))
    errors=[]
    for expected,doc in (("V78.56",foundation),("V78.57",submission),("V78.58",fill)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    fills=fill.get("paper_fills",[])
    checks={
        "offline_paper_broker_scope":foundation.get("scope")=="OFFLINE_PAPER_BROKER_ONLY",
        "submission_checks_passed":submission.get("failed_checks")==[],
        "fill_checks_passed":fill.get("failed_checks")==[],
        "paper_orders_present":submission.get("paper_order_submission_count",0)>0,
        "paper_fills_present":fill.get("paper_fill_count",0)>0,
        "real_orders_zero":submission.get("real_order_submission_count")==0,
        "real_fills_zero":fill.get("real_fill_count")==0,
        "fill_ids_unique":len({x["fill_id"] for x in fills})==len(fills),
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,submission,fill)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,submission,fill)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,submission,fill)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("paper_broker_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.59.paper_broker_safety_gate.1",
        "stage":"V78.59","status":status,
        "gate_scope":"OFFLINE_FILL_PORTFOLIO_BRIDGE_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_FILL_PORTFOLIO_BRIDGE" if not errors else "BLOCK_FILL_PORTFOLIO_BRIDGE",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_60_PAPER_BROKER_INTEGRATION_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"paper_broker_integration_safety_gate_v78_59.json",doc)
    ver={"stage":"V78.59","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_broker_integration_safety_gate_verification_v78_59.json",ver)
    return doc

def issue_paper_broker_integration_certificate(v56:Path,v57:Path,v58:Path,v59:Path,
                                               foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v56,v57,v58,v59)))
    foundation=load_json(foundation_path)
    expected=["V78.56","V78.57","V78.58","V78.59"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.60.paper_broker_certificate.1",
        "stage":"V78.60",
        "certificate_id":"PAPER-BROKER-INTEGRATION-V78.60",
        "status":status,
        "decision":"certified_for_offline_fill_portfolio_bridge" if not errors else "paper_broker_integration_rejected",
        "certification_scope":"OFFLINE_FILL_PORTFOLIO_BRIDGE_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_61_FILL_PORTFOLIO_BRIDGE_FOUNDATION" if not errors else "REPAIR_V78_60",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"paper_broker_integration_certificate_v78_60.json",cert)
    ver={"stage":"V78.60","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"paper_broker_integration_certificate_verification_v78_60.json",ver)
    return cert
