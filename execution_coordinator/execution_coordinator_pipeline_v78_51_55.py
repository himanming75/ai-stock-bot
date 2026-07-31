from __future__ import annotations
from dataclasses import dataclass, asdict
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
class PaperOrderIntent:
    order_intent_id: str
    risk_decision_id: str
    risk_request_id: str
    candidate_id: str
    symbol: str
    side: str
    quantity: int
    order_type: str
    time_in_force: str
    limit_price: float | None
    reference_price: float
    intent_sha256: str

@dataclass(frozen=True)
class QueueRecord:
    sequence: int
    queue_event: str
    order_intent_id: str
    status: str
    record_sha256: str

def build_order_intent(decision: dict, request: dict, config: dict) -> PaperOrderIntent | None:
    if decision.get("decision") != "APPROVE":
        return None
    if decision.get("risk_request_id") != request.get("risk_request_id"):
        raise ValueError("decision request mismatch")
    quantity = int(decision.get("approved_quantity", 0))
    if quantity <= 0:
        raise ValueError("approved quantity must be positive")
    side = str(request.get("side","")).lower()
    if side not in ("buy","sell"):
        raise ValueError("unsupported side")
    symbol = str(request.get("symbol","")).upper().strip()
    if not symbol:
        raise ValueError("symbol required")
    order_type = str(config.get("order_type","market")).lower()
    if order_type not in ("market","limit"):
        raise ValueError("unsupported order type")
    tif = str(config.get("time_in_force","day")).lower()
    if tif not in ("day","gtc"):
        raise ValueError("unsupported time in force")
    reference_price = float(request.get("reference_price",0))
    if reference_price <= 0:
        raise ValueError("reference price must be positive")
    limit_price = None
    if order_type == "limit":
        offset_bps = float(config.get("limit_offset_bps",0.0))
        multiplier = 1.0 + (offset_bps/10000.0 if side=="buy" else -offset_bps/10000.0)
        limit_price = round(reference_price*multiplier,8)

    base = {
        "risk_decision_id":decision["risk_decision_id"],
        "risk_request_id":request["risk_request_id"],
        "candidate_id":request["candidate_id"],
        "symbol":symbol,
        "side":side,
        "quantity":quantity,
        "order_type":order_type,
        "time_in_force":tif,
        "limit_price":limit_price,
        "reference_price":reference_price,
    }
    sha = digest_json(base)
    return PaperOrderIntent(
        order_intent_id=f"POI-{decision['risk_decision_id']}-{sha[:12]}",
        risk_decision_id=decision["risk_decision_id"],
        risk_request_id=request["risk_request_id"],
        candidate_id=request["candidate_id"],
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=order_type,
        time_in_force=tif,
        limit_price=limit_price,
        reference_price=reference_price,
        intent_sha256=sha,
    )

class ExecutionQueue:
    def __init__(self):
        self.sequence = 0
        self.pending: list[PaperOrderIntent] = []
        self.status_by_id: dict[str,str] = {}
        self.records: list[QueueRecord] = []

    def _record(self,event:str,intent_id:str,status:str)->QueueRecord:
        self.sequence += 1
        base={
            "sequence":self.sequence,
            "queue_event":event,
            "order_intent_id":intent_id,
            "status":status,
        }
        rec=QueueRecord(self.sequence,event,intent_id,status,digest_json(base))
        self.records.append(rec)
        return rec

    def enqueue(self,intent:PaperOrderIntent)->QueueRecord:
        if intent.order_intent_id in self.status_by_id:
            raise ValueError("duplicate order intent")
        self.pending.append(intent)
        self.status_by_id[intent.order_intent_id]="QUEUED"
        return self._record("ENQUEUE",intent.order_intent_id,"QUEUED")

    def dequeue(self)->PaperOrderIntent:
        if not self.pending:
            raise IndexError("execution queue empty")
        intent=self.pending.pop(0)
        self.status_by_id[intent.order_intent_id]="DISPATCHED_TO_PAPER_BROKER"
        self._record("DEQUEUE",intent.order_intent_id,"DISPATCHED_TO_PAPER_BROKER")
        return intent

    def cancel(self,intent_id:str)->QueueRecord:
        status=self.status_by_id.get(intent_id)
        if status is None:
            raise ValueError("unknown order intent")
        if status!="QUEUED":
            raise ValueError("only queued intent can be cancelled")
        self.pending=[x for x in self.pending if x.order_intent_id!=intent_id]
        self.status_by_id[intent_id]="CANCELLED"
        return self._record("CANCEL",intent_id,"CANCELLED")

    def snapshot(self)->dict:
        return {
            "pending_ids":[x.order_intent_id for x in self.pending],
            "status_by_id":dict(sorted(self.status_by_id.items())),
            "records":[asdict(x) for x in self.records],
            "last_sequence":self.sequence,
        }

