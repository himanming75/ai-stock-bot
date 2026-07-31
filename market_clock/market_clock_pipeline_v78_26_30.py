from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
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
class TradingSession:
    trading_date: str
    timezone: str
    premarket_open: str
    regular_open: str
    regular_close: str
    aftermarket_close: str
    is_holiday: bool
    is_early_close: bool
    session_type: str

@dataclass(frozen=True)
class MarketClockEvent:
    sequence: int
    event_type: str
    previous_state: str
    new_state: str
    timestamp: str
    event_sha256: str

class DeterministicTradingCalendar:
    def __init__(self, timezone: str, holidays: list[str], early_closes: dict[str,str]):
        self.timezone = timezone
        self.holidays = set(holidays)
        self.early_closes = dict(early_closes)

    def is_trading_day(self, d: date) -> bool:
        return d.weekday() < 5 and d.isoformat() not in self.holidays

    def next_trading_day(self, d: date) -> date:
        current = d + timedelta(days=1)
        while not self.is_trading_day(current):
            current += timedelta(days=1)
        return current

    def session_for(self, d: date) -> TradingSession:
        day = d.isoformat()
        if not self.is_trading_day(d):
            return TradingSession(
                trading_date=day,
                timezone=self.timezone,
                premarket_open="",
                regular_open="",
                regular_close="",
                aftermarket_close="",
                is_holiday=day in self.holidays,
                is_early_close=False,
                session_type="CLOSED",
            )
        regular_close = self.early_closes.get(day,"16:00")
        return TradingSession(
            trading_date=day,
            timezone=self.timezone,
            premarket_open="04:00",
            regular_open="09:30",
            regular_close=regular_close,
            aftermarket_close="20:00",
            is_holiday=False,
            is_early_close=day in self.early_closes,
            session_type="TRADING_DAY",
        )

class DeterministicMarketClock:
    ORDER = ["CLOSED","PREMARKET","REGULAR","AFTERMARKET","CLOSED"]

    def __init__(self, calendar: DeterministicTradingCalendar):
        self.calendar = calendar
        self.sequence = 0
        self.state = "CLOSED"
        self.events: list[MarketClockEvent] = []

    def state_at(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            raise ValueError("timezone-aware datetime required")
        local = dt.astimezone(ZoneInfo(self.calendar.timezone))
        session = self.calendar.session_for(local.date())
        if session.session_type == "CLOSED":
            return "CLOSED"
        t = local.time().replace(tzinfo=None)
        pre = time.fromisoformat(session.premarket_open)
        reg_open = time.fromisoformat(session.regular_open)
        reg_close = time.fromisoformat(session.regular_close)
        after = time.fromisoformat(session.aftermarket_close)
        if pre <= t < reg_open:
            return "PREMARKET"
        if reg_open <= t < reg_close:
            return "REGULAR"
        if reg_close <= t < after:
            return "AFTERMARKET"
        return "CLOSED"

    def advance(self, dt: datetime) -> MarketClockEvent | None:
        new_state = self.state_at(dt)
        if new_state == self.state:
            return None
        previous = self.state
        self.sequence += 1
        timestamp = dt.astimezone(ZoneInfo(self.calendar.timezone)).isoformat()
        base = {
            "sequence":self.sequence,
            "event_type":"MARKET_STATE_CHANGED",
            "previous_state":previous,
            "new_state":new_state,
            "timestamp":timestamp,
        }
        event = MarketClockEvent(
            sequence=self.sequence,
            event_type="MARKET_STATE_CHANGED",
            previous_state=previous,
            new_state=new_state,
            timestamp=timestamp,
            event_sha256=digest_json(base),
        )
        self.events.append(event)
        self.state = new_state
        return event

def build_market_clock_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.25" or cert.get("status")!="PASS":
        errors.append("runtime_scheduler_certificate")
    if cert.get("certification_scope")!="OFFLINE_MARKET_CLOCK_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    clock=config.get("market_clock",{})
    for key in ("timezone","holidays","early_closes","session_times"):
        if key not in clock:
            errors.append(f"config_{key}")
    if clock.get("timezone")!="America/New_York":
        errors.append("timezone")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.26.market_clock_foundation.1",
        "stage":"V78.26","status":status,
        "scope":"OFFLINE_MARKET_CLOCK_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "market_clock":clock,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_27_TRADING_SESSION_CALENDAR",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"market_clock_foundation_v78_26.json",doc)
    ver={"stage":"V78.26","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_clock_foundation_verification_v78_26.json",ver)
    return doc

