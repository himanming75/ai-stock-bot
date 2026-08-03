from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "indicator_engine/models.py",
        "indicator_engine/calculations.py",
        "indicator_engine/signals.py",
        "indicator_engine/engine.py",
        "indicator_engine/io.py",
        "dashboard_v2/indicator_integration.py",
        "tools/run_indicator_engine_v86_09_to_v86_16.py",
        "tools/test_indicator_engine_v86_09_to_v86_16.py",
        "tools/verify_indicator_engine_v86_09_to_v86_16.py",
        "release/v86_09_to_v86_16/input/ohlcv_sample.json",
        "release/v86_09_to_v86_16/README_V86_09_TO_V86_16.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V86.09-V86.16 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
