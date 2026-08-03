from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "multi_asset_backtest/io.py",
        "multi_asset_backtest/benchmark.py",
        "multi_asset_backtest/correlation.py",
        "multi_asset_backtest/portfolio.py",
        "multi_asset_backtest/engine.py",
        "dashboard_v2/multi_asset_backtest_integration.py",
        "tools/run_multi_asset_backtest_v87_17_to_v87_24.py",
        "tools/test_multi_asset_backtest_v87_17_to_v87_24.py",
        "tools/verify_multi_asset_backtest_v87_17_to_v87_24.py",
        "release/v87_17_to_v87_24/input/multi_asset_backtest_input.json",
        "release/v87_17_to_v87_24/README_V87_17_TO_V87_24.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V87.17-V87.24 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
