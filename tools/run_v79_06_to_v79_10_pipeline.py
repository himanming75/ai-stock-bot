from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data import (
    AlpacaRequestFactory,
    FixtureHistoricalTransport,
    HistoricalBarsQuery,
    HistoricalClientConfig,
    HistoricalDataCache,
    SafeHistoricalDataService,
    build_historical_certificate,
    inspect_historical_installation,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = root / "release" / "v79_10" / "output"
    cache_dir = output / "cache"
    if args.clean and output.exists():
        shutil.rmtree(output)

    install = inspect_historical_installation()
    if not (
        install.alpaca_py_installed
        and install.stock_historical_client_importable
        and install.stock_bars_request_importable
        and install.dataframe_support_available
    ):
        print(json.dumps({
            "stage_range": "V79.06-V79.10",
            "status": "FAIL",
            "error": "alpaca-py historical dependencies unavailable",
            "install_command": 'python -m pip install "alpaca-py>=0.43.5" pandas',
        }, indent=2))
        return 1

    config = HistoricalClientConfig()
    query = HistoricalBarsQuery(
        symbols=("AAPL", "MSFT"),
        timeframe="1Min",
        start="2026-01-05T14:00:00Z",
        end="2026-01-05T15:00:00Z",
        limit=100,
        adjustment="raw",
        feed=config.default_feed,
        sort="asc",
    )

    # Validates compatibility with the installed official alpaca-py request model.
    sdk_request = AlpacaRequestFactory.build_stock_bars_request(query)

    fixture_path = root / "release" / "v79_07" / "fixtures" / "historical_stock_bars_v79_07.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    transport = FixtureHistoricalTransport(payload)
    cache = HistoricalDataCache(cache_dir)
    service = SafeHistoricalDataService(config, transport, cache)
    records_first = service.get_bars(query)
    records_second = service.get_bars(query)
    if records_first != records_second:
        raise RuntimeError("cache replay mismatch")
    cache_manifest = json.loads((cache_dir / f"{query.cache_key}.manifest.json").read_text(encoding="utf-8"))

    certificate = build_historical_certificate(
        root, output, install, config, query, records_second,
        service.diagnostics(), cache_manifest
    )
    print(json.dumps({
        "stage_range": "V79.06-V79.10",
        "status": certificate["status"],
        "passed_stage_count": certificate["passed_stage_count"],
        "failed_stage_count": certificate["failed_stage_count"],
        "record_count": certificate["record_count"],
        "symbols": certificate["symbols"],
        "sdk_request_type": type(sdk_request).__name__,
        "fixture_fetch_count": transport.fixture_fetch_count,
        "cache_hit_count": certificate["diagnostics"]["cache_hit_count"],
        "network_calls_made": certificate["network_calls_made"],
        "credentials_used": certificate["credentials_used"],
        "broker_connected": certificate["broker_connected"],
        "trading_client_created": certificate["trading_client_created"],
        "actual_orders_submitted": certificate["actual_orders_submitted"],
        "next_phase": certificate["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
