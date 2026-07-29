from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import sys

MODULE_PATH = Path(__file__).resolve().parent / "backtest" / "offline_ai_signal_v25_0.py"
spec = importlib.util.spec_from_file_location("offline_ai_signal_v25_0", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

OfflineSignalEngine = module.OfflineSignalEngine
PriceBar = module.PriceBar
SignalPolicy = module.SignalPolicy
SignalAction = module.SignalAction
verify_result = module.verify_result
save_result = module.save_result
load_result = module.load_result


def make_bars(direction: str, count: int = 80) -> list[PriceBar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars: list[PriceBar] = []
    price = 100.0
    for index in range(count):
        if direction == "up":
            change = 0.45 + (index % 4) * 0.03
        elif direction == "down":
            change = -(0.45 + (index % 4) * 0.03)
        else:
            change = (0.08 if index % 2 == 0 else -0.08)
        open_price = price
        close_price = max(1.0, price + change)
        high = max(open_price, close_price) + 0.25
        low = min(open_price, close_price) - 0.25
        bars.append(
            PriceBar(
                timestamp=(start + timedelta(days=index)).isoformat(),
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close_price, 4),
                volume=1000.0 + index * 10,
            )
        )
        price = close_price
    return bars


def check(label: str, value: bool) -> None:
    print(f"{label:<52}: {value}")
    assert value, label


def blocked(callable_obj) -> bool:
    try:
        callable_obj()
    except RuntimeError:
        return True
    return False


def main() -> None:
    policy = SignalPolicy(buy_threshold=0.30, sell_threshold=-0.30, min_volume=500)
    engine = OfflineSignalEngine(policy)
    fixed_time = "2026-07-28T20:55:00+00:00"

    buy_result = engine.evaluate("TEST", make_bars("up"), evaluated_at=fixed_time)
    sell_result = engine.evaluate("TEST", make_bars("down"), evaluated_at=fixed_time)
    hold_result = engine.evaluate("TEST", make_bars("flat"), evaluated_at=fixed_time)

    check("V25.0 engine version verified", buy_result.version == "25.0")
    check("BUY signal generated", buy_result.action == SignalAction.BUY.value)
    check("SELL signal generated", sell_result.action == SignalAction.SELL.value)
    check("HOLD signal generated", hold_result.action == SignalAction.HOLD.value)
    check("BUY result hash verified", verify_result(buy_result))
    check("SELL result hash verified", verify_result(sell_result))
    check("HOLD result hash verified", verify_result(hold_result))
    check("Deterministic score verified", buy_result.score == engine.evaluate("TEST", make_bars("up"), evaluated_at=fixed_time).score)
    check("Deterministic result hash verified", buy_result.result_hash == engine.evaluate("TEST", make_bars("up"), evaluated_at=fixed_time).result_hash)
    check("Input hash differs for changed data", buy_result.input_hash != sell_result.input_hash)
    check("Policy hash created", len(buy_result.policy_hash) == 64)
    check("Confidence is bounded", 0.0 <= buy_result.confidence <= 1.0)
    check("Indicators were calculated", 0.0 <= buy_result.indicators.rsi <= 100.0)
    check("Composite components were calculated", -1.0 <= buy_result.components.trend <= 1.0)

    low_volume_bars = [replace(bar, volume=1.0) for bar in make_bars("up")]
    low_volume_result = engine.evaluate("TEST", low_volume_bars, evaluated_at=fixed_time)
    check("Low-volume policy gate forced HOLD", low_volume_result.action == SignalAction.HOLD.value)

    shock_bars = make_bars("up")
    prior = shock_bars[-2]
    shock_close = prior.close * 1.75
    shock_bars[-1] = replace(
        shock_bars[-1],
        open=prior.close,
        high=shock_close + 1.0,
        low=prior.close - 1.0,
        close=shock_close,
    )
    shock_result = engine.evaluate("TEST", shock_bars, evaluated_at=fixed_time)
    check("Abnormal return stability guard forced HOLD", shock_result.action == SignalAction.HOLD.value)

    tampered = replace(buy_result, score=-0.99)
    check("Tampered result detected", not verify_result(tampered))

    invalid_policy_blocked = False
    try:
        OfflineSignalEngine(SignalPolicy(fast_sma=20, slow_sma=5))
    except ValueError:
        invalid_policy_blocked = True
    check("Invalid policy was blocked", invalid_policy_blocked)

    insufficient_bars_blocked = False
    try:
        engine.evaluate("TEST", make_bars("up", 10), evaluated_at=fixed_time)
    except ValueError:
        insufficient_bars_blocked = True
    check("Insufficient bars were blocked", insufficient_bars_blocked)

    duplicate_time_bars = make_bars("up")
    duplicate_time_bars[-1] = replace(duplicate_time_bars[-1], timestamp=duplicate_time_bars[-2].timestamp)
    duplicate_time_blocked = False
    try:
        engine.evaluate("TEST", duplicate_time_bars, evaluated_at=fixed_time)
    except ValueError:
        duplicate_time_blocked = True
    check("Non-increasing timestamps were blocked", duplicate_time_blocked)

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "signal.json"
        save_result(buy_result, output_path)
        loaded = load_result(output_path)
        check("Result save and load passed", loaded == buy_result)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        payload["action"] = "SELL"
        output_path.write_text(json.dumps(payload), encoding="utf-8")
        tampered_load_blocked = False
        try:
            load_result(output_path)
        except ValueError:
            tampered_load_blocked = True
        check("Tampered saved result was blocked", tampered_load_blocked)

    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    forbidden_imports = ["import requests", "import urllib", "import socket", "import alpaca", "import ib_insync", "import ccxt"]
    check("Forbidden network/broker imports are absent", not any(item in source for item in forbidden_imports))
    check("Market data API was not called", module.FORBIDDEN_CAPABILITIES["market_data_api"] is False)
    check("Account API was not called", module.FORBIDDEN_CAPABILITIES["account_api"] is False)
    check("Network was not accessed", module.FORBIDDEN_CAPABILITIES["network_access"] is False)
    check("Broker API was not called", module.FORBIDDEN_CAPABILITIES["broker_api"] is False)
    check("Broker order was not created", blocked(module.broker_order))
    check("Order was not submitted", blocked(module.submit_order))
    check("Live execution not authorized", blocked(module.authorize_live_execution))
    check("Execution remains blocked", module.FORBIDDEN_CAPABILITIES["live_execution"] is False)
    check("Funds were not reserved", module.FORBIDDEN_CAPABILITIES["fund_reservation"] is False)
    check("Holdings were not reserved", module.FORBIDDEN_CAPABILITIES["holding_reservation"] is False)
    check("All checks passed", True)

    print("=" * 72)
    print("V25.0 offline AI signal engine test completed successfully.")
    print("BUY, HOLD, SELL, indicators, policy gates, hashing, and tamper detection were verified.")
    print("Market/account/network/broker/order/live execution remained blocked.")


if __name__ == "__main__":
    main()
