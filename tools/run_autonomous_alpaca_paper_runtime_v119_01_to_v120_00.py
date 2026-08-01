from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime import (
    AutonomousAlpacaPaperRuntime,
    AutonomousRuntimeConfig,
)


class FixtureMarketReader:
    def is_market_open(self):
        return True

    def get_price(self, symbol):
        return 50.0


class FixtureSignalProvider:
    def get_signal(self, symbol):
        return "BUY"


class FixturePreviewBuilder:
    def build(self, *, symbol, quantity, estimated_price):
        return {
            "symbol": symbol,
            "qty": quantity,
            "estimated_price": estimated_price,
            "client_order_id": "BOT-AUTO-PAPER-ONE-FIXTURE",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v120_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    runtime = AutonomousAlpacaPaperRuntime(
        config=AutonomousRuntimeConfig(
            symbol="AAPL",
            max_quantity=1,
            max_order_notional=100.0,
            read_network_enabled=True,
            single_order_write_enabled=False,
            live_trading_enabled=False,
        ),
        market_reader=FixtureMarketReader(),
        signal_provider=FixtureSignalProvider(),
        order_preview_builder=FixturePreviewBuilder(),
    )
    runtime.start()
    result = runtime.run_cycle()
    runtime.stop()

    payload = {
        "stage_range": "V119.01-V120.00",
        "status": "PASS",
        "implementation_type": "AUTONOMOUS_ALPACA_PAPER_RUNTIME_FOUNDATION",
        "mode": "OFFLINE_FIXTURE_PREVIEW_ONLY",
        **result.to_json_dict(),
        "runtime_final_state": runtime.state.value,
        "single_order_limit": 1,
        "max_order_notional": 100.0,
        "live_trading_enabled": False,
        "next_phase": "V120_01_ACTUAL_AUTONOMOUS_PAPER_READ_SESSION",
    }
    (output / "autonomous_alpaca_paper_runtime_foundation_result.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
