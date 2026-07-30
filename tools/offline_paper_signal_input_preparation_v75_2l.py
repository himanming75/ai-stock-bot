from __future__ import annotations
import argparse, copy, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "75.2L"
SCHEMA_VERSION = "v75.2l.offline_paper_signal_input_preparation.1"
SOURCE_SCHEMA = "v75.2k.offline_paper_cycle_runtime_baseline_certificate.1"

class SignalInputPreparationError(ValueError):
    pass

def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()

def read_json(path: Path) -> Dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SignalInputPreparationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SignalInputPreparationError(f"invalid JSON: {path}") from exc
    if not isinstance(obj, dict):
        raise SignalInputPreparationError("top-level JSON must be an object")
    return obj

def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise SignalInputPreparationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise SignalInputPreparationError("unsupported source schema")
    if source.get("certificate_state") != "READY_FOR_SIGNAL_INPUT_PREPARATION":
        raise SignalInputPreparationError("baseline is not ready for signal input preparation")
    if source.get("cycle_active") is not True:
        raise SignalInputPreparationError("cycle must be active")
    observed = source.get("offline_paper_cycle_runtime_baseline_certificate_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise SignalInputPreparationError("baseline certificate SHA256 is invalid")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_cycle_runtime_baseline_certificate_sha256", None)
    if sha256_of(clone) != observed:
        raise SignalInputPreparationError("baseline certificate integrity failed")
    if source.get("baseline_checks_sha256") != sha256_of(source.get("baseline_checks")):
        raise SignalInputPreparationError("baseline checks integrity failed")
    if source.get("baseline_ledger_sha256") != sha256_of(source.get("baseline_ledger")):
        raise SignalInputPreparationError("baseline ledger integrity failed")
    if source.get("baseline_snapshot_sha256") != sha256_of(source.get("baseline_snapshot")):
        raise SignalInputPreparationError("baseline snapshot integrity failed")
    gate = source.get("baseline_gate")
    expected = {
        "runtime_baseline_certified": True,
        "signal_input_preparation_allowed": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise SignalInputPreparationError("baseline gate missing")
    for key, value in expected.items():
        if gate.get(key) != value:
            raise SignalInputPreparationError(f"baseline_gate {key} is invalid")
    snap = source.get("baseline_snapshot")
    if not isinstance(snap, dict) or snap.get("state") != "ACTIVE":
        raise SignalInputPreparationError("baseline snapshot must be ACTIVE")
    for key, value in {
        "signal_generation_started": False,
        "order_generation_started": False,
        "fill_simulation_started": False,
        "order_queue": [],
        "orders_submitted": 0,
        "positions_mutated": False,
        "broker_connected": False,
        "network_enabled": False,
        "live_orders_enabled": False,
    }.items():
        if snap.get(key) != value:
            raise SignalInputPreparationError(f"baseline snapshot {key} is invalid")
    for key in ("paper_orders_allowed", "live_orders_allowed", "network_allowed", "broker_connection_allowed"):
        if source.get(key) is not False:
            raise SignalInputPreparationError(f"{key} must be false")

def validate_config(config: Dict[str, Any]) -> None:
    if config.get("input_mode") != "STATIC_OFFLINE_FIXTURE":
        raise SignalInputPreparationError("input_mode must be STATIC_OFFLINE_FIXTURE")
    symbols = config.get("symbols")
    if not isinstance(symbols, list) or not symbols or any(not isinstance(x, str) or not x for x in symbols):
        raise SignalInputPreparationError("symbols must be a non-empty string list")
    if len(set(symbols)) != len(symbols):
        raise SignalInputPreparationError("symbols must be unique")
    bars = config.get("market_bars")
    if not isinstance(bars, list) or len(bars) < 3:
        raise SignalInputPreparationError("at least 3 market bars are required")
    timestamps = []
    for i, bar in enumerate(bars, 1):
        if not isinstance(bar, dict):
            raise SignalInputPreparationError("each market bar must be an object")
        if bar.get("symbol") not in symbols:
            raise SignalInputPreparationError("market bar symbol is not configured")
        for field in ("open", "high", "low", "close", "volume"):
            if not isinstance(bar.get(field), (int, float)) or bar[field] < 0:
                raise SignalInputPreparationError(f"invalid {field}")
        if not (bar["low"] <= min(bar["open"], bar["close"]) <= max(bar["open"], bar["close"]) <= bar["high"]):
            raise SignalInputPreparationError("OHLC relationship is invalid")
        ts = bar.get("timestamp")
        if not isinstance(ts, str) or not ts:
            raise SignalInputPreparationError("timestamp is required")
        timestamps.append((bar["symbol"], ts))
    if len(set(timestamps)) != len(timestamps):
        raise SignalInputPreparationError("duplicate symbol/timestamp bars are not allowed")
    strategy = config.get("strategy_inputs")
    if not isinstance(strategy, dict) or not strategy:
        raise SignalInputPreparationError("strategy_inputs are required")
    for key in ("signal_generation_allowed", "order_generation_allowed", "fill_simulation_allowed",
                "paper_orders_allowed", "live_orders_allowed", "network_allowed",
                "broker_connection_allowed", "external_side_effects_allowed"):
        if config.get(key) is not False:
            raise SignalInputPreparationError(f"{key} must be false")

def preparation_id(certificate_id: str, prepared_at: str) -> str:
    return "SIP-" + hashlib.sha256(f"{certificate_id}|{prepared_at}|{VERSION}".encode()).hexdigest()[:16].upper()

def build_preparation(source: Dict[str, Any], config: Dict[str, Any], prepared_at: Optional[str] = None) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)
    if prepared_at is None:
        when = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        try:
            when = datetime.fromisoformat(prepared_at)
        except ValueError as exc:
            raise SignalInputPreparationError("prepared_at must be ISO-8601") from exc
        if when.tzinfo is None:
            raise SignalInputPreparationError("prepared_at must include timezone")
    prepared = when.isoformat()
    pid = preparation_id(source["certificate_id"], prepared)
    market_data = {
        "mode": "STATIC_OFFLINE_FIXTURE",
        "symbols": copy.deepcopy(config["symbols"]),
        "bars": copy.deepcopy(config["market_bars"]),
        "bar_count": len(config["market_bars"]),
        "network_source": False,
        "immutable": True,
    }
    strategy_inputs = copy.deepcopy(config["strategy_inputs"])
    strategy_inputs["immutable"] = True
    package = {
        "preparation_id": pid,
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "session_id": source["session_id"],
        "champion_candidate_id": source["champion_candidate_id"],
        "market_data": market_data,
        "strategy_inputs": strategy_inputs,
        "prepared_at": prepared,
    }
    checks = [
        {"check_index": 1, "check": "BASELINE_CERTIFICATE_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "STATIC_OFFLINE_INPUT_MODE", "state": "PASS"},
        {"check_index": 3, "check": "SYMBOL_UNIVERSE_VALID", "state": "PASS"},
        {"check_index": 4, "check": "MARKET_BARS_VALID", "state": "PASS"},
        {"check_index": 5, "check": "STRATEGY_INPUTS_VALID", "state": "PASS"},
        {"check_index": 6, "check": "INPUT_PACKAGE_IMMUTABLE", "state": "LOCKED"},
        {"check_index": 7, "check": "SIGNAL_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 8, "check": "ORDER_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 9, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 10, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "BASELINE_CERTIFICATE_VERIFIED", "state": "PASS", "preparation_id": pid},
        {"ledger_index": 2, "event": "OFFLINE_MARKET_DATA_LOCKED", "state": "LOCKED", "preparation_id": pid},
        {"ledger_index": 3, "event": "STRATEGY_INPUTS_LOCKED", "state": "LOCKED", "preparation_id": pid},
        {"ledger_index": 4, "event": "SIGNAL_INPUT_PACKAGE_CREATED", "state": "READY", "preparation_id": pid},
        {"ledger_index": 5, "event": "SIGNAL_INPUT_PREPARATION_COMPLETED", "state": "READY_FOR_SIGNAL_INPUT_VALIDATION", "preparation_id": pid},
    ]
    result = {
        "status": "PASS",
        "decision": "offline_paper_signal_input_prepared",
        "preparation_id": pid,
        "preparation_state": "READY_FOR_SIGNAL_INPUT_VALIDATION",
        "certificate_id": source["certificate_id"],
        "execution_id": source["execution_id"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "signal_input_package": package,
        "signal_input_package_sha256": sha256_of(package),
        "preparation_checks": checks,
        "preparation_checks_sha256": sha256_of(checks),
        "preparation_ledger": ledger,
        "preparation_ledger_sha256": sha256_of(ledger),
        "source_runtime_baseline_certificate_sha256": source["offline_paper_cycle_runtime_baseline_certificate_sha256"],
        "preparation_gate": {
            "signal_input_prepared": True,
            "signal_input_validation_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2M",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "prepared_at": prepared,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_signal_input_preparation_sha256"] = sha256_of(result)
    return result

def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_signal_input_preparation_v75_2l.json": result,
        "offline_paper_signal_input_package_v75_2l.json": result["signal_input_package"],
        "offline_paper_signal_input_preparation_checks_v75_2l.json": {
            "preparation_id": result["preparation_id"],
            "preparation_checks": result["preparation_checks"],
            "preparation_checks_sha256": result["preparation_checks_sha256"],
        },
        "offline_paper_signal_input_preparation_ledger_v75_2l.json": {
            "preparation_id": result["preparation_id"],
            "preparation_ledger": result["preparation_ledger"],
            "preparation_ledger_sha256": result["preparation_ledger_sha256"],
        },
    }
    for name, payload in payloads.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "offline_paper_signal_input_preparation_v75_2l.sha256").write_text(
        result["offline_paper_signal_input_preparation_sha256"] + "\n", encoding="utf-8"
    )

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="V75.2L Offline Paper Signal Input Preparation")
    p.add_argument("--input", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--prepared-at")
    args = p.parse_args(argv)
    try:
        result = build_preparation(read_json(Path(args.input)), read_json(Path(args.config)), args.prepared_at)
        write_outputs(result, Path(args.output_dir))
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "preparation_id": result["preparation_id"],
            "preparation_state": result["preparation_state"],
            "session_id": result["session_id"],
            "cycle_id": result["cycle_id"],
            "cycle_sequence": result["cycle_sequence"],
            "bar_count": result["signal_input_package"]["market_data"]["bar_count"],
            "signal_input_prepared": result["preparation_gate"]["signal_input_prepared"],
            "signal_input_validation_allowed": result["preparation_gate"]["signal_input_validation_allowed"],
            "signal_generation_allowed": result["preparation_gate"]["signal_generation_allowed"],
            "order_generation_allowed": result["preparation_gate"]["order_generation_allowed"],
            "paper_orders_allowed": result["paper_orders_allowed"],
            "live_orders_allowed": result["live_orders_allowed"],
            "network_allowed": result["network_allowed"],
            "orders_submitted": result["orders_submitted"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_signal_input_preparation_sha256": result["offline_paper_signal_input_preparation_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (SignalInputPreparationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_signal_input_preparation_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