def build_trading_session_calendar(foundation_path: Path, output_dir: Path) -> dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.26" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    cfg=foundation.get("market_clock",{})
    calendar=DeterministicTradingCalendar(cfg.get("timezone","America/New_York"),
        cfg.get("holidays",[]),cfg.get("early_closes",{}))
    dates=[
        date(2026,7,3),
        date(2026,7,4),
        date(2026,7,6),
        date(2026,11,27),
        date(2026,11,28),
    ]
    sessions=[asdict(calendar.session_for(d)) for d in dates]
    checks={
        "holiday_closed":sessions[0]["session_type"]=="CLOSED" and sessions[0]["is_holiday"] is True,
        "weekend_closed":sessions[1]["session_type"]=="CLOSED" and sessions[1]["is_holiday"] is False,
        "normal_day_open":sessions[2]["session_type"]=="TRADING_DAY" and sessions[2]["regular_close"]=="16:00",
        "early_close_applied":sessions[3]["is_early_close"] is True and sessions[3]["regular_close"]=="13:00",
        "next_trading_day_skips_holiday_weekend":calendar.next_trading_day(date(2026,7,2))==date(2026,7,6),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("trading_session_calendar_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.27.trading_session_calendar.1",
        "stage":"V78.27","status":status,
        "sessions":sessions,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_28_MARKET_OPEN_CLOSE_TRANSITION_ENGINE",
    }
    doc["calendar_sha256"]=digest_json({k:v for k,v in doc.items() if k!="calendar_sha256"})
    write_json(output_dir/"trading_session_calendar_v78_27.json",doc)
    ver={"stage":"V78.27","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"calendar_sha256":doc["calendar_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"trading_session_calendar_verification_v78_27.json",ver)
    return doc

def run_market_transition_engine(foundation_path: Path, output_dir: Path) -> dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.26" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    cfg=foundation.get("market_clock",{})
    calendar=DeterministicTradingCalendar(cfg["timezone"],cfg["holidays"],cfg["early_closes"])
    clock=DeterministicMarketClock(calendar)
    tz=ZoneInfo(cfg["timezone"])
    timestamps=[
        datetime(2026,7,6,3,59,tzinfo=tz),
        datetime(2026,7,6,4,0,tzinfo=tz),
        datetime(2026,7,6,9,30,tzinfo=tz),
        datetime(2026,7,6,16,0,tzinfo=tz),
        datetime(2026,7,6,20,0,tzinfo=tz),
    ]
    events=[]
    for ts in timestamps:
        evt=clock.advance(ts)
        if evt is not None:
            events.append(asdict(evt))
    early_states=[
        clock.state_at(datetime(2026,11,27,12,59,tzinfo=tz)),
        clock.state_at(datetime(2026,11,27,13,0,tzinfo=tz)),
        clock.state_at(datetime(2026,11,27,20,0,tzinfo=tz)),
    ]
    holiday_state=clock.state_at(datetime(2026,7,3,10,0,tzinfo=tz))
    checks={
        "transition_sequence":[x["new_state"] for x in events]==["PREMARKET","REGULAR","AFTERMARKET","CLOSED"],
        "event_sequences_contiguous":[x["sequence"] for x in events]==[1,2,3,4],
        "event_hashes_unique":len({x["event_sha256"] for x in events})==4,
        "early_close_transition":early_states==["REGULAR","AFTERMARKET","CLOSED"],
        "holiday_closed":holiday_state=="CLOSED",
        "final_state_closed":clock.state=="CLOSED",
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("market_transition_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.28.market_transition_engine.1",
        "stage":"V78.28","status":status,
        "events":events,
        "early_close_states":early_states,
        "holiday_state":holiday_state,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_29_MARKET_CLOCK_SAFETY_GATE",
    }
    doc["transition_sha256"]=digest_json({k:v for k,v in doc.items() if k!="transition_sha256"})
    write_json(output_dir/"market_open_close_transition_engine_v78_28.json",doc)
    ver={"stage":"V78.28","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"transition_sha256":doc["transition_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_open_close_transition_engine_verification_v78_28.json",ver)
    return doc

def run_market_clock_safety_gate(foundation_path:Path,calendar_path:Path,transition_path:Path,output_dir:Path)->dict:
    foundation,calendar,transition=map(load_json,(foundation_path,calendar_path,transition_path))
    errors=[]
    for expected,doc in (("V78.26",foundation),("V78.27",calendar),("V78.28",transition)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    events=transition.get("events",[])
    checks={
        "timezone_new_york":foundation.get("market_clock",{}).get("timezone")=="America/New_York",
        "calendar_checks_passed":calendar.get("failed_checks")==[],
        "transition_checks_passed":transition.get("failed_checks")==[],
        "event_sequences_contiguous":[x["sequence"] for x in events]==list(range(1,len(events)+1)),
        "event_hashes_unique":len({x["event_sha256"] for x in events})==len(events),
        "holiday_closed":transition.get("holiday_state")=="CLOSED",
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,calendar,transition)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,calendar,transition)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,calendar,transition)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("market_clock_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.29.market_clock_safety_gate.1",
        "stage":"V78.29","status":status,
        "gate_scope":"OFFLINE_MARKET_DATA_ADAPTER_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_MARKET_DATA_ADAPTER" if not errors else "BLOCK_MARKET_DATA_ADAPTER",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_30_MARKET_CLOCK_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"market_clock_safety_gate_v78_29.json",doc)
    ver={"stage":"V78.29","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "failed_checks":failed,"safety_gate_sha256":doc["safety_gate_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_clock_safety_gate_verification_v78_29.json",ver)
    return doc

def issue_market_clock_certificate(v26:Path,v27:Path,v28:Path,v29:Path,foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v26,v27,v28,v29)))
    foundation=load_json(foundation_path)
    expected=["V78.26","V78.27","V78.28","V78.29"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.30.market_clock_certificate.1",
        "stage":"V78.30",
        "certificate_id":"MARKET-CLOCK-V78.30",
        "status":status,
        "decision":"certified_for_offline_market_data_adapter" if not errors else "market_clock_rejected",
        "certification_scope":"OFFLINE_MARKET_DATA_ADAPTER_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_31_MARKET_DATA_ADAPTER_FOUNDATION" if not errors else "REPAIR_V78_30",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"market_clock_certificate_v78_30.json",cert)
    ver={"stage":"V78.30","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_clock_certificate_verification_v78_30.json",ver)
    return cert
