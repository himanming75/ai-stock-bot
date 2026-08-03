from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required = [
        "strategy_engine_v2/models.py",
        "strategy_engine_v2/scoring.py",
        "strategy_engine_v2/decision.py",
        "strategy_engine_v2/explain.py",
        "strategy_engine_v2/engine.py",
        "strategy_engine_v2/io.py",
        "dashboard_v2/strategy_integration.py",
        "tools/run_strategy_engine_v2_v86_01_to_v86_08.py",
        "tools/test_strategy_engine_v2_v86_01_to_v86_08.py",
        "tools/verify_strategy_engine_v2_v86_01_to_v86_08.py",
        "release/v86_01_to_v86_08/input/strategy_signal_input.json",
        "release/v86_01_to_v86_08/README_V86_01_TO_V86_08.md",
    ]
    missing = [item for item in required if not (root / item).exists()]
    if missing:
        for item in missing:
            print(f"MISSING: {item}")
        return 1
    print("V86.01-V86.08 INSTALL CHECK PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
