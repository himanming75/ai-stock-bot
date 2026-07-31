from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
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
class BusEvent:
    event_id: str
    sequence: int
    topic: str
    event_type: str
    payload: dict
    event_sha256: str

@dataclass(frozen=True)
class DeliveryRecord:
    delivery_id: str
    event_id: str
    subscriber_id: str
    attempt: int
    status: str
    error: str | None = None

class SubscriberRegistry:
    def __init__(self):
        self._subscribers: dict[str, tuple[set[str], Callable[[BusEvent], None]]] = {}

    def register(self, subscriber_id: str, topics: list[str], handler: Callable[[BusEvent], None]) -> None:
        sid = subscriber_id.strip()
        if not sid:
            raise ValueError("subscriber_id required")
        if sid in self._subscribers:
            raise ValueError("subscriber already registered")
        normalized = {x.strip() for x in topics if x.strip()}
        if not normalized:
            raise ValueError("at least one topic required")
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._subscribers[sid] = (normalized, handler)

    def matching(self, topic: str) -> list[tuple[str, Callable[[BusEvent], None]]]:
        return [
            (sid, handler)
            for sid, (topics, handler) in sorted(self._subscribers.items())
            if topic in topics or "*" in topics
        ]

    def subscriber_ids(self) -> list[str]:
        return sorted(self._subscribers)

class OfflineEventBus:
    def __init__(self, max_retries: int = 2):
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.registry = SubscriberRegistry()
        self.max_retries = int(max_retries)
        self._sequence = 0
        self._published_event_ids: set[str] = set()
        self._delivered_keys: set[tuple[str, str]] = set()
        self.delivery_records: list[DeliveryRecord] = []
        self.dead_letter_queue: list[dict] = []
        self.network_allowed = False
        self.broker_connected = False
        self.actual_orders_submitted = 0

    def make_event(self, topic: str, event_type: str, payload: dict) -> BusEvent:
        topic = topic.strip()
        event_type = event_type.strip()
        if not topic:
            raise ValueError("topic required")
        if not event_type:
            raise ValueError("event_type required")
        self._sequence += 1
        base = {
            "sequence":self._sequence,
            "topic":topic,
            "event_type":event_type,
            "payload":payload,
        }
        sha = digest_json(base)
        return BusEvent(
            event_id=f"BUS-EVT-{self._sequence:08d}-{sha[:12]}",
            sequence=self._sequence,
            topic=topic,
            event_type=event_type,
            payload=dict(payload),
            event_sha256=sha,
        )

    def publish(self, event: BusEvent) -> list[DeliveryRecord]:
        if event.event_id in self._published_event_ids:
            raise ValueError("duplicate event publish")
        expected = digest_json({
            "sequence":event.sequence,
            "topic":event.topic,
            "event_type":event.event_type,
            "payload":event.payload,
        })
        if expected != event.event_sha256:
            raise ValueError("event hash mismatch")
        self._published_event_ids.add(event.event_id)

        records: list[DeliveryRecord] = []
        for subscriber_id, handler in self.registry.matching(event.topic):
            key = (event.event_id, subscriber_id)
            if key in self._delivered_keys:
                continue

            delivered = False
            last_error = None
            for attempt in range(1, self.max_retries + 2):
                delivery_id = f"{event.event_id}:{subscriber_id}:{attempt}"
                try:
                    handler(event)
                    record = DeliveryRecord(
                        delivery_id=delivery_id,
                        event_id=event.event_id,
                        subscriber_id=subscriber_id,
                        attempt=attempt,
                        status="DELIVERED",
                    )
                    self.delivery_records.append(record)
                    records.append(record)
                    self._delivered_keys.add(key)
                    delivered = True
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}:{exc}"
                    record = DeliveryRecord(
                        delivery_id=delivery_id,
                        event_id=event.event_id,
                        subscriber_id=subscriber_id,
                        attempt=attempt,
                        status="RETRY" if attempt <= self.max_retries else "FAILED",
                        error=last_error,
                    )
                    self.delivery_records.append(record)
                    records.append(record)

            if not delivered:
                self.dead_letter_queue.append({
                    "event":asdict(event),
                    "subscriber_id":subscriber_id,
                    "attempts":self.max_retries + 1,
                    "last_error":last_error,
                    "status":"DEAD_LETTER",
                })
        return records

    def replay_dead_letter(self, index: int) -> DeliveryRecord:
        if index < 0 or index >= len(self.dead_letter_queue):
            raise IndexError("dead letter index")
        item = self.dead_letter_queue[index]
        event = BusEvent(**item["event"])
        subscriber_id = item["subscriber_id"]
        matches = {sid:handler for sid,handler in self.registry.matching(event.topic)}
        if subscriber_id not in matches:
            raise ValueError("subscriber no longer registered")
        key = (event.event_id, subscriber_id)
        if key in self._delivered_keys:
            raise ValueError("already delivered")
        try:
            matches[subscriber_id](event)
        except Exception as exc:
            raise RuntimeError(f"dead letter replay failed:{exc}") from exc
        record = DeliveryRecord(
            delivery_id=f"{event.event_id}:{subscriber_id}:DLQ",
            event_id=event.event_id,
            subscriber_id=subscriber_id,
            attempt=item["attempts"] + 1,
            status="DELIVERED_FROM_DLQ",
        )
        self.delivery_records.append(record)
        self._delivered_keys.add(key)
        item["status"] = "RECOVERED"
        return record

    def health(self) -> dict:
        return {
            "status":"HEALTHY",
            "mode":"offline_event_bus",
            "network_allowed":False,
            "broker_connected":False,
            "actual_orders_submitted":0,
            "subscriber_count":len(self.registry.subscriber_ids()),
            "delivery_record_count":len(self.delivery_records),
            "dead_letter_count":sum(x["status"]=="DEAD_LETTER" for x in self.dead_letter_queue),
        }

