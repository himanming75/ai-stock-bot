from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
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
class RuntimeBar:
    symbol: str
    timestamp: str
    close: float
    volume: int

@dataclass(frozen=True)
class RuntimeContext:
    strategy_id: str
    candidate_id: str
    symbol: str
    fast_window: int
    slow_window: int
    minimum_history: int
    allow_order_creation: bool = False
    allow_order_submission: bool = False

@dataclass(frozen=True)
class StrategySignal:
    signal_id: str
    strategy_id: str
    candidate_id: str
    symbol: str
    timestamp: str
    action: str
    reason: str
    fast_value: float | None
    slow_value: float | None
    signal_sha256: str

@runtime_checkable
class StrategyRuntime(Protocol):
    strategy_id: str
    def evaluate(self, context: RuntimeContext, bars: list[RuntimeBar]) -> StrategySignal: ...

class StrategyRegistry:
    def __init__(self):
        self._strategies: dict[str, StrategyRuntime] = {}

    def register(self, strategy: StrategyRuntime) -> None:
        sid = str(strategy.strategy_id).strip()
        if not sid:
            raise ValueError("strategy_id required")
        if sid in self._strategies:
            raise ValueError("strategy already registered")
        if not isinstance(strategy, StrategyRuntime):
            raise TypeError("strategy does not satisfy runtime protocol")
        self._strategies[sid] = strategy

    def get(self, strategy_id: str) -> StrategyRuntime:
        if strategy_id not in self._strategies:
            raise ValueError("strategy not registered")
        return self._strategies[strategy_id]

    def strategy_ids(self) -> list[str]:
        return sorted(self._strategies)

class MovingAverageCrossStrategy:
    strategy_id = "moving_average_cross_v78"

    @staticmethod
    def _mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 8)

    def evaluate(self, context: RuntimeContext, bars: list[RuntimeBar]) -> StrategySignal:
        if context.strategy_id != self.strategy_id:
            raise ValueError("strategy context mismatch")
        if context.allow_order_creation or context.allow_order_submission:
            raise ValueError("strategy runtime cannot create or submit orders")
        if context.fast_window <= 0 or context.slow_window <= 0:
            raise ValueError("window must be positive")
        if context.fast_window >= context.slow_window:
            raise ValueError("fast_window must be less than slow_window")
        if not bars:
            raise ValueError("bars required")
        if any(b.symbol != context.symbol for b in bars):
            raise ValueError("symbol mismatch")
        timestamps = [b.timestamp for b in bars]
        if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
            raise ValueError("bar timestamps must be strictly increasing")
        if any(b.close <= 0 or b.volume < 0 for b in bars):
            raise ValueError("invalid bar")

        latest = bars[-1]
        fast_value = None
        slow_value = None
        action = "HOLD"
        reason = "INSUFFICIENT_HISTORY"

        required = max(context.minimum_history, context.slow_window)
        if len(bars) >= required:
            closes = [b.close for b in bars]
            fast_value = self._mean(closes[-context.fast_window:])
            slow_value = self._mean(closes[-context.slow_window:])
            if fast_value > slow_value:
                action = "BUY"
                reason = "FAST_ABOVE_SLOW"
            elif fast_value < slow_value:
                action = "SELL"
                reason = "FAST_BELOW_SLOW"
            else:
                action = "HOLD"
                reason = "FAST_EQUALS_SLOW"

        base = {
            "strategy_id":self.strategy_id,
            "candidate_id":context.candidate_id,
            "symbol":context.symbol,
            "timestamp":latest.timestamp,
            "action":action,
            "reason":reason,
            "fast_value":fast_value,
            "slow_value":slow_value,
        }
        sha = digest_json(base)
        return StrategySignal(
            signal_id=f"SIG-{context.candidate_id}-{latest.timestamp}-{sha[:12]}",
            strategy_id=self.strategy_id,
            candidate_id=context.candidate_id,
            symbol=context.symbol,
            timestamp=latest.timestamp,
            action=action,
            reason=reason,
            fast_value=fast_value,
            slow_value=slow_value,
            signal_sha256=sha,
        )

