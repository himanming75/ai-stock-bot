from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data import (
    BarRequest,
    MarketBar,
    OfflineAlpacaMarketDataAdapter,
    build_foundation_certificate,
    inspect_alpaca_installation,
    load_safety_config,
)

def load_fixture(path: Path) -> list[MarketBar]:
    return [MarketBar(**item) for item in json.loads(path.read_text(encoding="utf-8"))]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve()
    output_dir = repository_root / "release" / "v79_05" / "output"
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)

    install_status = inspect_alpaca_installation()
    safety = load_safety_config()
    bars = load_fixture(
        repository_root / "release" / "v79_04" / "fixtures" / "sample_stock_bars_v79_04.json"
    )
    request = BarRequest(
        symbols=("AAPL", "MSFT"),
        timeframe="1Min",
        start="2026-01-05T14:00:00Z",
        end="2026-01-05T15:00:00Z",
        limit=100,
        feed=safety.feed,
    )
    adapter = OfflineAlpacaMarketDataAdapter(bars, safety)
    result = adapter.get_stock_bars(request)
    certificate = build_foundation_certificate(
        repository_root,
        output_dir,
        install_status,
        safety,
        result,
        adapter.diagnostics(),
    )
    print(json.dumps({
        "stage_range": "V79.01-V79.05",
        "status": certificate["status"],
        "passed_stage_count": certificate["passed_stage_count"],
        "failed_stage_count": certificate["failed_stage_count"],
        "fixture_bar_count": certificate["fixture_bar_count"],
        "alpaca_py_installed": certificate["alpaca_sdk"]["installed"],
        "network_calls_made": certificate["network_calls_made"],
        "broker_connected": certificate["broker_connected"],
        "actual_orders_submitted": certificate["actual_orders_submitted"],
        "next_phase": certificate["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
