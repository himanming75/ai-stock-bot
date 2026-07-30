from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "75.2O"
SCHEMA_VERSION = "v75.2o.offline_paper_signal_generation_execution.1"
AUTH_SCHEMA = "v75.2n.offline_paper_signal_generation_authorization.1"
PREPARATION_SCHEMA = "v75.2l.offline_paper_signal_input_preparation.1"
OUTPUT_NAME = "offline_paper_signal_generation_execution_v75_2o.json"


class SignalGenerationExecutionError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SignalGenerationExecutionError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SignalGenerationExecutionError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SignalGenerationExecutionError("top-level JSON must be an object")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SignalGenerationExecutionError(
            f"{field} must be a non-empty ISO-8601 string"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SignalGenerationExecutionError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SignalGenerationExecutionError(f"{field} must include timezone")
    return parsed


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("execution_scope") != "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY":
        raise SignalGenerationExecutionError("execution_scope is invalid")
    if config.get("signal_method") != "SIMPLE_MOVING_AVERAGE_CROSSOVER":
        raise SignalGenerationExecutionError("signal_method is invalid")
    if config.get("buy_when_fast_above_slow") is not True:
        raise SignalGenerationExecutionError("buy_when_fast_above_slow must be true")
    if config.get("sell_when_fast_below_slow") is not True:
        raise SignalGenerationExecutionError("sell_when_fast_below_slow must be true")
    if config.get("hold_when_equal") is not True:
        raise SignalGenerationExecutionError("hold_when_equal must be true")
    for key in (
        "require_authorization_integrity",
        "require_input_package_integrity",
        "require_single_use_token",
        "require_token_unconsumed",
        "require_token_unexpired",
        "require_static_offline_fixture",
        "require_immutable_inputs",
        "prevent_output_overwrite",
    ):
        if config.get(key) is not True:
            raise SignalGenerationExecutionError(f"{key} must be true")
    for key in (
        "order_generation_allowed",
        "fill_simulation_allowed",
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise SignalGenerationExecutionError(f"{key} must be false")


def validate_authorization(auth: Dict[str, Any], executed_at: datetime) -> None:
    if auth.get("status") != "PASS":
        raise SignalGenerationExecutionError("authorization status must be PASS")
    if auth.get("schema_version") != AUTH_SCHEMA:
        raise SignalGenerationExecutionError("unsupported authorization schema")
    if auth.get("authorization_state") != "AUTHORIZED_NOT_EXECUTED":
        raise SignalGenerationExecutionError("authorization is not executable")
    if auth.get("authorization_scope") != "OFFLINE_PAPER_SIGNAL_GENERATION_ONLY":
        raise SignalGenerationExecutionError("authorization scope is invalid")
    if auth.get("signal_generation_authorized") is not True:
        raise SignalGenerationExecutionError("signal generation is not authorized")
    if auth.get("signal_generation_executed") is not False:
        raise SignalGenerationExecutionError("signal generation was already executed")
    if auth.get("token_consumed") is not False:
        raise SignalGenerationExecutionError("authorization token was already consumed")

    observed = auth.get("offline_paper_signal_generation_authorization_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise SignalGenerationExecutionError("authorization SHA256 is invalid")
    clone = copy.deepcopy(auth)
    clone.pop("offline_paper_signal_generation_authorization_sha256", None)
    if sha256_of(clone) != observed:
        raise SignalGenerationExecutionError("authorization integrity failed")

    checks = auth.get("authorization_checks")
    ledger = auth.get("authorization_ledger")
    token = auth.get("authorization_token")
    if auth.get("authorization_checks_sha256") != sha256_of(checks):
        raise SignalGenerationExecutionError("authorization checks integrity failed")
    if auth.get("authorization_ledger_sha256") != sha256_of(ledger):
        raise SignalGenerationExecutionError("authorization ledger integrity failed")
    if auth.get("authorization_token_sha256") != sha256_of(token):
        raise SignalGenerationExecutionError("authorization token envelope integrity failed")
    if not isinstance(token, dict):
        raise SignalGenerationExecutionError("authorization token is required")

    token_material = {
        "authorization_id": token.get("authorization_id"),
        "validation_id": token.get("validation_id"),
        "issued_at": token.get("issued_at"),
        "expires_at": token.get("expires_at"),
        "nonce": token.get("nonce"),
        "scope": token.get("scope"),
    }
    if token.get("token_sha256") != sha256_of(token_material):
        raise SignalGenerationExecutionError("authorization token integrity failed")
    if token.get("authorization_id") != auth.get("authorization_id"):
        raise SignalGenerationExecutionError("token authorization_id mismatch")
    if token.get("validation_id") != auth.get("validation_id"):
        raise SignalGenerationExecutionError("token validation_id mismatch")
    if token.get("scope") != auth.get("authorization_scope"):
        raise SignalGenerationExecutionError("token scope mismatch")
    if token.get("single_use") is not True:
        raise SignalGenerationExecutionError("token must be single use")
    if token.get("consumed") is not False:
        raise SignalGenerationExecutionError("token is already consumed")
    if token.get("consumed_at") is not None:
        raise SignalGenerationExecutionError("unconsumed token cannot have consumed_at")
    if token.get("token_state") != "ISSUED_NOT_CONSUMED":
        raise SignalGenerationExecutionError("token state is invalid")

    issued = parse_timestamp(token.get("issued_at"), "token issued_at")
    expires = parse_timestamp(token.get("expires_at"), "token expires_at")
    if expires <= issued:
        raise SignalGenerationExecutionError("token expiry must follow issuance")
    if executed_at < issued:
        raise SignalGenerationExecutionError("execution is before token issuance")
    if executed_at > expires:
        raise SignalGenerationExecutionError("authorization token expired")

    gate = auth.get("authorization_gate")
    expected = {
        "signal_generation_authorized": True,
        "signal_generation_execution_allowed": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise SignalGenerationExecutionError("authorization_gate is required")
    for key, value in expected.items():
        if gate.get(key) != value:
            raise SignalGenerationExecutionError(f"authorization_gate {key} is invalid")

    for key in (
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if auth.get(key) is not False:
            raise SignalGenerationExecutionError(f"{key} must be false")
    if auth.get("orders_submitted") != 0:
        raise SignalGenerationExecutionError("orders_submitted must be zero")
    if auth.get("approved_for_live") is not False:
        raise SignalGenerationExecutionError("approved_for_live must be false")
    if auth.get("network_used") is not False:
        raise SignalGenerationExecutionError("network_used must be false")

    lock = auth.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise SignalGenerationExecutionError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise SignalGenerationExecutionError(f"safety_lock {key} must be false")


def validate_preparation(
    preparation: Dict[str, Any], auth: Dict[str, Any]
) -> Dict[str, Any]:
    if preparation.get("status") != "PASS":
        raise SignalGenerationExecutionError("preparation status must be PASS")
    if preparation.get("schema_version") != PREPARATION_SCHEMA:
        raise SignalGenerationExecutionError("unsupported preparation schema")

    observed = preparation.get("offline_paper_signal_input_preparation_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise SignalGenerationExecutionError("preparation SHA256 is invalid")
    clone = copy.deepcopy(preparation)
    clone.pop("offline_paper_signal_input_preparation_sha256", None)
    if sha256_of(clone) != observed:
        raise SignalGenerationExecutionError("preparation integrity failed")

    package = preparation.get("signal_input_package")
    if not isinstance(package, dict):
        raise SignalGenerationExecutionError("signal_input_package is required")
    package_hash = sha256_of(package)
    if preparation.get("signal_input_package_sha256") != package_hash:
        raise SignalGenerationExecutionError("signal input package integrity failed")
    if auth.get("source_signal_input_package_sha256") != package_hash:
        raise SignalGenerationExecutionError(
            "authorization and input package hashes do not match"
        )

    identities = (
        "preparation_id",
        "certificate_id",
        "execution_id",
        "session_id",
        "cycle_id",
        "cycle_sequence",
        "champion_candidate_id",
    )
    for key in identities:
        if preparation.get(key) != auth.get(key):
            raise SignalGenerationExecutionError(f"{key} mismatch")

    market = package.get("market_data")
    strategy = package.get("strategy_inputs")
    if not isinstance(market, dict) or not isinstance(strategy, dict):
        raise SignalGenerationExecutionError("market_data and strategy_inputs are required")
    if market.get("mode") != "STATIC_OFFLINE_FIXTURE":
        raise SignalGenerationExecutionError("market data must be static offline fixture")
    if market.get("network_source") is not False:
        raise SignalGenerationExecutionError("network source must be false")
    if market.get("immutable") is not True or strategy.get("immutable") is not True:
        raise SignalGenerationExecutionError("inputs must be immutable")
    return package


def execution_id(authorization_id: str, executed_at: str) -> str:
    material = f"{authorization_id}|{executed_at}|{VERSION}"
    return "SGE-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def compute_signals(package: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    market = package["market_data"]
    strategy = package["strategy_inputs"]
    symbols = market["symbols"]
    bars = market["bars"]
    price_field = strategy["price_field"]
    fast_window = strategy["fast_window"]
    slow_window = strategy["slow_window"]

    signals: List[Dict[str, Any]] = []
    grouped: Dict[str, List[Dict[str, Any]]] = {symbol: [] for symbol in symbols}
    for bar in bars:
        grouped[bar["symbol"]].append(bar)

    for symbol in symbols:
        symbol_bars = sorted(grouped[symbol], key=lambda bar: bar["timestamp"])
        if len(symbol_bars) < slow_window:
            raise SignalGenerationExecutionError(f"insufficient history for {symbol}")
        prices = [float(bar[price_field]) for bar in symbol_bars]
        fast_values = prices[-fast_window:]
        slow_values = prices[-slow_window:]
        fast_sma = sum(fast_values) / fast_window
        slow_sma = sum(slow_values) / slow_window
        if fast_sma > slow_sma:
            action = "BUY"
        elif fast_sma < slow_sma:
            action = "SELL"
        else:
            action = "HOLD"
        signal_material = {
            "symbol": symbol,
            "as_of": symbol_bars[-1]["timestamp"],
            "strategy_id": strategy["strategy_id"],
            "signal_method": "SIMPLE_MOVING_AVERAGE_CROSSOVER",
            "price_field": price_field,
            "fast_window": fast_window,
            "slow_window": slow_window,
            "fast_sma": round(fast_sma, 10),
            "slow_sma": round(slow_sma, 10),
            "latest_price": prices[-1],
            "action": action,
        }
        signals.append({
            **signal_material,
            "signal_id": "SIG-" + sha256_of(signal_material)[:16].upper(),
            "order_created": False,
            "order_submitted": False,
        })

    summary = {
        "signal_count": len(signals),
        "buy_count": sum(s["action"] == "BUY" for s in signals),
        "sell_count": sum(s["action"] == "SELL" for s in signals),
        "hold_count": sum(s["action"] == "HOLD" for s in signals),
        "symbols": copy.deepcopy(symbols),
        "strategy_id": strategy["strategy_id"],
        "signal_method": "SIMPLE_MOVING_AVERAGE_CROSSOVER",
    }
    return signals, summary


def build_execution(
    auth: Dict[str, Any],
    preparation: Dict[str, Any],
    config: Dict[str, Any],
    executed_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_config(config)
    when = (
        datetime.now(timezone.utc).replace(microsecond=0)
        if executed_at is None
        else parse_timestamp(executed_at, "executed_at")
    )
    validate_authorization(auth, when)
    package = validate_preparation(preparation, auth)
    signals, summary = compute_signals(package)

    executed_at_value = when.isoformat()
    eid = execution_id(auth["authorization_id"], executed_at_value)
    consumed_token = copy.deepcopy(auth["authorization_token"])
    consumed_token.update({
        "consumed": True,
        "consumed_at": executed_at_value,
        "token_state": "CONSUMED",
    })

    checks = [
        {"check_index": 1, "check": "SIGNAL_GENERATION_AUTHORIZATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "AUTHORIZATION_TOKEN_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "AUTHORIZATION_TOKEN_TIME_WINDOW", "state": "PASS"},
        {"check_index": 4, "check": "AUTHORIZATION_TOKEN_SINGLE_USE", "state": "CONSUMED"},
        {"check_index": 5, "check": "SIGNAL_INPUT_PACKAGE_INTEGRITY", "state": "PASS"},
        {"check_index": 6, "check": "STATIC_OFFLINE_INPUT_MODE", "state": "PASS"},
        {"check_index": 7, "check": "SIGNAL_CALCULATION_COMPLETED", "state": "PASS"},
        {"check_index": 8, "check": "ORDER_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 9, "check": "FILL_SIMULATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 10, "check": "ZERO_ORDER_SIDE_EFFECTS", "state": "PASS"},
        {"check_index": 11, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 12, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "SIGNAL_GENERATION_AUTHORIZATION_VERIFIED", "state": "PASS", "signal_execution_id": eid},
        {"ledger_index": 2, "event": "SINGLE_USE_TOKEN_CONSUMED", "state": "CONSUMED", "signal_execution_id": eid},
        {"ledger_index": 3, "event": "SIGNAL_INPUT_PACKAGE_LOADED", "state": "LOCKED", "signal_execution_id": eid},
        {"ledger_index": 4, "event": "OFFLINE_SIGNAL_CALCULATION_EXECUTED", "state": "PASS", "signal_execution_id": eid},
        {"ledger_index": 5, "event": "SIGNAL_OUTPUT_PACKAGE_CREATED", "state": "READY", "signal_execution_id": eid},
        {"ledger_index": 6, "event": "SIGNAL_GENERATION_EXECUTION_COMPLETED", "state": "READY_FOR_SIGNAL_OUTPUT_VALIDATION", "signal_execution_id": eid},
    ]
    signal_package = {
        "signal_execution_id": eid,
        "authorization_id": auth["authorization_id"],
        "validation_id": auth["validation_id"],
        "preparation_id": auth["preparation_id"],
        "session_id": auth["session_id"],
        "cycle_id": auth["cycle_id"],
        "cycle_sequence": auth["cycle_sequence"],
        "champion_candidate_id": auth["champion_candidate_id"],
        "executed_at": executed_at_value,
        "signals": signals,
        "signal_summary": summary,
        "immutable": True,
        "network_source": False,
        "orders_created": 0,
        "orders_submitted": 0,
    }

    result = {
        "status": "PASS",
        "decision": "offline_paper_signal_generation_executed",
        "signal_execution_id": eid,
        "execution_state": "READY_FOR_SIGNAL_OUTPUT_VALIDATION",
        "authorization_id": auth["authorization_id"],
        "authorization_state": "CONSUMED",
        "signal_generation_authorized": True,
        "signal_generation_executed": True,
        "token_consumed": True,
        "consumed_authorization_token": consumed_token,
        "consumed_authorization_token_sha256": sha256_of(consumed_token),
        "signal_output_package": signal_package,
        "signal_output_package_sha256": sha256_of(signal_package),
        "execution_checks": checks,
        "execution_checks_sha256": sha256_of(checks),
        "execution_ledger": ledger,
        "execution_ledger_sha256": sha256_of(ledger),
        "source_signal_generation_authorization_sha256":
            auth["offline_paper_signal_generation_authorization_sha256"],
        "source_signal_input_package_sha256":
            preparation["signal_input_package_sha256"],
        "validation_id": auth["validation_id"],
        "preparation_id": auth["preparation_id"],
        "certificate_id": auth["certificate_id"],
        "execution_id": auth["execution_id"],
        "session_id": auth["session_id"],
        "cycle_id": auth["cycle_id"],
        "cycle_sequence": auth["cycle_sequence"],
        "champion_candidate_id": auth["champion_candidate_id"],
        "execution_gate": {
            "signal_generation_executed": True,
            "signal_output_validation_allowed": True,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2P",
        },
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_created": 0,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(auth["safety_lock"]),
        "executed_at": executed_at_value,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_signal_generation_execution_sha256"] = sha256_of(result)
    return result


def write_outputs(
    result: Dict[str, Any], output_dir: Path, prevent_overwrite: bool = True
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    primary = output_dir / OUTPUT_NAME
    if prevent_overwrite and primary.exists():
        raise SignalGenerationExecutionError(
            f"execution output already exists: {primary}"
        )
    payloads = {
        OUTPUT_NAME: result,
        "offline_paper_signal_output_package_v75_2o.json":
            result["signal_output_package"],
        "offline_paper_signal_generation_execution_checks_v75_2o.json": {
            "signal_execution_id": result["signal_execution_id"],
            "execution_checks": result["execution_checks"],
            "execution_checks_sha256": result["execution_checks_sha256"],
        },
        "offline_paper_signal_generation_execution_ledger_v75_2o.json": {
            "signal_execution_id": result["signal_execution_id"],
            "execution_ledger": result["execution_ledger"],
            "execution_ledger_sha256": result["execution_ledger_sha256"],
        },
        "offline_paper_signal_generation_consumed_token_v75_2o.json":
            result["consumed_authorization_token"],
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "offline_paper_signal_generation_execution_v75_2o.sha256").write_text(
        result["offline_paper_signal_generation_execution_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.2O Offline Paper Signal Generation Executor"
    )
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--signal-input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--executed-at")
    args = parser.parse_args(argv)
    try:
        config = read_json(Path(args.config))
        output_dir = Path(args.output_dir)
        if config.get("prevent_output_overwrite") is True and (
            output_dir / OUTPUT_NAME
        ).exists():
            raise SignalGenerationExecutionError(
                f"execution output already exists: {output_dir / OUTPUT_NAME}"
            )
        result = build_execution(
            read_json(Path(args.authorization)),
            read_json(Path(args.signal_input)),
            config,
            args.executed_at,
        )
        write_outputs(result, output_dir, config["prevent_output_overwrite"])
        summary = result["signal_output_package"]["signal_summary"]
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "signal_execution_id": result["signal_execution_id"],
            "execution_state": result["execution_state"],
            "authorization_id": result["authorization_id"],
            "authorization_state": result["authorization_state"],
            "signal_generation_executed": result["signal_generation_executed"],
            "token_consumed": result["token_consumed"],
            "signal_count": summary["signal_count"],
            "buy_count": summary["buy_count"],
            "sell_count": summary["sell_count"],
            "hold_count": summary["hold_count"],
            "signals": [
                {
                    "signal_id": signal["signal_id"],
                    "symbol": signal["symbol"],
                    "action": signal["action"],
                    "fast_sma": signal["fast_sma"],
                    "slow_sma": signal["slow_sma"],
                    "latest_price": signal["latest_price"],
                }
                for signal in result["signal_output_package"]["signals"]
            ],
            "signal_output_validation_allowed":
                result["execution_gate"]["signal_output_validation_allowed"],
            "order_generation_allowed": result["order_generation_allowed"],
            "fill_simulation_allowed": result["fill_simulation_allowed"],
            "orders_created": result["orders_created"],
            "orders_submitted": result["orders_submitted"],
            "network_allowed": result["network_allowed"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_signal_generation_execution_sha256":
                result["offline_paper_signal_generation_execution_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (SignalGenerationExecutionError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_signal_generation_execution_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_created": 0,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