def build_strategy_runtime_foundation(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json, (certificate_path, config_path))
    errors = []
    if cert.get("stage") != "V78.35" or cert.get("status") != "PASS":
        errors.append("market_data_certificate")
    if cert.get("certification_scope") != "OFFLINE_STRATEGY_RUNTIME_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")

    runtime = config.get("strategy_runtime", {})
    for key in ("strategy_id", "symbol", "minimum_history", "default_parameters"):
        if key not in runtime:
            errors.append(f"config_{key}")

    champion = cert.get("champion_candidate") or {}
    candidate_id = champion.get("candidate_id")
    if not candidate_id:
        errors.append("champion_candidate_id")

    parameters = champion.get("parameters") or {}
    defaults = runtime.get("default_parameters") or {}
    fast_window = int(parameters.get("fast_window", defaults.get("fast_window", 3)))
    slow_window = int(parameters.get("slow_window", defaults.get("slow_window", 5)))
    if fast_window <= 0 or slow_window <= 0 or fast_window >= slow_window:
        errors.append("strategy_windows")

    context = {
        "strategy_id":runtime.get("strategy_id"),
        "candidate_id":candidate_id,
        "symbol":runtime.get("symbol"),
        "fast_window":fast_window,
        "slow_window":slow_window,
        "minimum_history":max(int(runtime.get("minimum_history", slow_window)), slow_window),
        "allow_order_creation":False,
        "allow_order_submission":False,
    }
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.36.strategy_runtime_foundation.1",
        "stage":"V78.36",
        "status":status,
        "scope":"OFFLINE_SIGNAL_GENERATION_ONLY",
        "champion_candidate":champion,
        "runtime_context":context,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_37_STRATEGY_REGISTRY_RUNTIME_CONTEXT",
    }
    doc["foundation_sha256"] = digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"strategy_runtime_foundation_v78_36.json", doc)

    ver = {
        "stage":"V78.36",
        "status":status,
        "verified":not errors,
        "error_count":len(errors),
        "errors":errors,
        "foundation_sha256":doc["foundation_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"strategy_runtime_foundation_verification_v78_36.json", ver)
    return doc

def build_strategy_registry_context(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors = []
    if foundation.get("stage") != "V78.36" or foundation.get("status") != "PASS":
        errors.append("foundation_input")

    registry = StrategyRegistry()
    strategy = MovingAverageCrossStrategy()
    try:
        registry.register(strategy)
        context = RuntimeContext(**foundation["runtime_context"])
        protocol_ok = isinstance(strategy, StrategyRuntime)
    except Exception as exc:
        context = None
        protocol_ok = False
        errors.append(f"registry_exception:{type(exc).__name__}")

    checks = {
        "registry_contains_strategy":registry.strategy_ids()==["moving_average_cross_v78"],
        "protocol_compliance":protocol_ok,
        "context_candidate_present":context is not None and bool(context.candidate_id),
        "fast_window_less_than_slow":context is not None and context.fast_window < context.slow_window,
        "minimum_history_sufficient":context is not None and context.minimum_history >= context.slow_window,
        "order_creation_disabled":context is not None and context.allow_order_creation is False,
        "order_submission_disabled":context is not None and context.allow_order_submission is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("strategy_registry_context_checks")

    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.37.strategy_registry_context.1",
        "stage":"V78.37",
        "status":status,
        "strategy_ids":registry.strategy_ids(),
        "runtime_context":asdict(context) if context else None,
        "checks":checks,
        "failed_checks":failed,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_38_DETERMINISTIC_SIGNAL_EXECUTION_ENGINE",
    }
    doc["registry_context_sha256"] = digest_json({k:v for k,v in doc.items() if k!="registry_context_sha256"})
    write_json(output_dir/"strategy_registry_runtime_context_v78_37.json", doc)

    ver = {
        "stage":"V78.37",
        "status":status,
        "verified":not errors,
        "error_count":len(errors),
        "errors":errors,
        "failed_checks":failed,
        "registry_context_sha256":doc["registry_context_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"strategy_registry_runtime_context_verification_v78_37.json", ver)
    return doc

def run_deterministic_signal_execution(foundation_path: Path, output_dir: Path) -> dict:
    foundation = load_json(foundation_path)
    errors = []
    if foundation.get("stage") != "V78.36" or foundation.get("status") != "PASS":
        errors.append("foundation_input")

    context = RuntimeContext(**foundation["runtime_context"])
    strategy = MovingAverageCrossStrategy()

    def make_bars(closes: list[float], prefix: str) -> list[RuntimeBar]:
        return [
            RuntimeBar(
                symbol=context.symbol,
                timestamp=f"2026-07-06T09:{30+i:02d}:00-04:00-{prefix}",
                close=float(value),
                volume=1000+i*10,
            )
            for i, value in enumerate(closes)
        ]

    # Lexicographically monotonic deterministic timestamps without external clock calls.
    def bars_from_closes(closes: list[float]) -> list[RuntimeBar]:
        bars=[]
        for i,value in enumerate(closes):
            minute=30+i
            hour=9+minute//60
            minute=minute%60
            bars.append(RuntimeBar(
                symbol=context.symbol,
                timestamp=f"2026-07-06T{hour:02d}:{minute:02d}:00-04:00",
                close=float(value),
                volume=1000+i*10,
            ))
        return bars

    n = context.minimum_history
    try:
        insufficient = strategy.evaluate(context, bars_from_closes([100.0] * max(1, n-1)))
        buy = strategy.evaluate(context, bars_from_closes(
            [100.0] * max(0, n-context.fast_window) +
            [101.0 + i for i in range(context.fast_window)]
        ))
        sell = strategy.evaluate(context, bars_from_closes(
            [110.0] * max(0, n-context.fast_window) +
            [100.0 - i for i in range(context.fast_window)]
        ))
        hold = strategy.evaluate(context, bars_from_closes([100.0] * n))
        buy_repeat = strategy.evaluate(context, bars_from_closes(
            [100.0] * max(0, n-context.fast_window) +
            [101.0 + i for i in range(context.fast_window)]
        ))
    except Exception as exc:
        insufficient = buy = sell = hold = buy_repeat = None
        errors.append(f"signal_execution_exception:{type(exc).__name__}")

    signals = [x for x in (insufficient,buy,sell,hold) if x is not None]
    checks = {
        "insufficient_history_holds":insufficient is not None and insufficient.action=="HOLD" and insufficient.reason=="INSUFFICIENT_HISTORY",
        "buy_signal_generated":buy is not None and buy.action=="BUY",
        "sell_signal_generated":sell is not None and sell.action=="SELL",
        "equal_averages_hold":hold is not None and hold.action=="HOLD" and hold.reason=="FAST_EQUALS_SLOW",
        "deterministic_repeat":buy is not None and buy_repeat is not None and asdict(buy)==asdict(buy_repeat),
        "signal_hashes_valid":all(
            s.signal_sha256==digest_json({
                "strategy_id":s.strategy_id,
                "candidate_id":s.candidate_id,
                "symbol":s.symbol,
                "timestamp":s.timestamp,
                "action":s.action,
                "reason":s.reason,
                "fast_value":s.fast_value,
                "slow_value":s.slow_value,
            }) for s in signals
        ),
        "no_order_creation":context.allow_order_creation is False,
        "no_order_submission":context.allow_order_submission is False,
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("deterministic_signal_checks")

    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.38.deterministic_signal_execution.1",
        "stage":"V78.38",
        "status":status,
        "signals":[asdict(x) for x in signals],
        "checks":checks,
        "failed_checks":failed,
        "generated_order_count":0,
        "submitted_order_count":0,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_39_STRATEGY_RUNTIME_SAFETY_GATE",
    }
    doc["signal_execution_sha256"] = digest_json({k:v for k,v in doc.items() if k!="signal_execution_sha256"})
    write_json(output_dir/"deterministic_signal_execution_engine_v78_38.json", doc)

    ver = {
        "stage":"V78.38",
        "status":status,
        "verified":not errors,
        "error_count":len(errors),
        "errors":errors,
        "failed_checks":failed,
        "signal_execution_sha256":doc["signal_execution_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"deterministic_signal_execution_engine_verification_v78_38.json", ver)
    return doc

def run_strategy_runtime_safety_gate(foundation_path: Path, registry_path: Path, execution_path: Path, output_dir: Path) -> dict:
    foundation, registry, execution = map(load_json, (foundation_path, registry_path, execution_path))
    errors = []
    for expected, doc in (("V78.36",foundation),("V78.37",registry),("V78.38",execution)):
        if doc.get("stage") != expected or doc.get("status") != "PASS":
            errors.append(expected)

    signals = execution.get("signals", [])
    actions = {x.get("action") for x in signals}
    context = foundation.get("runtime_context", {})
    checks = {
        "offline_signal_scope":foundation.get("scope")=="OFFLINE_SIGNAL_GENERATION_ONLY",
        "champion_candidate_bound":bool(context.get("candidate_id")),
        "registry_checks_passed":registry.get("failed_checks")==[],
        "execution_checks_passed":execution.get("failed_checks")==[],
        "allowed_actions_only":actions.issubset({"BUY","SELL","HOLD"}),
        "buy_sell_hold_covered":{"BUY","SELL","HOLD"}.issubset(actions),
        "signal_ids_unique":len({x["signal_id"] for x in signals})==len(signals),
        "generated_orders_zero":execution.get("generated_order_count")==0,
        "submitted_orders_zero":execution.get("submitted_order_count")==0,
        "order_creation_disabled":context.get("allow_order_creation") is False,
        "order_submission_disabled":context.get("allow_order_submission") is False,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,registry,execution)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,registry,execution)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,registry,execution)),
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("strategy_runtime_safety_checks")

    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v78.39.strategy_runtime_safety_gate.1",
        "stage":"V78.39",
        "status":status,
        "gate_scope":"OFFLINE_SIGNAL_RISK_BRIDGE_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_SIGNAL_RISK_BRIDGE" if not errors else "BLOCK_SIGNAL_RISK_BRIDGE",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,
        "failed_checks":failed,
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_40_STRATEGY_RUNTIME_CERTIFICATE",
    }
    doc["safety_gate_sha256"] = digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"strategy_runtime_safety_gate_v78_39.json", doc)

    ver = {
        "stage":"V78.39",
        "status":status,
        "verified":not errors,
        "error_count":len(errors),
        "errors":errors,
        "failed_checks":failed,
        "safety_gate_sha256":doc["safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"strategy_runtime_safety_gate_verification_v78_39.json", ver)
    return doc

def issue_strategy_runtime_certificate(v36: Path, v37: Path, v38: Path, v39: Path, foundation_path: Path, output_dir: Path) -> dict:
    docs = list(map(load_json, (v36,v37,v38,v39)))
    foundation = load_json(foundation_path)
    expected = ["V78.36","V78.37","V78.38","V78.39"]
    errors = []
    for stage, doc in zip(expected, docs):
        if doc.get("stage") != stage or doc.get("status") != "PASS" or doc.get("verified") is not True:
            errors.append(stage)

    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v78.40.strategy_runtime_certificate.1",
        "stage":"V78.40",
        "certificate_id":"STRATEGY-RUNTIME-V78.40",
        "status":status,
        "decision":"certified_for_offline_signal_risk_bridge" if not errors else "strategy_runtime_rejected",
        "certification_scope":"OFFLINE_SIGNAL_RISK_BRIDGE_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),
        "errors":errors,
        **safety(),
        "next_phase":"V78_41_SIGNAL_RISK_BRIDGE_FOUNDATION" if not errors else "REPAIR_V78_40",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"strategy_runtime_certificate_v78_40.json", cert)

    ver = {
        "stage":"V78.40",
        "status":status,
        "verified":not errors,
        "error_count":len(errors),
        "errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"strategy_runtime_certificate_verification_v78_40.json", ver)
    return cert