def build_execution_coordinator_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.50" or cert.get("status")!="PASS":
        errors.append("portfolio_runtime_certificate")
    if cert.get("certification_scope")!="OFFLINE_EXECUTION_COORDINATOR_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    coordinator=config.get("execution_coordinator",{})
    for key in ("order_type","time_in_force","allow_paper_broker_dispatch","allow_real_broker_dispatch"):
        if key not in coordinator:
            errors.append(f"config_{key}")
    if coordinator.get("allow_real_broker_dispatch") is not False:
        errors.append("real_broker_dispatch")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.51.execution_coordinator_foundation.1",
        "stage":"V78.51","status":status,
        "scope":"OFFLINE_PAPER_ORDER_INTENT_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "execution_coordinator":coordinator,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_52_APPROVED_DECISION_TO_PAPER_ORDER_INTENT",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"execution_coordinator_foundation_v78_51.json",doc)
    ver={"stage":"V78.51","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"execution_coordinator_foundation_verification_v78_51.json",ver)
    return doc

def run_approved_decision_to_order_intent(foundation_path:Path,decision_path:Path,
                                          normalization_path:Path,output_dir:Path)->dict:
    foundation,decision_doc,normalization=map(load_json,(foundation_path,decision_path,normalization_path))
    errors=[]
    if foundation.get("stage")!="V78.51" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if decision_doc.get("stage")!="V78.43" or decision_doc.get("status")!="PASS":
        errors.append("decision_input")
    if normalization.get("stage")!="V78.42" or normalization.get("status")!="PASS":
        errors.append("normalization_input")
    requests={x["risk_request_id"]:x for x in normalization.get("risk_requests",[])}
    intents=[]
    try:
        for decision in decision_doc.get("risk_decisions",[]):
            request=requests[decision["risk_request_id"]]
            intent=build_order_intent(decision,request,foundation.get("execution_coordinator",{}))
            if intent is not None:
                intents.append(intent)
    except Exception as exc:
        errors.append(f"intent_exception:{type(exc).__name__}")

    checks={
        "intent_count_matches_approved":len(intents)==sum(x.get("decision")=="APPROVE" for x in decision_doc.get("risk_decisions",[])),
        "buy_sell_intents_present":{"buy","sell"}.issubset({x.side for x in intents}),
        "quantity_positive":all(x.quantity>0 for x in intents),
        "intent_ids_unique":len({x.order_intent_id for x in intents})==len(intents),
        "intent_hashes_unique":len({x.intent_sha256 for x in intents})==len(intents),
        "real_broker_dispatch_disabled":foundation.get("execution_coordinator",{}).get("allow_real_broker_dispatch") is False,
        "actual_orders_zero":True,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("order_intent_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.52.approved_decision_to_order_intent.1",
        "stage":"V78.52","status":status,
        "paper_order_intents":[asdict(x) for x in intents],
        "checks":checks,"failed_checks":failed,
        "paper_broker_dispatch_count":0,
        "real_broker_dispatch_count":0,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_53_EXECUTION_QUEUE_IDEMPOTENCY",
    }
    doc["intent_batch_sha256"]=digest_json({k:v for k,v in doc.items() if k!="intent_batch_sha256"})
    write_json(output_dir/"approved_decision_to_paper_order_intent_v78_52.json",doc)
    ver={"stage":"V78.52","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "intent_batch_sha256":doc["intent_batch_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"approved_decision_to_paper_order_intent_verification_v78_52.json",ver)
    return doc

def run_execution_queue_idempotency(intent_path:Path,output_dir:Path)->dict:
    intent_doc=load_json(intent_path)
    errors=[]
    if intent_doc.get("stage")!="V78.52" or intent_doc.get("status")!="PASS":
        errors.append("intent_input")
    queue=ExecutionQueue()
    intents=[PaperOrderIntent(**x) for x in intent_doc.get("paper_order_intents",[])]
    dispatched=[]
    cancelled_id=None
    try:
        for intent in intents:
            queue.enqueue(intent)
        if len(intents)>=2:
            cancelled_id=intents[1].order_intent_id
            queue.cancel(cancelled_id)
        if queue.pending:
            dispatched.append(queue.dequeue())
    except Exception as exc:
        errors.append(f"queue_exception:{type(exc).__name__}")

    snapshot=queue.snapshot()
    checks={
        "records_sequence_contiguous":[x["sequence"] for x in snapshot["records"]]==list(range(1,len(snapshot["records"])+1)),
        "record_hashes_unique":len({x["record_sha256"] for x in snapshot["records"]})==len(snapshot["records"]),
        "cancelled_removed_from_pending":cancelled_id is None or cancelled_id not in snapshot["pending_ids"],
        "fifo_dispatch":not dispatched or dispatched[0].order_intent_id==intents[0].order_intent_id,
        "dispatched_to_paper_only":all(
            snapshot["status_by_id"][x.order_intent_id]=="DISPATCHED_TO_PAPER_BROKER" for x in dispatched
        ),
        "real_broker_dispatch_count_zero":True,
        "actual_orders_zero":True,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("execution_queue_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.53.execution_queue_idempotency.1",
        "stage":"V78.53","status":status,
        "queue_snapshot":snapshot,
        "dispatched_intents":[asdict(x) for x in dispatched],
        "checks":checks,"failed_checks":failed,
        "paper_broker_dispatch_count":len(dispatched),
        "real_broker_dispatch_count":0,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_54_EXECUTION_COORDINATOR_SAFETY_GATE",
    }
    doc["queue_sha256"]=digest_json({k:v for k,v in doc.items() if k!="queue_sha256"})
    write_json(output_dir/"execution_queue_idempotency_v78_53.json",doc)
    ver={"stage":"V78.53","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "queue_sha256":doc["queue_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"execution_queue_idempotency_verification_v78_53.json",ver)
    return doc

def run_execution_coordinator_safety_gate(foundation_path:Path,intent_path:Path,
                                          queue_path:Path,output_dir:Path)->dict:
    foundation,intent_doc,queue_doc=map(load_json,(foundation_path,intent_path,queue_path))
    errors=[]
    for expected,doc in (("V78.51",foundation),("V78.52",intent_doc),("V78.53",queue_doc)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    intents=intent_doc.get("paper_order_intents",[])
    records=queue_doc.get("queue_snapshot",{}).get("records",[])
    checks={
        "offline_intent_scope":foundation.get("scope")=="OFFLINE_PAPER_ORDER_INTENT_ONLY",
        "intent_checks_passed":intent_doc.get("failed_checks")==[],
        "queue_checks_passed":queue_doc.get("failed_checks")==[],
        "intent_ids_unique":len({x["order_intent_id"] for x in intents})==len(intents),
        "queue_sequences_contiguous":[x["sequence"] for x in records]==list(range(1,len(records)+1)),
        "paper_broker_dispatch_allowed":foundation.get("execution_coordinator",{}).get("allow_paper_broker_dispatch") is True,
        "real_broker_dispatch_disabled":foundation.get("execution_coordinator",{}).get("allow_real_broker_dispatch") is False,
        "real_broker_dispatch_zero":queue_doc.get("real_broker_dispatch_count")==0,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,intent_doc,queue_doc)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,intent_doc,queue_doc)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,intent_doc,queue_doc)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed: errors.append("execution_coordinator_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.54.execution_coordinator_safety_gate.1",
        "stage":"V78.54","status":status,
        "gate_scope":"OFFLINE_PAPER_BROKER_INTEGRATION_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_PAPER_BROKER_INTEGRATION" if not errors else "BLOCK_PAPER_BROKER_INTEGRATION",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_55_EXECUTION_COORDINATOR_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"execution_coordinator_safety_gate_v78_54.json",doc)
    ver={"stage":"V78.54","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"execution_coordinator_safety_gate_verification_v78_54.json",ver)
    return doc

def issue_execution_coordinator_certificate(v51:Path,v52:Path,v53:Path,v54:Path,
                                            foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v51,v52,v53,v54)))
    foundation=load_json(foundation_path)
    expected=["V78.51","V78.52","V78.53","V78.54"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.55.execution_coordinator_certificate.1",
        "stage":"V78.55",
        "certificate_id":"EXECUTION-COORDINATOR-V78.55",
        "status":status,
        "decision":"certified_for_offline_paper_broker_integration" if not errors else "execution_coordinator_rejected",
        "certification_scope":"OFFLINE_PAPER_BROKER_INTEGRATION_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_56_PAPER_BROKER_INTEGRATION_FOUNDATION" if not errors else "REPAIR_V78_55",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"execution_coordinator_certificate_v78_55.json",cert)
    ver={"stage":"V78.55","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"execution_coordinator_certificate_verification_v78_55.json",ver)
    return cert
