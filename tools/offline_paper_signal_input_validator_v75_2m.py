from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "75.2M"
SCHEMA_VERSION = "v75.2m.offline_paper_signal_input_validation.1"
SOURCE_SCHEMA = "v75.2l.offline_paper_signal_input_preparation.1"


class SignalInputValidationError(ValueError):
    pass


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_of(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SignalInputValidationError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SignalInputValidationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise SignalInputValidationError("top-level JSON must be an object")
    return value


def parse_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SignalInputValidationError(f"{field} must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SignalInputValidationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SignalInputValidationError(f"{field} must include timezone")
    return parsed


def validate_source(source: Dict[str, Any]) -> None:
    if source.get("status") != "PASS":
        raise SignalInputValidationError("source status must be PASS")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise SignalInputValidationError("unsupported source schema")
    if source.get("preparation_state") != "READY_FOR_SIGNAL_INPUT_VALIDATION":
        raise SignalInputValidationError("source is not ready for signal input validation")

    observed = source.get("offline_paper_signal_input_preparation_sha256")
    if not isinstance(observed, str) or len(observed) != 64:
        raise SignalInputValidationError("source preparation SHA256 is invalid")
    clone = copy.deepcopy(source)
    clone.pop("offline_paper_signal_input_preparation_sha256", None)
    if sha256_of(clone) != observed:
        raise SignalInputValidationError("source preparation integrity failed")

    checks = source.get("preparation_checks")
    ledger = source.get("preparation_ledger")
    package = source.get("signal_input_package")
    if source.get("preparation_checks_sha256") != sha256_of(checks):
        raise SignalInputValidationError("preparation checks integrity failed")
    if source.get("preparation_ledger_sha256") != sha256_of(ledger):
        raise SignalInputValidationError("preparation ledger integrity failed")
    if source.get("signal_input_package_sha256") != sha256_of(package):
        raise SignalInputValidationError("signal input package integrity failed")

    gate = source.get("preparation_gate")
    expected_gate = {
        "signal_input_prepared": True,
        "signal_input_validation_allowed": True,
        "signal_generation_allowed": False,
        "order_generation_allowed": False,
        "fill_simulation_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "next_version": VERSION,
    }
    if not isinstance(gate, dict):
        raise SignalInputValidationError("preparation gate missing")
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise SignalInputValidationError(f"preparation_gate {key} is invalid")

    for key in (
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
    ):
        if source.get(key) is not False:
            raise SignalInputValidationError(f"{key} must be false")
    if source.get("orders_submitted") != 0:
        raise SignalInputValidationError("orders_submitted must be zero")
    if source.get("approved_for_live") is not False:
        raise SignalInputValidationError("approved_for_live must be false")
    if source.get("network_used") is not False:
        raise SignalInputValidationError("network_used must be false")

    lock = source.get("safety_lock")
    if not isinstance(lock, dict) or lock.get("lock_state") != "ENFORCED":
        raise SignalInputValidationError("safety lock must be ENFORCED")
    for key in (
        "broker_connected",
        "broker_credentials_required",
        "external_side_effects_allowed",
        "live_orders_enabled",
        "live_trading_approval_allowed",
        "network_enabled",
    ):
        if lock.get(key) is not False:
            raise SignalInputValidationError(f"safety_lock {key} must be false")


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("required_input_mode") != "STATIC_OFFLINE_FIXTURE":
        raise SignalInputValidationError("required_input_mode must be STATIC_OFFLINE_FIXTURE")
    for key in (
        "require_package_immutable",
        "require_strategy_immutable",
        "require_network_source_false",
        "require_strict_time_order",
        "require_unique_symbol_timestamps",
        "require_valid_ohlc",
        "require_nonnegative_volume",
        "require_strategy_window_consistency",
        "require_minimum_history",
    ):
        if config.get(key) is not True:
            raise SignalInputValidationError(f"{key} must be true")
    allowed_price_fields = config.get("allowed_price_fields")
    if not isinstance(allowed_price_fields, list) or not allowed_price_fields:
        raise SignalInputValidationError("allowed_price_fields must be a non-empty list")
    for key in (
        "signal_generation_allowed",
        "order_generation_allowed",
        "fill_simulation_allowed",
        "paper_orders_allowed",
        "live_orders_allowed",
        "network_allowed",
        "broker_connection_allowed",
        "external_side_effects_allowed",
    ):
        if config.get(key) is not False:
            raise SignalInputValidationError(f"{key} must be false")


def validate_package(
    source: Dict[str, Any], config: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    package = source.get("signal_input_package")
    if not isinstance(package, dict):
        raise SignalInputValidationError("signal_input_package is required")

    identity_pairs = (
        ("preparation_id", source.get("preparation_id")),
        ("cycle_id", source.get("cycle_id")),
        ("cycle_sequence", source.get("cycle_sequence")),
        ("session_id", source.get("session_id")),
        ("champion_candidate_id", source.get("champion_candidate_id")),
    )
    for key, expected in identity_pairs:
        if package.get(key) != expected:
            raise SignalInputValidationError(f"package {key} mismatch")

    prepared_at = parse_timestamp(package.get("prepared_at"), "package prepared_at")
    source_prepared_at = parse_timestamp(source.get("prepared_at"), "source prepared_at")
    if prepared_at != source_prepared_at:
        raise SignalInputValidationError("prepared_at mismatch")

    market = package.get("market_data")
    if not isinstance(market, dict):
        raise SignalInputValidationError("market_data is required")
    if market.get("mode") != config["required_input_mode"]:
        raise SignalInputValidationError("market input mode mismatch")
    if market.get("immutable") is not True:
        raise SignalInputValidationError("market_data must be immutable")
    if market.get("network_source") is not False:
        raise SignalInputValidationError("market_data network_source must be false")

    symbols = market.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise SignalInputValidationError("symbols must be a non-empty list")
    if any(not isinstance(symbol, str) or not symbol for symbol in symbols):
        raise SignalInputValidationError("each symbol must be a non-empty string")
    if len(symbols) != len(set(symbols)):
        raise SignalInputValidationError("symbols must be unique")

    bars = market.get("bars")
    if not isinstance(bars, list) or not bars:
        raise SignalInputValidationError("bars must be a non-empty list")
    if market.get("bar_count") != len(bars):
        raise SignalInputValidationError("bar_count mismatch")

    seen = set()
    timestamps_by_symbol: Dict[str, List[datetime]] = {symbol: [] for symbol in symbols}
    symbol_counts: Dict[str, int] = {symbol: 0 for symbol in symbols}
    for index, bar in enumerate(bars, 1):
        if not isinstance(bar, dict):
            raise SignalInputValidationError(f"bar {index} must be an object")
        symbol = bar.get("symbol")
        if symbol not in symbols:
            raise SignalInputValidationError(f"bar {index} symbol is outside the universe")
        ts = parse_timestamp(bar.get("timestamp"), f"bar {index} timestamp")
        key = (symbol, ts.isoformat())
        if key in seen:
            raise SignalInputValidationError("duplicate symbol/timestamp bar")
        seen.add(key)
        timestamps_by_symbol[symbol].append(ts)
        symbol_counts[symbol] += 1

        for field in ("open", "high", "low", "close", "volume"):
            value = bar.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SignalInputValidationError(f"bar {index} {field} must be numeric")
        if bar["volume"] < 0:
            raise SignalInputValidationError(f"bar {index} volume must be nonnegative")
        if min(bar["open"], bar["close"]) < bar["low"]:
            raise SignalInputValidationError(f"bar {index} low exceeds body minimum")
        if max(bar["open"], bar["close"]) > bar["high"]:
            raise SignalInputValidationError(f"bar {index} high is below body maximum")
        if bar["low"] > bar["high"]:
            raise SignalInputValidationError(f"bar {index} low exceeds high")

    for symbol, timestamps in timestamps_by_symbol.items():
        if timestamps != sorted(timestamps):
            raise SignalInputValidationError(f"bars for {symbol} are not time ordered")
        if len(timestamps) != len(set(timestamps)):
            raise SignalInputValidationError(f"bars for {symbol} contain duplicates")

    strategy = package.get("strategy_inputs")
    if not isinstance(strategy, dict):
        raise SignalInputValidationError("strategy_inputs are required")
    if strategy.get("immutable") is not True:
        raise SignalInputValidationError("strategy_inputs must be immutable")
    if not isinstance(strategy.get("strategy_id"), str) or not strategy["strategy_id"]:
        raise SignalInputValidationError("strategy_id is required")
    if strategy.get("price_field") not in config["allowed_price_fields"]:
        raise SignalInputValidationError("price_field is not allowed")
    for field in ("fast_window", "slow_window", "minimum_history_bars"):
        value = strategy.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SignalInputValidationError(f"{field} must be a positive integer")
    if strategy["fast_window"] >= strategy["slow_window"]:
        raise SignalInputValidationError("fast_window must be less than slow_window")
    if strategy["minimum_history_bars"] < strategy["slow_window"]:
        raise SignalInputValidationError(
            "minimum_history_bars must be at least slow_window"
        )
    for symbol, count in symbol_counts.items():
        if count < strategy["minimum_history_bars"]:
            raise SignalInputValidationError(
                f"insufficient history for {symbol}: {count}"
            )

    market_summary = {
        "mode": market["mode"],
        "symbol_count": len(symbols),
        "symbols": copy.deepcopy(symbols),
        "bar_count": len(bars),
        "first_timestamp_by_symbol": {
            symbol: timestamps_by_symbol[symbol][0].isoformat() for symbol in symbols
        },
        "last_timestamp_by_symbol": {
            symbol: timestamps_by_symbol[symbol][-1].isoformat() for symbol in symbols
        },
        "bar_count_by_symbol": symbol_counts,
        "strict_time_order": True,
        "duplicate_symbol_timestamps": 0,
        "network_source": False,
        "immutable": True,
    }
    strategy_summary = {
        "strategy_id": strategy["strategy_id"],
        "price_field": strategy["price_field"],
        "fast_window": strategy["fast_window"],
        "slow_window": strategy["slow_window"],
        "minimum_history_bars": strategy["minimum_history_bars"],
        "history_sufficient": True,
        "window_consistency": True,
        "immutable": True,
    }
    return market_summary, strategy_summary


def validation_id(preparation_id: str, validated_at: str) -> str:
    material = f"{preparation_id}|{validated_at}|{VERSION}"
    return "SIV-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16].upper()


def build_validation(
    source: Dict[str, Any],
    config: Dict[str, Any],
    validated_at: Optional[str] = None,
) -> Dict[str, Any]:
    validate_source(source)
    validate_config(config)
    market_summary, strategy_summary = validate_package(source, config)

    if validated_at is None:
        when = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        when = parse_timestamp(validated_at, "validated_at")
    validated_at_value = when.isoformat()
    vid = validation_id(source["preparation_id"], validated_at_value)

    checks = [
        {"check_index": 1, "check": "SIGNAL_INPUT_PREPARATION_INTEGRITY", "state": "PASS"},
        {"check_index": 2, "check": "SIGNAL_INPUT_PACKAGE_INTEGRITY", "state": "PASS"},
        {"check_index": 3, "check": "PACKAGE_IDENTITY_CONSISTENCY", "state": "PASS"},
        {"check_index": 4, "check": "STATIC_OFFLINE_INPUT_MODE", "state": "PASS"},
        {"check_index": 5, "check": "MARKET_DATA_IMMUTABILITY", "state": "LOCKED"},
        {"check_index": 6, "check": "SYMBOL_UNIVERSE_VALID", "state": "PASS"},
        {"check_index": 7, "check": "OHLC_STRUCTURE_VALID", "state": "PASS"},
        {"check_index": 8, "check": "TIMESTAMP_ORDER_VALID", "state": "PASS"},
        {"check_index": 9, "check": "DUPLICATE_BARS_ABSENT", "state": "PASS"},
        {"check_index": 10, "check": "STRATEGY_INPUTS_VALID", "state": "PASS"},
        {"check_index": 11, "check": "MINIMUM_HISTORY_SUFFICIENT", "state": "PASS"},
        {"check_index": 12, "check": "SIGNAL_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 13, "check": "ORDER_GENERATION_NOT_STARTED", "state": "PASS"},
        {"check_index": 14, "check": "NETWORK_DISABLED", "state": "PASS"},
        {"check_index": 15, "check": "LIVE_TRADING_PROHIBITION", "state": "ENFORCED"},
    ]
    ledger = [
        {"ledger_index": 1, "event": "SIGNAL_INPUT_PREPARATION_VERIFIED", "state": "PASS", "validation_id": vid},
        {"ledger_index": 2, "event": "SIGNAL_INPUT_PACKAGE_VERIFIED", "state": "PASS", "validation_id": vid},
        {"ledger_index": 3, "event": "MARKET_DATA_VALIDATED", "state": "PASS", "validation_id": vid},
        {"ledger_index": 4, "event": "STRATEGY_INPUTS_VALIDATED", "state": "PASS", "validation_id": vid},
        {"ledger_index": 5, "event": "SAFETY_LOCKS_RECONFIRMED", "state": "ENFORCED", "validation_id": vid},
        {"ledger_index": 6, "event": "SIGNAL_INPUT_VALIDATION_COMPLETED", "state": "READY_FOR_SIGNAL_GENERATION_AUTHORIZATION", "validation_id": vid},
    ]

    evidence = {
        "validation_id": vid,
        "preparation_id": source["preparation_id"],
        "signal_input_package_sha256": source["signal_input_package_sha256"],
        "market_summary": market_summary,
        "strategy_summary": strategy_summary,
        "validated_at": validated_at_value,
    }

    result = {
        "status": "PASS",
        "decision": "offline_paper_signal_input_validated",
        "validation_id": vid,
        "validation_state": "READY_FOR_SIGNAL_GENERATION_AUTHORIZATION",
        "preparation_id": source["preparation_id"],
        "certificate_id": source["certificate_id"],
        "execution_id": source["execution_id"],
        "session_id": source["session_id"],
        "cycle_id": source["cycle_id"],
        "cycle_sequence": source["cycle_sequence"],
        "champion_candidate_id": source["champion_candidate_id"],
        "validation_evidence": evidence,
        "validation_evidence_sha256": sha256_of(evidence),
        "validation_checks": checks,
        "validation_checks_sha256": sha256_of(checks),
        "validation_ledger": ledger,
        "validation_ledger_sha256": sha256_of(ledger),
        "source_signal_input_preparation_sha256":
            source["offline_paper_signal_input_preparation_sha256"],
        "source_signal_input_package_sha256": source["signal_input_package_sha256"],
        "validation_gate": {
            "signal_input_validated": True,
            "signal_generation_authorization_allowed": True,
            "signal_generation_allowed": False,
            "order_generation_allowed": False,
            "fill_simulation_allowed": False,
            "paper_orders_allowed": False,
            "live_orders_allowed": False,
            "network_allowed": False,
            "next_version": "75.2N",
        },
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "network_used": False,
        "safety_lock": copy.deepcopy(source["safety_lock"]),
        "validated_at": validated_at_value,
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
    }
    result["offline_paper_signal_input_validation_sha256"] = sha256_of(result)
    return result


def write_outputs(result: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "offline_paper_signal_input_validation_v75_2m.json": result,
        "offline_paper_signal_input_validation_evidence_v75_2m.json":
            result["validation_evidence"],
        "offline_paper_signal_input_validation_checks_v75_2m.json": {
            "validation_id": result["validation_id"],
            "validation_checks": result["validation_checks"],
            "validation_checks_sha256": result["validation_checks_sha256"],
        },
        "offline_paper_signal_input_validation_ledger_v75_2m.json": {
            "validation_id": result["validation_id"],
            "validation_ledger": result["validation_ledger"],
            "validation_ledger_sha256": result["validation_ledger_sha256"],
        },
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (output_dir / "offline_paper_signal_input_validation_v75_2m.sha256").write_text(
        result["offline_paper_signal_input_validation_sha256"] + "\n",
        encoding="utf-8",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="V75.2M Offline Paper Signal Input Validator"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--validated-at")
    args = parser.parse_args(argv)
    try:
        result = build_validation(
            read_json(Path(args.input)),
            read_json(Path(args.config)),
            args.validated_at,
        )
        write_outputs(result, Path(args.output_dir))
        summary = result["validation_evidence"]
        print(json.dumps({
            "status": result["status"],
            "decision": result["decision"],
            "validation_id": result["validation_id"],
            "validation_state": result["validation_state"],
            "session_id": result["session_id"],
            "cycle_id": result["cycle_id"],
            "cycle_sequence": result["cycle_sequence"],
            "symbol_count": summary["market_summary"]["symbol_count"],
            "bar_count": summary["market_summary"]["bar_count"],
            "strict_time_order": summary["market_summary"]["strict_time_order"],
            "duplicate_symbol_timestamps":
                summary["market_summary"]["duplicate_symbol_timestamps"],
            "history_sufficient":
                summary["strategy_summary"]["history_sufficient"],
            "signal_input_validated":
                result["validation_gate"]["signal_input_validated"],
            "signal_generation_authorization_allowed":
                result["validation_gate"]["signal_generation_authorization_allowed"],
            "signal_generation_allowed":
                result["validation_gate"]["signal_generation_allowed"],
            "order_generation_allowed":
                result["validation_gate"]["order_generation_allowed"],
            "paper_orders_allowed": result["paper_orders_allowed"],
            "live_orders_allowed": result["live_orders_allowed"],
            "network_allowed": result["network_allowed"],
            "orders_submitted": result["orders_submitted"],
            "approved_for_live": result["approved_for_live"],
            "network_used": result["network_used"],
            "offline_paper_signal_input_validation_sha256":
                result["offline_paper_signal_input_validation_sha256"],
        }, indent=2, sort_keys=True))
        return 0
    except (SignalInputValidationError, OSError) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "offline_paper_signal_input_validation_failed",
            "error": str(exc),
            "approved_for_live": False,
            "network_used": False,
            "orders_submitted": 0,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
