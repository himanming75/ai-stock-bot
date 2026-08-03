from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "backtest_v2/models.py",
        "backtest_v2/broker.py",
        "backtest_v2/strategy.py",
        "backtest_v2/statistics.py",
        "backtest_v2/engine.py",
        "backtest_v2/io.py",
        "dashboard_v2/backtest_v2_integration.py",
        "tools/run_backtest_v2_v87_01_to_v87_08.py",
        "tools/test_backtest_v2_v87_01_to_v87_08.py",
        "tools/verify_backtest_v2_v87_01_to_v87_08.py",
        "release/v87_01_to_v87_08/input/backtest_sample.json",
        "release/v87_01_to_v87_08/README_V87_01_TO_V87_08.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V87.01-V87.08 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