def build_event_bus_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json,(certificate_path,config_path))
    errors = []
    if cert.get("stage")!="V78.10" or cert.get("status")!="PASS":
        errors.append("paper_event_certificate")
    if cert.get("certification_scope")!="OFFLINE_EVENT_BUS_FOUNDATION_ONLY":
        errors.append("certificate_scope")
    bus = config.get("event_bus",{})
    for key in ("mode","max_retries","topics","delivery_policy"):
        if key not in bus:
            errors.append(f"config_{key}")
    if bus.get("mode")!="offline":
        errors.append("mode")
    if bus.get("delivery_policy")!="at_least_once_with_idempotency":
        errors.append("delivery_policy")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.11.event_bus_foundation.1",
        "stage":"V78.11","status":status,
        "scope":"OFFLINE_EVENT_BUS_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "event_bus":bus,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_12_SUBSCRIBER_REGISTRY",
    }
    doc["foundation_sha256"] = digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"event_bus_foundation_v78_11.json",doc)
    ver = {
        "stage":"V78.11","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "foundation_sha256":doc["foundation_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"event_bus_foundation_verification_v78_11.json",ver)
    return doc

def build_subscriber_registry(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors = []
    if foundation.get("stage")!="V78.11" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    received: dict[str,list[str]] = {"portfolio":[],"risk":[],"audit":[]}
    registry = SubscriberRegistry()
    registry.register("portfolio",["order.events","fill.events"],lambda e:received["portfolio"].append(e.event_id))
    registry.register("risk",["order.events"],lambda e:received["risk"].append(e.event_id))
    registry.register("audit",["*"],lambda e:received["audit"].append(e.event_id))
    checks = {
        "subscriber_count":len(registry.subscriber_ids())==3,
        "subscriber_ids_sorted":registry.subscriber_ids()==["audit","portfolio","risk"],
        "order_topic_matches_three":len(registry.matching("order.events"))==3,
        "fill_topic_matches_two":len(registry.matching("fill.events"))==2,
        "unknown_topic_matches_wildcard":len(registry.matching("system.events"))==1,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("subscriber_registry_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.12.subscriber_registry.1",
        "stage":"V78.12","status":status,
        "subscriber_ids":registry.subscriber_ids(),
        "topic_map":{
            "order.events":[x[0] for x in registry.matching("order.events")],
            "fill.events":[x[0] for x in registry.matching("fill.events")],
            "system.events":[x[0] for x in registry.matching("system.events")],
        },
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_13_EVENT_DISPATCH_RETRY_DLQ",
    }
    doc["registry_sha256"] = digest_json({k:v for k,v in doc.items() if k!="registry_sha256"})
    write_json(output_dir/"subscriber_registry_v78_12.json",doc)
    ver = {
        "stage":"V78.12","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "registry_sha256":doc["registry_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"subscriber_registry_verification_v78_12.json",ver)
    return doc

def run_event_dispatch_retry_dlq(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors = []
    if foundation.get("stage")!="V78.11" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    bus = OfflineEventBus(max_retries=int(foundation.get("event_bus",{}).get("max_retries",2)))
    received = {"portfolio":[],"audit":[]}
    flaky_attempts = {"count":0}
    permanent_attempts = {"count":0}

    def portfolio_handler(event: BusEvent) -> None:
        received["portfolio"].append(event.event_id)

    def audit_handler(event: BusEvent) -> None:
        received["audit"].append(event.event_id)

    def flaky_handler(event: BusEvent) -> None:
        flaky_attempts["count"] += 1
        if flaky_attempts["count"] < 2:
            raise RuntimeError("transient")
        received.setdefault("flaky",[]).append(event.event_id)

    def permanent_handler(event: BusEvent) -> None:
        permanent_attempts["count"] += 1
        raise RuntimeError("permanent")

    bus.registry.register("portfolio",["order.events","fill.events"],portfolio_handler)
    bus.registry.register("audit",["*"],audit_handler)
    bus.registry.register("flaky",["order.events"],flaky_handler)
    bus.registry.register("permanent",["system.events"],permanent_handler)

    e1 = bus.make_event("order.events","ORDER_ACCEPTED",{"order_id":"ORD-1"})
    r1 = bus.publish(e1)
    e2 = bus.make_event("fill.events","ORDER_FILLED",{"order_id":"ORD-1","price":100.0})
    r2 = bus.publish(e2)
    e3 = bus.make_event("system.events","BROKER_DISCONNECTED",{"reason":"offline_test"})
    r3 = bus.publish(e3)

    checks = {
        "sequence_ordered":[e1.sequence,e2.sequence,e3.sequence]==[1,2,3],
        "portfolio_received_two":received["portfolio"]==[e1.event_id,e2.event_id],
        "audit_received_three":received["audit"]==[e1.event_id,e2.event_id,e3.event_id],
        "flaky_retried_then_delivered":flaky_attempts["count"]==2 and received["flaky"]==[e1.event_id],
        "permanent_failed_all_attempts":permanent_attempts["count"]==bus.max_retries+1,
        "dead_letter_created":len(bus.dead_letter_queue)==1,
        "delivery_ids_unique":len({x.delivery_id for x in bus.delivery_records})==len(bus.delivery_records),
        "network_disabled":bus.health()["network_allowed"] is False,
        "actual_orders_zero":bus.health()["actual_orders_submitted"]==0,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("dispatch_retry_dlq_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.13.event_dispatch_retry_dlq.1",
        "stage":"V78.13","status":status,
        "events":[asdict(e1),asdict(e2),asdict(e3)],
        "delivery_records":[asdict(x) for x in bus.delivery_records],
        "dead_letter_queue":bus.dead_letter_queue,
        "received":received,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_14_EVENT_BUS_SAFETY_GATE",
    }
    doc["dispatch_sha256"] = digest_json({k:v for k,v in doc.items() if k!="dispatch_sha256"})
    write_json(output_dir/"event_dispatch_retry_dlq_v78_13.json",doc)
    ver = {
        "stage":"V78.13","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "dispatch_sha256":doc["dispatch_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"event_dispatch_retry_dlq_verification_v78_13.json",ver)
    return doc

def run_event_bus_safety_gate(foundation_path: Path, registry_path: Path, dispatch_path: Path, output_dir: Path) -> dict:
    foundation, registry, dispatch = map(load_json,(foundation_path,registry_path,dispatch_path))
    errors = []
    for expected,doc in (("V78.11",foundation),("V78.12",registry),("V78.13",dispatch)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    events = dispatch.get("events",[])
    records = dispatch.get("delivery_records",[])
    dlq = dispatch.get("dead_letter_queue",[])
    checks = {
        "offline_mode":foundation.get("event_bus",{}).get("mode")=="offline",
        "delivery_policy":foundation.get("event_bus",{}).get("delivery_policy")=="at_least_once_with_idempotency",
        "event_sequences_contiguous":[x["sequence"] for x in events]==list(range(1,len(events)+1)),
        "event_ids_unique":len({x["event_id"] for x in events})==len(events),
        "delivery_ids_unique":len({x["delivery_id"] for x in records})==len(records),
        "subscriber_registry_passed":registry.get("failed_checks")==[],
        "dispatch_checks_passed":dispatch.get("failed_checks")==[],
        "dlq_records_complete":all(
            x.get("status") in ("DEAD_LETTER","RECOVERED")
            and x.get("subscriber_id")
            and x.get("event",{}).get("event_id")
            for x in dlq
        ),
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,registry,dispatch)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,registry,dispatch)),
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("event_bus_safety_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.14.event_bus_safety_gate.1",
        "stage":"V78.14","status":status,
        "gate_scope":"OFFLINE_SESSION_MANAGER_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_SESSION_MANAGER" if not errors else "BLOCK_SESSION_MANAGER",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_15_EVENT_BUS_CERTIFICATE",
    }
    doc["safety_gate_sha256"] = digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"event_bus_safety_gate_v78_14.json",doc)
    ver = {
        "stage":"V78.14","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"event_bus_safety_gate_verification_v78_14.json",ver)
    return doc

def issue_event_bus_certificate(v11: Path,v12: Path,v13: Path,v14: Path,foundation_path: Path,output_dir: Path) -> dict:
    docs = list(map(load_json,(v11,v12,v13,v14)))
    foundation = load_json(foundation_path)
    expected = ["V78.11","V78.12","V78.13","V78.14"]
    errors = []
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v78.15.event_bus_certificate.1",
        "stage":"V78.15",
        "certificate_id":"OFFLINE-EVENT-BUS-V78.15",
        "status":status,
        "decision":"certified_for_offline_session_manager" if not errors else "event_bus_rejected",
        "certification_scope":"OFFLINE_SESSION_MANAGER_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_16_PAPER_SESSION_MANAGER_FOUNDATION" if not errors else "REPAIR_V78_15",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"event_bus_certificate_v78_15.json",cert)
    ver = {
        "stage":"V78.15","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"event_bus_certificate_verification_v78_15.json",ver)
    return cert
